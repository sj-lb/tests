# ibis_sqreamdb/compiler.py

from itertools import starmap
from calendar import day_name

from ibis.expr import operations as ops, datatypes as dt
from ibis.backends.sql.datatypes import SqlglotType
from ibis.backends.sql.compilers.base import NULL, AggGen, SQLGlotCompiler
from ibis.backends.sql.compilers import SQLiteCompiler, PostgresCompiler
import ibis.common.exceptions as com
from sqlglot import exp
from sqlglot.generator import Generator
import sqlglot as sg
from functools import reduce

import sqlglot.expressions as sge
# from sqlglot.dataframe.sqlglot import DataType # Import DataType from sqlglot
from .dialect import SQreamDialect

class SQreamType(SqlglotType):
    dialect = SQreamDialect()

    @classmethod
    def from_string(cls, type_string: str, nullable: bool | None = None) -> dt.DataType:
        nullable = cls.default_nullable if nullable is None else nullable
        type_string_upper = type_string.upper()

        if type_string_upper.startswith("ARRAY:"):
            inner_type_str = type_string_upper[len("ARRAY:"):]
            
            inner_ibis_type = cls.from_string(type_string=inner_type_str)
            
            return dt.Array(inner_ibis_type, nullable=True)

        if type_string_upper == "BIGINT":
            return dt.Int64(nullable=nullable)
        elif type_string_upper == "INTEGER":
            return dt.Int32(nullable=nullable)
        elif type_string_upper == "BOOLEAN":
            return dt.Boolean(nullable=nullable)
        elif type_string_upper == "REAL":
            return dt.Float32(nullable=nullable)
        elif type_string_upper == "DOUBLE":
            return dt.Float64(nullable=nullable)
        elif type_string_upper == "NUMERIC": # Often for DECIMAL
            return dt.Decimal(precision=None, scale=None, nullable=nullable)
        elif type_string_upper.startswith(("VARCHAR", "NVARCHAR", "TEXT", "NTEXT")):
            return dt.String(nullable=nullable)
        elif type_string_upper == "DATE":
            return dt.Date(nullable=nullable)
        elif type_string_upper == "TIMESTAMP":
            return dt.Timestamp(nullable=nullable)
        return super().from_string(type_string)

