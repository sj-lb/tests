# ibis_sqreamdb/compiler.py

from ibis.expr import operations as ops, datatypes as dt
from ibis.backends.sql.datatypes import SqlglotType
from ibis.backends.sql.compilers.base import NULL, AggGen, SQLGlotCompiler
from ibis.backends.sql.compilers import SQLiteCompiler, PostgresCompiler
import ibis.common.exceptions as com

import sqlglot.expressions as sge
# from sqlglot.dataframe.sqlglot import DataType # Import DataType from sqlglot
from .dialect import SQreamDialect

# It is cleaner to define a simple dialect for SQREAM rather than inheriting
# all the specifics from the Postgres compiler.
#class SqreamDialect(PyDialect):
#    """A class to represent the SQREAM dialect for sqlglot."""
#    pass

class SQreamType(SqlglotType):
    dialect = SQreamDialect()

    # @classmethod
    # def to_string(cls, dtype: dt.DataType) -> str:
    #     return 'TEXT' if isinstance(dtype, dt.String) else super().to_string(dtype)

class SqreamCompiler(SQLGlotCompiler):
    """
    The Ibis compiler for the SQREAM backend.

    This class translates Ibis expressions into SQL by implementing
    special "visitor" methods for operations that SQREAM handles
    uniquely.
    """
    dialect = SQreamDialect
    type_mapper = SQreamType
    agg = AggGen(supports_filter=True)


    UNSUPPORTED_OPS = (
        ops.Clip,
        ops.Least,
        ops.Greatest
        # ops.Levenshtein,
        # ops.RegexSplit,
        # ops.StringSplit,
        # ops.IsNan,
        # ops.IsInf,
        # ops.Covariance,
        # ops.Correlation,
        # ops.Median,
        # ops.ApproxMedian,
        # ops.Array,
        # ops.ArrayConcat,
        # ops.ArrayStringJoin,
        # ops.ArrayContains,
        # ops.ArrayFlatten,
        # ops.ArrayLength,
        # ops.ArraySort,
        # ops.ArrayStringJoin,
        # ops.CountDistinctStar,
        # ops.IntervalBinary,
        # ops.IntervalAdd,
        # ops.IntervalSubtract,
        # ops.IntervalMultiply,
        # ops.IntervalFloorDivide,
        # ops.TimestampBucket,
        # ops.TimestampDiff,
        # ops.StringToDate,
        # ops.StringToTimestamp,
        # ops.StringToTime,
        # ops.TimeDelta,
        # ops.TimestampDelta,
        # ops.TryCast,
    )

    SIMPLE_OPS = {
        ops.Cot: "cot",
        ops.Count: "count",
        ops.TypeOf: "typeof",
        ops.Log10: " log10", # doesn't work without leading whitespace
        ops.Ln: " log",
        # ops.Least: "min",
    }

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
    def visit_ArgMaxxxx(self, op: ops.ArgMax, *, arg: sge.Expression, key: sge.Expression, where: sge.Expression | None) -> sge.Expression:
        ibis_table_rel = op.arg.rel
        table_expr = sge.Table(
            this=sge.Identifier(this=ibis_table_rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True)))
        inner_max_subquery = sge.Select(expressions=[sge.Max(this=key)]).from_(table_expr.copy())
        if where:
            inner_max_subquery = inner_max_subquery.where(where)

        scalar_argmax_subquery = sge.Select(expressions=[arg]).from_(table_expr.copy())

        comparison_condition = sge.EQ(this=key, expression=sge.Paren(this=inner_max_subquery))

        if where:
            scalar_argmax_subquery = scalar_argmax_subquery.where(sge.And(where, comparison_condition))
        else:
            scalar_argmax_subquery = scalar_argmax_subquery.where(comparison_condition)

        scalar_argmax_subquery = scalar_argmax_subquery.order_by(
            sge.Ordered(this=arg, desc=False)) # .order_by() takes Ordered expressions directly).limit(sge.Literal.number(1)

        return sge.Paren(this=scalar_argmax_subquery)

    def visit_ArgMax(self, op: ops.ArgMax, *, arg: sge.Expression, key: sge.Expression, where: sge.Expression | None) -> sge.Expression:
        ibis_table_rel = op.arg.rel

        main_table_sqlglot = sge.Table(
            this=sge.Identifier(this=ibis_table_rel.name, quoted=True),
            alias=sge.Alias(this=sge.Identifier(this=arg.table, quoted=True)))

        inner_max_subquery = sge.Select(expressions=[sge.Max(this=key).as_("max_val")]).from_(main_table_sqlglot.copy())
        aliased_inner_max_subquery = inner_max_subquery.as_("t1")

        join_condition = sge.EQ(
            this=key,
            expression=sge.Column(this=sge.Identifier(this="max_val", quoted=True), table=sge.Identifier(this="t1", quoted=True)))

        final_query = sge.Select(expressions=[arg]).from_(main_table_sqlglot)
        print(f'\033[34;1mFINAL QUERY THE FINAL FINALING: \033[33m{final_query}\033[m') # SELECT "t0"."id" FROM "ibis_test_argmax" AS "t0";
        final_query = final_query.join(aliased_inner_max_subquery, on=join_condition)
        print(f'\033[34;1mFINAL QUERY AFTER JOIN: \033[33m{final_query}\033[m') # SELECT "t0"."id" FROM "ibis_test_argmax" AS "t0" JOIN SELECT MAX("t0"."value") AS max_val FROM "ibis_test_argmax" AS "t0" AS t1 ON "t0"."value" = "t1"."max_val";
        
        return final_query.where(where) if where else final_query
    def visit_TimestampAdd(self, op, *, left, right):
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
        sql_unit = sge.Var(this=unit.upper())

        return self.f.dateadd(sql_unit, sql_amount, left)
    def visit_TimestampSub(self, op, *, left, right): # TODO: reuse TimestampAdd
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
        sql_unit = sge.Var(this=unit.upper())

        return self.f.dateadd(sql_unit, -sql_amount, left)
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
            "us": "us",
        }

        if (raw_unit := unit_mapping.get(unit.short)) is None:
            raise com.UnsupportedOperationError(
                f"Unsupported truncate unit {unit.short!r}"
            )

        return self.f.trunc(arg, sge.Identifier(this=raw_unit))