# ibis_sqreamdb/backend.py
from __future__ import annotations
import traceback
import contextlib
import logging
from typing import Any
from urllib.parse import ParseResult, unquote_plus

import pandas as pd
import sqlglot as sg
import sqlglot.expressions as sge

import ibis
import ibis.common.exceptions as com
import ibis.expr.operations as ops
import ibis.expr.schema as sch
import ibis.expr.types as ir
from ibis.backends.sql import SQLBackend
from ibis.backends.sql.compilers.base import C

from .compiler import SqreamCompiler
from .dialect import SQreamDialect

logger = logging.getLogger("ibis.sqream")
import ibis.backends.sql.compilers as sc

pymods_names = {
    ops.ArrayMax: 'array_max',
    ops.ArrayMin: 'array_min',
    ops.ArrayMean: 'array_mean',
    ops.ArraySum: 'array_sum',
    ops.ArraySort: 'array_sort',
    ops.ArrayRepeat: 'array_repeat',
    ops.ArraySlice: 'array_slice',
    ops.ArrayFilter: 'array_filter',
    ops.ArrayMap: 'array_map',
    ops.ArrayDistinct: 'array_distinct',
    ops.ArrayIntersect: 'array_intersect',
    ops.ArrayUnion: 'array_union'
}

class Backend(SQLBackend):
    name = 'sqream'
    compiler = SqreamCompiler()
    dialect = SQreamDialect()
    pymods_entries = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_connect() # for range tests
         # Keep this from our previous steps
    def _from_url(self, url: ParseResult, **kwargs):
        connect_kwargs = kwargs.copy()
        if url.username:
            connect_kwargs["user"] = unquote_plus(url.username)
        if url.password:
            connect_kwargs["password"] = unquote_plus(url.password)
        if url.hostname:
            connect_kwargs["host"] = url.hostname
        if url.port:
            connect_kwargs["port"] = url.port
        if url.path:
            connect_kwargs["database"] = url.path[1:]
        self.connect(**connect_kwargs)
        return self

    @property
    def current_database(self) -> str:
        with self._safe_raw_sql("select current_database();") as cur:
            (db,) = cur.fetchone()
            return db

    @property
    def version(self) -> str:
        with self._safe_raw_sql("select proc_version();") as cur:
            (version,) = cur.fetchone()
            return version

    def do_connect(self, **kwargs: Any) -> None:
        import pysqream
        self._con_kwargs = kwargs.copy()
        if "username" not in self._con_kwargs and "user" in self._con_kwargs:
            self._con_kwargs["username"] = self._con_kwargs.pop("user")
        
        self._con_kwargs.setdefault("host", "127.0.0.1")
        self._con_kwargs.setdefault("port", 5000)
        self._con_kwargs.setdefault("database", "master")
        self._con_kwargs.setdefault("username", "sqream")
        self._con_kwargs.setdefault("password", "sqream")
        
        self.con = pysqream.connect(**self._con_kwargs)

    @contextlib.contextmanager
    def _safe_raw_sql(self, query, **kwargs):
        if not isinstance(query, str):
            query = query.sql(dialect=self.dialect)
        print(f'\033[32;1m{__name__}\033[33m::\033[32m_safe_raw_sql\033[33m::\033[32mquery \033[33m=\033[34m {query}\033[m')
        cursor = self.con.cursor()
        try:
            logger.info(f"Executing SQL: {query}")
            cursor.execute(query, **kwargs)
            yield cursor
        finally:
            cursor.close()

    def list_tables(self, *, like: str | None = None, schema: str | None = None) -> list[str]:
        query = sg.select(C.table_name).from_(sg.table("tables", db="sqream_catalog"))
        conditions =""
        if schema:
            conditions.append(C.table_schema.eq(sge.convert(schema)))
        query = query.where(*conditions)
        with self._safe_raw_sql(query) as cur:
            results = [r[0] for r in cur.fetchall()]
        return self._filter_with_like(results, like)

    def get_schema(
        self,
        table_name: str,
        *,
        database: str | None = None, # <-- FIX: Changed parameter name from 'schema' to 'database'
        catalog: str | None = None
    ) -> sch.Schema:
        if catalog is not None:
            logger.info("SQreamDB does not support catalogs, the 'catalog' argument will be ignored.")

        query = (sg.select(sg.func('ibis_table_details', sge.convert('public.' + table_name))))
        # The 'database' parameter now correctly matches the variable name
        if database:
            query = query.where(C.table_schema.eq(sge.convert(database)))
        #query = query.order_by(C.ordinal_position)
        with self._safe_raw_sql(query) as cur:
            rows = cur.fetchall()
        if not rows:
            raise com.TableNotFound(f"Table not found :" + table_name)
        names, types, nullables = zip(*rows)
        nullables = [False if n == '0' else True for n in nullables]

        ibis_types = [
            self.compiler.type_mapper.from_string(type_string=t, nullable=n)
            for t, n in zip(types, nullables)]
        return sch.Schema(dict(zip(names, ibis_types)))
    def create_table(
        self,
        name: str,
        obj: ir.Table | pd.DataFrame | None = None,
        *,
        schema: sch.Schema | None = None,
        database: str | None = None,
        temp: bool = False,
        overwrite: bool = False,
    ):
        logger.info(f"--- ENTERING CREATE_TABLE for table '{name}' ---")

        if obj is None and schema is None:
            raise ValueError("Either `obj` or `schema` must be specified")

        ibis_schema = ibis.schema(schema) if schema is not None else ibis.memtable(obj).schema()
        
        # --- THE DEFINITIVE FIX: Manually build the SQL string ---

        # 1. Get the quoted table name (e.g., "my_schema"."my_table")
        target_sql = sg.table(name, db=database, quoted=self.compiler.quoted).sql(self.dialect)
        
        # 2. Manually build the list of column definitions as strings
        column_parts = []
        for col_name, ibis_dtype in ibis_schema.items():
            # Get the SQL type (e.g., 'BIGINT', 'NVARCHAR(1000)') from our type mapper
            sql_type_str = self.compiler.type_mapper.to_string(ibis_dtype)
            # Get the quoted column name (e.g., '"a"')
            quoted_col_name = sg.to_identifier(col_name, quoted=self.compiler.quoted).sql(self.dialect)
            # Append the full column definition (e.g., '"a" BIGINT') to our list
            column_parts.append(f"{quoted_col_name} {sql_type_str}")
        
        # 3. Join the parts together: '"a" BIGINT, "b" NVARCHAR(1000)'
        columns_sql = ", ".join(column_parts)
        if not columns_sql:
            raise com.IbisError("Cannot create a table with no columns")

        # 4. Assemble the final, complete SQL string using a simple f-string
        cmd = 'CREATE OR REPLACE' if overwrite else 'CREATE'
        create_stmt_sql = f'{cmd} TABLE {target_sql} ({columns_sql})'
        logger.info(f"Final generated SQL to be executed: {create_stmt_sql}")
        
        with self._safe_raw_sql(create_stmt_sql):
            pass
        logger.info("CREATE TABLE statement executed successfully.")

        if obj is not None:
            self.insert(name, obj, schema=database, overwrite=False)
            
        return self.table(name, database=database)
    def create_pymods(self, name, args, ret):
        entry = f'[name=\'{name}\', arguments [{", ".join([self.compiler.type_mapper.to_string(t) for t in args])}], returns scalar {self.compiler.type_mapper.to_string(ret)}, gpu=true]'
        self.pymods_entries = ', '.join([self.pymods_entries, entry]) if self.pymods_entries else entry
        print(f'\033[34;1mENTRIES: \033[33m{self.pymods_entries}\033[m')
        with self._safe_raw_sql(f"CREATE OR REPLACE MODULE m_internal OPTIONS(PATH='...', entry_points=[{self.pymods_entries}]);"):
            pass
    def drop_table(self, name: str, *, schema: str | None = None, force: bool = False) -> None:
        drop_stmt = sg.exp.Drop(
            kind="TABLE", this=sg.table(name, db=schema, quoted=self.compiler.quoted), exists=force
        )
        with self._safe_raw_sql(drop_stmt):
            pass

    def _get_schema_using_query(self, query: str) -> sch.Schema:
        sql_query = sg.parse_one(query, read=self.dialect).limit(0)
        with self._safe_raw_sql(sql_query) as cursor:
            if not cursor.description:
                raise com.IbisError("Query did not return any columns")
            names = [desc[0] for desc in cursor.description]
            types = [desc[1] for desc in cursor.description]
            ibis_types = [self.compiler.type_mapper.from_string(t) for t in types]
            return sch.Schema(dict(zip(names, ibis_types)))

    def _register_in_memory_table(self, op: ops.InMemoryTable):
        self.create_table(op.name, obj=op.data.to_frame(), temp=True)
    def _fetch_from_cursor(
        self, cursor: pysqream.Cursor, schema: sch.Schema
    ) -> pd.DataFrame:
        """
        Fetch all rows from a pysqream cursor and load them into a
        pandas DataFrame.
        """
        import pandas as pd

        data = cursor.fetchall()
        
        df = pd.DataFrame.from_records(data, columns=schema.names)
        
        return df

    def insert(self, name: str, obj: pd.DataFrame | ir.Table, *, schema: str | None = None, overwrite: bool = False):
        """
        Insert data into a table.
        This version correctly handles pandas DataFrames directly.
        """
        table = sg.table(name, db=schema, quoted=self.compiler.quoted)
        if overwrite:
            with self._safe_raw_sql(sge.Delete(this=table)):
                pass
        if isinstance(obj, ir.Table):
            # This path is for inserting from another ibis Table
            query = sge.Insert(this=table, expression=self.compile(obj))
            with self._safe_raw_sql(query):
                pass
        elif isinstance(obj, pd.DataFrame):
            # This is the direct, robust path for pandas DataFrames.
            if obj.empty:
                return
            column_names = ", ".join(sg.to_identifier(c, quoted=True).sql(self.dialect) for c in obj.columns)
            placeholders = ", ".join(["?"] * len(obj.columns))
            insert_sql = f"INSERT INTO {table.sql(self.dialect)} ({column_names}) VALUES ({placeholders})"
            print(f'\033[32;1mINSERT SQL: \033[33m{insert_sql}\033[m')
            # SQreamDB's executemany expects a list of tuples.
            # Replace NaN with None, as databases use NULL.
            data_to_insert = []
            for row in obj.itertuples(index=False, name=None):
                processed_row_elements = []
                for v in row:
                    if isinstance(v, list):
                        for item in v:
                            item = None if pd.isna(item) else item
                    elif pd.isna(v):
                        v = None
                    processed_row_elements.append(v)
                data_to_insert.append(tuple(processed_row_elements))
            print(f'\033[34;1mdata_to_insert: \033[33m{data_to_insert}\033[m')
            with self.con.cursor() as cursor:
                try:
                    logger.info(f"Executing INSERT with {len(data_to_insert)} rows into {name}")
                    cursor.executemany(insert_sql, data_to_insert)
                except Exception as e:
                    logger.error("Insert failed.", exc_info=True)
                    print(f'\033[31mERROR ENCOUNTERED, PRINTING TRACEBACK:\033[m\n{traceback.format_exc()}')
                    raise e

    def execute(self, expr, params, limit, **kwargs):
        for arg in expr.op().args:
            if isinstance(arg, dict):
                for a in arg.values():
                    if isinstance(a, tuple(pymods_names.keys())):
                        try:
                            self.create_pymods(name=pymods_names[type(a)], args=[a.arg.dtype], ret=a.dtype)
                        except Exception as e:
                            logger.error('failed to create module for array_max', exc_info=True)
                            raise com.IbisError("Failed to set up ArrayMax UDF: " + str(e))
        return super().execute(expr, params=params, limit=limit, **kwargs)