class SqreamCompiler(SQLGlotCompiler):
    dialect = SQreamDialect
    type_mapper = SQreamType
    agg = AggGen(supports_filter=True)
    pymods_entries = None

    UNSUPPORTED_OPS = (
        ops.ApproxCountDistinct,
        ops.ApproxMedian,
        ops.ApproxMultiQuantile,
        ops.ApproxQuantile,
        ops.ExtractIsoYear,
        ops.ExtractMicrosecond,
        ops.FindInSet,
        ops.Greatest,
        ops.Levenshtein,
        ops.JSONGetItem,
        ops.UnwrapJSONBoolean,
        ops.UnwrapJSONString,
        ops.UnwrapJSONInt64,
        ops.UnwrapJSONFloat64,
        ops.IsInf,
        ops.RandomScalar,
        ops.TimeFromHMS,
        ops.ArrayZip
    )

    SIMPLE_OPS = {
        ops.Cot: "cot",
        ops.Count: "count",
        ops.TypeOf: "typeof",
        ops.Log10: " log10", # doesn't work without leading whitespace
        ops.Ln: " log",
        ops.GroupConcat: "string_agg",
        ops.Hash: "CRC64",
        ops.RegexExtract: "regexp_substr",
        ops.Strip: "trim",
        ops.LStrip: "ltrim",
        ops.RStrip: "rtrim",
        ops.Unnest: "unnest",
        ops.ArrayRemove: "array_remove",
        ops.ArrayMin: "m_internal.array_min",
        ops.ArrayMean: "m_internal.array_mean",
        ops.ArrayMax: "m_internal.array_max",
        ops.ArraySum: "m_internal.array_sum",
        ops.ArraySort: "m_internal.array_sort",
        ops.ArrayRepeat: 'm_internal.array_repeat',
        ops.ArraySlice: 'm_internal.array_slice', # TODO: handle param
        ops.ArrayFilter: 'm_internal.array_filter', # TODO: handle param
        ops.ArrayMap: 'm_internal.array_map', # TODO: handle param
        ops.ArrayDistinct: 'm_internal.array_distinct',
        ops.ArrayIntersect: 'm_internal.array_intersect',
        ops.ArrayUnion: 'm_internal.array_union'
        # ops.First: "top 1"
    }
    
    def visit_Aggregate(self, op, *, parent, groups, metrics):
        return next(iter(metrics.values())) if isinstance(next(iter(op.metrics.values())), (ops.ArgMax, ops.ArgMin, ops.Last)) else super().visit_Aggregate(op, parent=parent, groups=groups, metrics=metrics)
    def visit_Date(self, op, *, arg):
        return sge.Cast(this=sge.convert(arg), to=sge.DataType.build('DATE'), copy=False)
    def visit_StringToDate(self, op, *, arg):
        return sge.Cast(this=sge.convert(arg), to=sge.DataType.build('DATE'), copy=False)
    def visit_StringToTimestamp(self, op, *, arg, format_str):
        return sge.Cast(this=sge.convert(arg), to=sge.DataType.build('TIMESTAMP'), copy=False)
    def visit_Log2(self, op: ops.Log2, *, arg: sge.Expression) -> sge.Expression:
        return self.f.log(arg) / self.f.log(2)
    def visit_Log(self, op, *, arg, base):
        if base is None:
            return self.f.log(arg)
        return self.f.log(arg) / self.f.log(base)
    def visit_StartsWith(self, op, *, arg, start):
        return arg.like(self.f.concat(start, "%"))
    def visit_EndsWith(self, op, *, arg, end):
        return arg.like(self.f.concat("%", end))
    def visit_Xor(self, op, *, left, right):
        return (left.or_(right)).and_(sge.not_(left.and_(right)))
    def visit_Correlation(self, op, *, left, right, how, where):
        if how == "sample":
            raise com.UnsupportedOperationError(
                f"{self.dialect} only implements `pop` correlation coefficient")
        if (left_type := op.left.dtype).is_boolean():
            left = self.cast(left, dt.Int32(nullable=left_type.nullable))
        if (right_type := op.right.dtype).is_boolean():
            right = self.cast(right, dt.Int32(nullable=right_type.nullable))
        return self.agg.corr(left, right, where=where)
    def visit_All(self, op: ops.All, *, arg: sge.Expression, where: sge.Expression | None) -> sge.Expression:
        return self.agg.min(
            self.cast(arg, dt.Int32(nullable=op.arg.dtype.nullable)),
            where=where)
    def visit_Any(self, op: ops.All, *, arg: sge.Expression, where: sge.Expression | None) -> sge.Expression:
        return self.agg.max(
            self.cast(arg, dt.Int32(nullable=op.arg.dtype.nullable)),
            where=where)
    def visit_ArgMax(self, op, *, arg, key, where):
        main_table_sqlglot = sge.Table(
            this=sge.Identifier(this=op.arg.rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True)))

        inner_max_subquery = sge.Select(expressions=[sge.Max(this=key).as_("max_val")]).from_(main_table_sqlglot.copy())
        aliased_inner_max_subquery = sge.Paren(this=inner_max_subquery).as_("t1", quoted=True)

        join_condition = sge.EQ(
            this=key,
            expression=sge.Column(
                this=sge.Identifier(this="max_val", quoted=True),
                table=sge.Identifier(this="t1", quoted=True)))

        final_query = sge.Select(expressions=[arg]).from_(main_table_sqlglot)
        final_query = final_query.join(aliased_inner_max_subquery, on=join_condition)
        return final_query.where(where) if where else final_query
    def visit_ArgMin(self, op: ops.ArgMax, *, arg: sge.Expression, key: sge.Expression, where: sge.Expression | None) -> sge.Expression:
        ibis_table_rel = op.arg.rel

        main_table_sqlglot = sge.Table(
            this=sge.Identifier(this=ibis_table_rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True)))

        inner_max_subquery = sge.Paren(this=sge.Select(expressions=[sge.Min(this=key).as_("max_val")]).from_(main_table_sqlglot.copy()))
        aliased_inner_max_subquery = inner_max_subquery.as_("t1")

        join_condition = sge.EQ(
            this=key,
            expression=sge.Column(this=sge.Identifier(this="max_val", quoted=True), table=sge.Identifier(this="t1", quoted=True)))

        final_query = sge.Select(expressions=[arg]).from_(main_table_sqlglot)
        final_query = final_query.join(aliased_inner_max_subquery, on=join_condition)
        
        return sge.Paren(this=final_query.where(where) if where else final_query)
    def tsadd_impl(self, op, *, left, right, is_sub: bool | None = None):
        if isinstance(op.right, ops.Literal) and isinstance(op.right.dtype, dt.Interval):
            amount_sqlglot_expr = sge.Literal.number(op.right.value)
            unit = op.right.dtype.unit.short

        elif isinstance(op.right, ops.IntervalFromInteger):
            amount_sqlglot_expr = right.this
            unit = op.right.unit.short

        else:
            raise com.UnsupportedOperationError(
                f"Unsupported interval type for addition in SQreamDB: {type(op.right).__name__}")

        sql_amount = sge.Cast(this=amount_sqlglot_expr, to=sge.DataType.build('INT'))
        if is_sub:
            sql_amount = -sql_amount
        if unit == 'm':
            unit = 'N'
        sql_unit = sge.Var(this=unit.upper())

        return self.f.dateadd(sql_unit, sql_amount, left)
    def visit_TimestampAdd(self, op, *, left, right):
        return self.tsadd_impl(op=op, left=left, right=right)
    def visit_TimestampSub(self, op, *, left, right): # TODO: reuse TimestampAdd
        return self.tsadd_impl(op=op, left=left, right=right, is_sub=True)
    def visit_TimestampDiff(self, op, *, left, right):
        return self.f.datediff(sge.Var(this='s'), right, left)
    def visit_IntervalFromInteger(self, op, *, arg, unit):
        return arg
    def _lpad_sql(self, arg, length, pad):
        arg_str = sge.Cast(this=arg, to=sge.DataType.build('TEXT'))
        
        if isinstance(pad, sge.Literal) and pad.is_string:
            py_pad_char = pad.this
            long_literal_pad_string = sge.Literal.string(py_pad_char * int(length.this))
        else:
            raise com.UnsupportedOperationError(
                "LPAD only supports literal 'pad' character for now.")

        concatenated_string = self.f.concat(long_literal_pad_string, arg_str)
        return self.f.right(concatenated_string, length)
    def visit_LPad(self, op, *, arg, length, pad):
        return self._lpad_sql(arg, length, pad)
    def _rpad_sql(self, arg, length, pad):
        arg_str = sge.Cast(this=arg, to=sge.DataType.build('TEXT'))

        if isinstance(pad, sge.Literal) and pad.is_string:
            py_pad_char = pad.this
            long_literal_pad_string = sge.Literal.string(py_pad_char * int(length.this))
        else:
            raise com.UnsupportedOperationError(
                "RPAD only supports literal 'pad' character for now.")

        concatenated_string = self.f.concat(arg_str, long_literal_pad_string)
        return self.f.left(concatenated_string, length)
    def visit_RPad(self, op, *, arg, length, pad):
        return self._rpad_sql(arg, length, pad)
    def visit_Clip(self, op, *, arg, lower, upper):
        ifs = []
        if upper is not None:
            upper = self.cast(upper, op.arg.dtype)
            ifs.append(self.if_(sge.GT(this=arg, expression=upper), upper))
        if lower is not None:
            lower = self.cast(lower, op.arg.dtype)
            ifs.append(self.if_(sge.LT(this=arg, expression=lower), lower))
        return sge.Case(ifs=ifs, default=arg) if ifs else arg
    def visit_DateFromYMD(self, op, *, year, month, day):
        year_str = sge.Cast(this=year, to=sge.DataType.build('TEXT'))
        month_str = sge.Cast(this=month, to=sge.DataType.build('TEXT'))
        day_str = sge.Cast(this=day, to=sge.DataType.build('TEXT'))

        padded_month = self._lpad_sql(arg=month_str, length=sge.Literal.number(2), pad=sge.Literal.string('0'))
        padded_day = self._lpad_sql(arg=day_str, length=sge.Literal.number(2), pad=sge.Literal.string('0'))

        date_string_expr = self.f.concat(
            year_str,
            sge.Literal.string('-'),
            padded_month,
            sge.Literal.string('-'),
            padded_day)

        return sge.Cast(this=date_string_expr, to=sge.DataType.build('DATE'))
    def visit_TimestampFromYMDHMS(self, op, *, year, month, day, hours, minutes, seconds):
        return sge.Cast(
            this=self.f.concat(
                sge.Cast(this=year, to=sge.DataType.build('TEXT')),
                sge.Literal.string('-'),
                self._lpad_sql(
                    arg=month,
                    length= sge.Literal.number(2),
                    pad=sge.Literal.string('0')),
                sge.Literal.string('-'),
                self._lpad_sql(
                    arg=day,
                    length= sge.Literal.number(2),
                    pad=sge.Literal.string('0')),
                sge.Literal.string(' '),
                self._lpad_sql(
                    arg=hours,
                    length= sge.Literal.number(2),
                    pad=sge.Literal.string('0')),
                sge.Literal.string(':'),
                self._lpad_sql(
                    arg=minutes,
                    length= sge.Literal.number(2),
                    pad=sge.Literal.string('0')),
                sge.Literal.string(':'),
                self._lpad_sql(
                    arg=seconds,
                    length= sge.Literal.number(2),
                    pad=sge.Literal.string('0')),),
            to=sge.DataType.build('TIMESTAMP'))
    def visit_TimestampTruncate(self, op, *, arg, unit):
        unit_mapping = {
            "Y": "year",
            "Q": "quarter",
            "M": "month",
            "W": "week",
            "D": "day",
            "h": "hour",
            "m": "minute",
            "s": "second",
            "ms": "ms",
            "us": "us"}

        if (raw_unit := unit_mapping.get(unit.short)) is None:
            raise com.UnsupportedOperationError(
                f"Unsupported truncate unit {unit.short!r}")

        return self.f.trunc(arg, sge.Identifier(this=raw_unit))
    def visit_DayOfWeekIndex(self, op, *, arg):
        return self.f.datepart(sge.Identifier(this='WEEKDAY'), arg)
    def visit_DayOfWeekName(self, op, *, arg):
        # day of week number is 0-indexed: Sunday == 0, Saturday == 6
        return sge.Case(
            this=((self.f.datepart(sge.Identifier(this='WEEKDAY'), arg) + 5) % 7),
            ifs=list(starmap(self.if_, enumerate(day_name))))
    def visit_ExtractEpochSeconds(self, op, *, arg):
        return self.f.to_unixts(self.cast(arg, dt.timestamp))
    def visit_ExtractMillisecond(self, op, *, arg):
        return self.f.extract(self.v.millisecond, arg)
    def visit_ExtractQuery(self, op, *, arg, key=None):
        if key is not None:
            raise com.UnsupportedOperationError(
                "Extracting specific query keys is not yet supported in SQreamDB backend.")

        question_mark_pos = sge.func(' CHARINDEX', sge.Literal.string('?'), arg)
        url_length = self.f.length(arg)

        substring_expression = self.f.substring(
            arg,
            sge.Add(this=question_mark_pos, expression=sge.Literal.number(1)),
            sge.Sub(this=url_length, expression=question_mark_pos))

        return sge.Case(
            this=question_mark_pos,
            ifs={self.if_(condition=sge.Literal.number(0), true=sge.Identifier(this='NULL'))},
            default=substring_expression) # ELSE substring_expression
    def visit_First(self, op, *, arg, order_by, include_null, where):
        subquery_select_list = [arg] # The column to select in the subquery

        subquery_order_by_list = []
        if order_by:
            for i, order_expr_sqlglot in enumerate(order_by):
                ibis_order_op = op.order_by[i] # Get the Ibis operation for sort key
                is_desc = isinstance(ibis_order_op, ops.SortKey) and ibis_order_op.descending
                subquery_order_by_list.append(sge.Ordered(this=order_expr_sqlglot, desc=is_desc))
        else:
            subquery_order_by_list.append(sge.Ordered(this=arg)) 
        from_expr = sge.Table(
            this=sge.Identifier(this=op.arg.rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True))) # arg.table gives the alias like 't0'

        subquery = sge.Select(expressions=subquery_select_list).from_(from_expr)

        if where:
            subquery = subquery.where(where)
        
        if subquery_order_by_list:
            subquery = subquery.order_by(*subquery_order_by_list)
        return sge.func('TOP 1', subquery)
    def visit_Arbitrary(self, op, *, arg, where):
        ret = sge.Select(expressions=[sge.func('top 1', arg)])
        # return ret.where(where) if where else ret
        return sge.func('top 1', arg)
    def visit_Last(self, op, *, arg, where, order_by=None, include_null=True, **kwargs):
        subquery_select_list = [arg] # Select the argument column

        subquery_order_by_list = []
        if order_by:
            for i, order_expr_sqlglot in enumerate(order_by):
                ibis_order_op = op.order_by[i]
                is_desc = isinstance(ibis_order_op, ops.SortKey) and ibis_order_op.descending
                subquery_order_by_list.append(sge.Ordered(this=order_expr_sqlglot, desc=is_desc))
        else:
            raise com.UnsupportedOperationError('last is meaningless when the table is not ordered')

        from_expr = sge.Table(
            this=sge.Identifier(this=op.arg.rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True)))

        subquery = sge.Select(expressions=subquery_select_list).from_(from_expr)

        if where:
            subquery = subquery.where(where)

        if subquery_order_by_list:
            subquery = subquery.order_by(*subquery_order_by_list)

        return subquery.limit(sge.Literal.number(1))
    def visit_Least(self, op, *, arg):
        return sge.Select(expressions=[arg]).order_by(sge.Ordered(this=arg, desc=False)).limit(sge.Literal.number(1))
    def visit_Greatest(self, op, *, arg):
        return sge.Select(expressions=[arg]).order_by(sge.Ordered(this=arg, desc=True)).limit(sge.Literal.number(1))
    def visit_IdenticalTo(self, op, *, left, right):
        equals_expr = sge.Paren(this=sge.EQ(this=left, expression=right))

        both_null_expr = sge.Paren(this=sge.And(
            this=sge.Is(this=left, expression=NULL),
            expression=sge.Is(this=right, expression=NULL)))

        return self.if_(condition=sge.Or(this=equals_expr, expression=both_null_expr), true=sge.Identifier(this='True'), false=sge.Identifier(this='False'))
    def quantile_impl(self, *, arg, quantile, where=None):
        qtl_expr = sge.WithinGroup(
            this=sge.PercentileCont(this=quantile),
            expression=sge.Order(expressions=[arg]))

        return sge.Filter(this=qtl_expr, expression=where) if where else qtl_expr
    def visit_Quantile(self, op, *, arg, quantile, where):
        return self.quantile_impl(arg=arg, quantile=quantile.this, where=where)
    def visit_Median(self, op, *, arg, where):
        return self.quantile_impl(arg=arg, quantile=sge.Literal.number(0.5), where=where)
    def visit_MultiQuantile(self, op, *, arg, quantile, where):
        quantile_expressions = []
        for q_ibis_op in quantile:
            quantile_expressions.append(self.quantile_impl(
                arg=arg,
                quantile=q_ibis_op,
                where=where))
        return sge.Array(expressions=quantile_expressions)
    def visit_IsNan(self, op, *, arg):
        return arg.is_(NULL)
    def visit_Mode(self, op, *, arg, where):
        mode_expr = sge.WithinGroup(
            this=self.f.mode(),
            expression=sge.Order(expressions=[arg]))
        return sge.Filter(this=mode_expr, expression=where) if where else mode_expr
    def range_impl(self, op, start, stop, step, **kwargs):
        series_column_name = "value"

        if isinstance(op.step, ops.Literal) and op.step.value < 0:
            adjusted_stop = sge.Add(this=stop, expression=sge.Literal.number(1))
        else: # Default to positive step if not specified or > 0
            adjusted_stop = sge.Sub(this=stop, expression=sge.Literal.number(1))
        
        generate_series_call = sge.GenerateSeries(
            this=start,               # Start
            expression=adjusted_stop, # End (inclusive for GENERATE_SERIES)
            step=step)                # Step
        return sge.Table(
            this=generate_series_call,
            alias=sge.Alias(this=sge.Identifier(this="_", quoted=True)), # Alias the derived table
            columns=[sge.Column(this=sge.Identifier(this=series_column_name, quoted=True))]) # Define column in derived table
    def visit_IntegerRange(self, op, *, start, stop, step, **kwargs):
        return self.range_impl(start=start, op=op, stop=stop, step=step, kwargs=kwargs)
    def visit_Range(self, op, *, start, stop, step, **kwargs):
        return self.range_impl(start=start, op=op, stop=stop, step=step, kwargs=kwargs)
    def visit_RegexReplace(self, op, *, arg, pattern, replacement):
        return self.f.regexp_replace(arg, pattern, replacement)
    def visit_StringContains(self, op, *, haystack, needle):
        return sge.GT(this= self.strfind_impl(haystack, needle), expression=sge.Literal.number(0))
    def visit_StringJoin(self, op, *, sep, arg):
        concatenated_parts = []
        for i, col_expr in enumerate(arg):
            concatenated_parts.append(col_expr)
            if i < len(arg) - 1:
                concatenated_parts.append(sep)
        return self.f.concat(*concatenated_parts)
    def strfind_impl(self, arg, substr, start=None, end=None): # TODO: check SQream start and end options
        if start is not None:
            raise com.UnsupportedOperationError(
                "String find with start offset is not supported")
        if end is not None:
            raise com.UnsupportedOperationError(
                "String find with end offset is not supported")
        return sge.func(' CHARINDEX', substr, arg)
        # return self.f.charindex(substr=substr, arg=arg) # FIXME: dialect.py -> parser
    def visit_StringFind(self, op, *, arg, substr, start, end):
        return self.strfind_impl(arg=arg, substr=substr, start=start, end=end)
    def visit_TimestampFromUNIX(self, op, *, arg, unit):
        if unit.short == 's':
            return self.f.from_unixts(arg)
        if unit.short == 'ms':
            return self.f.from_unixtsms(arg)
        raise com.UnsupportedOperationError(
            "SQreamDB only supports `TimestampFromUNIX` with seconds.")
    def visit_ArrayIndex(self, op, *, arg, index):
        return sge.Bracket(this=arg, expressions=[index])
    def visit_ArrayAll(self, op, *, arg):
        return self.f.array_position(arg, False).is_(NULL)
    def visit_ArrayAny(self, op, *, arg):
        return sge.not_(self.f.array_position(arg, True).is_(NULL))
    def visit_ArrayConcat(self, op, *, arg):
        return reduce(lambda x, y: sge.DPipe(this=x, expression=y), arg) 
    def visit_ArrayContains(self, op, *, arg, other):
        return sge.not_(self.f.array_position(arg, other).is_(NULL))
    def visit_ArrayPosition(self, op, *, arg, other): #FIXME: why - 1 ???
        return sge.func('array_position', arg, other) + 1
    def visit_ArrayCollect(self, op, *, arg, where, order_by, include_null, distinct): #TODO: use all arguments
        return self.agg.array_agg(arg, where=where)
    def visit_TableUnnest(
        self,
        op,
        *,
        parent,
        column,
        column_name: str,
        offset: str | None,
        keep_empty: bool,
    ):
        quoted = self.quoted

        column_alias = sg.to_identifier("table_unnest_column", quoted=quoted)

        parent_alias = parent.alias_or_name

        parent_schema = op.parent.schema
        overlaps_with_parent = column_name in parent_schema
        computed_column = sge.Unnest(
            expressions=[column],
            alias=sg.to_identifier(column_name, quoted=quoted),
            offset=offset).as_(column_alias, quoted=quoted)

        selcols = []

        if overlaps_with_parent:
            column_alias_or_name = column.alias_or_name
            selcols.extend(
                sg.column(col, table=parent_alias, quoted=quoted)
                if col != column_alias_or_name
                else computed_column
                for col in parent_schema.names)
        else:
            selcols.append(sge.Column(
                this=sge.Star(),
                table=sg.to_identifier(parent_alias, quoted=quoted)))

        if offset is not None:
            offset_name = offset
            offset = sg.to_identifier(offset_name, quoted=quoted)
            selcols.append((offset - 1).as_(offset_name, quoted=quoted))

        return sg.select(*selcols).from_(parent)
    def visit_TimestampBucket(self, op, *, arg, interval, offset):
        if interval.args['this'] != sge.Literal.string('1'):
            raise com.UnsupportedOperationError(f"Unsupported truncate unit: {interval}")
        return self.f.trunc(arg, interval.args['unit'])
    def visit_GroupConcat(self, op, *, arg):
        pass
    def visit_FindInSet(self, op, *, needle, values):
        return self.f.coalesce(
            self.f.array_position(self.f.array(*values), needle),
            0,
        )
