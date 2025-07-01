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
from ibis.backends.sql.compilers import PostgresCompiler
from ibis.backends.sql.compilers.base import C

from .compiler import SqreamCompiler

logger = logging.getLogger("ibis.sqream")
import ibis.backends.sql.compilers as sc
class Backend(SQLBackend):
    name = "sqream"
    
    #dialect = "postgres"
    #compiler = SqreamCompiler
    #compiler_class = SqreamCompiler
    #compiler=sc.postgres.compiler
    #dialect = 'postgres'
    dialect = "sqlite"
    compiler = sc.sqlite.compiler
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        # The dialect used for SQL generation is now "postgres"
        #traceback.print_stack()
        print("SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",type(query))
        print("RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR",query)
        if not isinstance(query, str):
            query = query.sql(dialect=self.dialect)
        cursor = self.con.cursor()
        try:
            logger.info(f"Executing SQL: {query}")
            print("BEFORE QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ" ,query)           
            cursor.execute(query, **kwargs)
            print("AFTER QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ" ,query)
            yield cursor
        finally:
            cursor.close()

    def list_tables(self, *, like: str | None = None, schema: str | None = None) -> list[str]:
        query = sg.select(C.table_name).from_(sg.table("tables", db="sqream_catalog"))
        conditions =""
        #conditions = [C.table_type.isin(sge.convert("BASE TABLE"), sge.convert("VIEW"))]
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
        catalog: str | None = None,
    ) -> sch.Schema:
        
        if catalog is not None:
            logger.info("SQreamDB does not support catalogs, the 'catalog' argument will be ignored.")
        
        
         
        query = (
            
            sg.select(C.column_name, C.type_name, sge.false())
            #sg.select('get_col_name(' +C.column_name+')', C.type_name, False)
            .from_(sg.table('view_sqream_catalog_columns', db='public'))
            .where(C.table_name.eq(sge.convert(table_name)))
        )
        
        # The 'database' parameter now correctly matches the variable name
        if database:
            query = query.where(C.table_schema.eq(sge.convert(database)))
        #query = query.order_by(C.ordinal_position)
        #print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",query)
        with self._safe_raw_sql(query) as cur:
            rows = cur.fetchall()
        if not rows:
            raise com.TableNotFound(f"Table not found :" + table_name)

        names, types, nullables = zip(*rows)
        ibis_types = [
            self.compiler.type_mapper.from_string(t, nullable=n == "YES")
            for t, n in zip(types, nullables)
        ]
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
        
        if overwrite:
            self.drop_table(name, schema=database, force=True)
            
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
        create_stmt_sql = f"CREATE TABLE {target_sql} ({columns_sql})"
        #print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%',create_stmt_sql)
        logger.info(f"Final generated SQL to be executed: {create_stmt_sql}")
        
        with self._safe_raw_sql(create_stmt_sql):
            pass
        logger.info("CREATE TABLE statement executed successfully.")

        if obj is not None:
            self.insert(name, obj, schema=database, overwrite=False)
            
        return self.table(name, database=database)
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

        # This is the crucial step: call .fetchall() to get the data
        # out of the cursor and into a list of tuples.
        data = cursor.fetchall()
        
        # Now, create the DataFrame from the list of data.
        df = pd.DataFrame.from_records(data, columns=schema.names)
        
        # Here you could add more complex type conversions if needed
        # For example, converting string dates to datetime objects.
        return df
    
    def insert(self, name: str, obj: pd.DataFrame | ir.Table, *, schema: str | None = None, overwrite: bool = False):
        table = sg.table(name, db=schema, quoted=self.compiler.quoted)
        if overwrite:
            with self._safe_raw_sql(sge.Delete(this=table)):
                pass
        if not isinstance(obj, ir.Expr):
            obj = ibis.memtable(obj)
        query = sge.Insert(this=table, expression=self.compile(obj))
        with self._safe_raw_sql(query):
            pass
