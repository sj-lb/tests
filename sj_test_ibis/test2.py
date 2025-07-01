import os
import sys
import logging
import pandas as pd
import numpy as np
import pytest
import ibis
from ibis import _
import sqlite3
# Use the direct connect function that is known to work
from ibis_sqreamdb import connect

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/ibis_sqream_all_ops_test.log", mode='w'),
        logging.StreamHandler(sys.stdout)])

# --- Database Connection Details ---
HOST = os.environ.get("IBIS_SQREAM_HOST", "192.168.4.31")
PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
USER = os.environ.get("IBIS_SQREAM_USER", "sqream")
PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")
CLUSTERED = os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"

# --- Helper Function for Running a Single Test Case ---
def pandas_dtype_to_ibis_string(dtype, col=None):
    """
    Manually and explicitly converts pandas dtypes to Ibis type strings.
    This is the most robust way to avoid schema inference errors.
    """
    ret: str = ''
    suf: str = ''
    if dtype.name == 'object' and col is not None and len(col) > 0:
        # Check if it's a list (or similar iterable) and try to infer inner type
        first_non_null_item = next((item for item in col if item is not None and isinstance(item, (list, tuple))), None)

        if first_non_null_item:
            ret += 'array<'
            suf = '>'
            dtype = pd.DataFrame(col.to_list()).dtypes[0]
    if pd.api.types.is_integer_dtype(dtype):
        ret += f"int{dtype.itemsize * 8}"
    elif pd.api.types.is_float_dtype(dtype):
        ret += f"float{dtype.itemsize * 8}"
    elif pd.api.types.is_bool_dtype(dtype):
        ret += "boolean"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        ret += "timestamp"
    elif pd.api.types.is_string_dtype(dtype):
        ret += "string"
    else:
        raise TypeError(f"Unsupported pandas dtype for schema creation: {dtype}")
    ret += suf
    print(f'\033[34;1mpd_to_ibis type: \033[33m{ret}\033[m')
    return ret

def run_test_case(op_name, data: pd.DataFrame, ibis_expr_func, pandas_expr_func):
    """
    A helper function to encapsulate the test logic for a single operation.
    """
    logging.info(f"--- Running Test: {op_name} ---")
    
    con = connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

    table_name = f"ibis_test_{op_name.lower()}"
    
    try:
        # ** THE FINAL FIX: Manually create the schema from basic strings **
        schema_dict = {
            name: pandas_dtype_to_ibis_string(dtype, data[col]) for col, (name, dtype) in zip(data.columns, data.dtypes.items())}
        schema = ibis.schema(schema_dict)
        
        con.create_table(table_name, schema=schema, overwrite=True)
        logging.info(f"Created empty table '{table_name}' with schema: {schema}")

        con.insert(table_name, obj=data)
        logging.info(f"Inserted data into '{table_name}'")
        
        ibis_table = con.table(table_name)
        ibis_expr = ibis_expr_func(ibis_table)
        
        expected_df = pandas_expr_func(data)
            
        logging.info("Executing Ibis query...")
        ibis_result_df = ibis_expr.execute()

        # Standardize dataframes for robust comparison
        if isinstance(ibis_result_df, pd.Series):
            ibis_result_df = ibis_result_df.to_frame()
        if isinstance(expected_df, pd.Series):
            expected_df = expected_df.to_frame()

        expected_cols = sorted(list(expected_df.columns))
        ibis_result_df = ibis_result_df[expected_cols].sort_values(by=expected_cols).reset_index(drop=True)
        expected_df = expected_df[expected_cols].sort_values(by=expected_cols).reset_index(drop=True)
        
        for col in expected_df.columns:
            if col in ibis_result_df.columns:
                expected_df[col] = expected_df[col].astype(ibis_result_df[col].dtype)

        logging.info("Ibis Result:\n%s", ibis_result_df)
        logging.info("Pandas Expected Result:\n%s", expected_df)

        pd.testing.assert_frame_equal(ibis_result_df, expected_df, check_dtype=True)
        logging.info(f"✅ Assertion successful for operation: {op_name}")
    finally:
        logging.info(f"Cleaning up table '{table_name}'...")
        try:
            con.drop_table(table_name, force=True)
            logging.info(f"Cleaned up table '{table_name}'")
        except Exception as e:
            logging.error(f"Could not drop table {table_name}. Reason: {e}")

def run_test_case2(op_name, data: dict[str, pd.DataFrame], ibis_expr_func, pandas_expr_func):
    """
    A helper function to encapsulate the test logic for a single operation,
    supporting multiple input tables.

    Args:
        op_name (str): The name of the operation being tested.
        data (dict[str, pd.DataFrame]): A dictionary where keys are table names
                                        and values are pandas DataFrames to be inserted.
        ibis_expr_func (callable): A function that takes a dictionary of Ibis tables
                                   (keys matching the 'data' keys) and returns an Ibis expression.
        pandas_expr_func (callable): A function that takes a dictionary of pandas DataFrames
                                     (keys matching the 'data' keys) and returns the expected
                                     pandas DataFrame result.
    """
    logging.info(f"--- Running Test: {op_name} ---")

    con = connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

    created_tables = [] # To keep track of tables created for cleanup

    try:
        ibis_tables = {}
        for table_key, df in data.items():
            # Generate a unique table name for each DataFrame in the dict
            table_name = f"ibis_test_{op_name.lower()}_{table_key.lower()}"
            created_tables.append(table_name)

            # Manually create the schema from basic strings
            schema_dict = {
                col: pandas_dtype_to_ibis_string(dtype) for col, dtype in df.dtypes.items()}
            schema = ibis.schema(schema_dict)

            con.create_table(table_name, schema=schema, overwrite=True)
            logging.info(f"Created empty table '{table_name}' with schema: {schema}")

            con.insert(table_name, obj=df)
            logging.info(f"Inserted data into '{table_name}'")

            ibis_tables[table_key] = con.table(table_name)

        ibis_expr = ibis_expr_func(ibis_tables)
        expected_df = pandas_expr_func(data)

        logging.info("Executing Ibis query...")
        ibis_result_df = ibis_expr.execute()

        # Standardize dataframes for robust comparison
        if isinstance(ibis_result_df, pd.Series):
            ibis_result_df = ibis_result_df.to_frame()
        if isinstance(expected_df, pd.Series):
            expected_df = expected_df.to_frame()

        expected_cols = sorted(list(expected_df.columns))
        # Ensure columns exist before accessing them, especially when sorting
        common_cols = [col for col in expected_cols if col in ibis_result_df.columns]
        if common_cols:
            ibis_result_df = ibis_result_df[common_cols].sort_values(by=common_cols).reset_index(drop=True)
        else: # Handle cases where expected_df might be empty or have no common columns
            ibis_result_df = ibis_result_df.copy().reset_index(drop=True)

        expected_df = expected_df[expected_cols].sort_values(by=expected_cols).reset_index(drop=True)

        for col in expected_df.columns:
            if col in ibis_result_df.columns:
                expected_df[col] = expected_df[col].astype(ibis_result_df[col].dtype)

        logging.info("Ibis Result:\n%s", ibis_result_df)
        logging.info("Pandas Expected Result:\n%s", expected_df)

        pd.testing.assert_frame_equal(ibis_result_df, expected_df, check_dtype=True)
        logging.info(f"✅ Assertion successful for operation: {op_name}")

    finally:
        for table_name_to_drop in created_tables:
            logging.info(f"Cleaning up table '{table_name_to_drop}'...")
            try:
                con.drop_table(table_name_to_drop, force=True)
                logging.info(f"Cleaned up table '{table_name_to_drop}'")
            except Exception as e:
                logging.error(f"Could not drop table {table_name_to_drop}. Reason: {e}")

# --- Test Functions For Each Operation ---

def test_op_sum():
    run_test_case(
        op_name='Sum',
        data=pd.DataFrame({'value': [1, 2, 3, None, 4]}),
        ibis_expr_func=lambda t: t.aggregate(sum=t.value.sum()),
        pandas_expr_func=lambda df: pd.DataFrame({'sum': [df['value'].sum()]}))
def test_op_mean():
    run_test_case(
        op_name='Mean',
        data=pd.DataFrame({'value': [1, 2, 3, None, 4]}),
        ibis_expr_func=lambda t: t.aggregate(mean=t.value.mean()),
        pandas_expr_func=lambda df: pd.DataFrame({'mean': [df['value'].mean()]}))
def test_op_count():
    run_test_case(
        op_name='Count',
        data=pd.DataFrame({'value': [1, 2, 3, None, 4]}),
        ibis_expr_func=lambda t: t.aggregate(count=t.value.count()),
        pandas_expr_func=lambda df: pd.DataFrame({'count': [df['value'].count()]}, dtype=np.int64))
def test_op_count_distinct():
    run_test_case(
        op_name='CountDistinct',
        data=pd.DataFrame({'value': [1, 2, 1, None, 4, 2]}),
        ibis_expr_func=lambda t: t.aggregate(nunique=t.value.nunique()),
        pandas_expr_func=lambda df: pd.DataFrame({'nunique': [df['value'].nunique()]}, dtype=np.int64))
def test_op_min():
    run_test_case(
        op_name='Min',
        data=pd.DataFrame({'value': [10, 2, 30, None, 4]}),
        ibis_expr_func=lambda t: t.aggregate(min=t.value.min()),
        pandas_expr_func=lambda df: pd.DataFrame({'min': [df['value'].min()]}))
def test_op_max():
    run_test_case(
        op_name='Max',
        data=pd.DataFrame({'value': [10, 2, 30, None, 4]}),
        ibis_expr_func=lambda t: t.aggregate(max=t.value.max()),
        pandas_expr_func=lambda df: pd.DataFrame({'max': [df['value'].max()]}))
def test_op_groupby_aggregate():
    """
    Tests a groupby operation followed by an aggregation.
    """
    run_test_case(
        op_name='Groupby_Aggregate',
        data=pd.DataFrame({
            'g': ['a', 'b', 'a', 'b', 'a'],
            'v': [10, 20, 11, 22, 12]
        }),
        ibis_expr_func=lambda t: t.group_by('g').aggregate(total=t.v.sum()),
        pandas_expr_func=lambda df: df.groupby('g', as_index=False).agg(total=('v', 'sum')))
def test_op_round():
    run_test_case(
        op_name='Round',
        data=pd.DataFrame({'value': [1.234, 2.678, 3.5]}),
        ibis_expr_func=lambda t: t.select(rounded=t.value.round(2)),
        pandas_expr_func=lambda df: pd.DataFrame({'rounded': df['value'].round(2)}))
def test_op_log10():
    run_test_case(
        op_name='Log10',
        data=pd.DataFrame({'value': [1.0, 10.0, 100.0]}),
        ibis_expr_func=lambda t: t.select(log_val=t.value.log10()),
        pandas_expr_func=lambda df: pd.DataFrame({'log_val': np.log10(df['value'])}))
def test_op_abs():
    run_test_case(
        op_name='Abs',
        data=pd.DataFrame({'value': [-10, 20, -30]}),
        ibis_expr_func=lambda t: t.select(abs_val=t.value.abs()),
        pandas_expr_func=lambda df: pd.DataFrame({'abs_val': df['value'].abs()}))
def test_op_string_length():
    run_test_case(
        op_name='StringLength',
        data=pd.DataFrame({'s': ['apple', 'banana', None]}),
        ibis_expr_func=lambda t: t.select(length=t.s.length()),
        pandas_expr_func=lambda df: pd.DataFrame({'length': df['s'].str.len()}))
def test_op_string_concat():
    run_test_case(
        op_name='StringConcat',
        data=pd.DataFrame({'a': ['hello', 'ibis'], 'b': [' world', ' rocks']}),
        ibis_expr_func=lambda t: t.select(concatted=(t.a + t.b)),
        pandas_expr_func=lambda df: pd.DataFrame({'concatted': df['a'] + df['b']}))
#SELECT INSTR("t0"."s", 'an') >= 1 AS "contains" FROM "ibis_test_stringcontains" AS "t0" ;
#CREATE TABLE "ibis_test_stringcontains" ("s" TEXT);
@pytest.mark.skip(reason="This operation is not yet implemented Sqream ")
def test_op_string_contains():
    run_test_case(
        op_name='StringContains',
        data=pd.DataFrame({'s': ['apple', 'banana', 'orange']}),
        ibis_expr_func=lambda t: t.select(contains=t.s.contains('an')),
        pandas_expr_func=lambda df: pd.DataFrame({'contains': df['s'].str.contains('an')}))
def test_op_endswith():
    run_test_case(
        op_name='EndsWith',
        data=pd.DataFrame({'s': ['apple', 'banana', 'orange']}),
        ibis_expr_func=lambda t: t.select(ends=t.s.endswith('e')),
        pandas_expr_func=lambda df: pd.DataFrame({'ends': df['s'].str.endswith('e')}))
#SELECT CAST(STRFTIME('%Y', "t0"."ts") AS INTEGER) AS "year" FROM "ibis_test_extractyear" AS "t0"
#CREATE TABLE "ibis_test_extractyear" ("ts" TIMESTAMP)
@pytest.mark.skip(reason="This operation is not yet implemented in the backend")
def test_op_extract_year():
    run_test_case(
        op_name='ExtractYear',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-15', '2024-05-20'])}),
        ibis_expr_func=lambda t: t.select(year=t.ts.year()),
        pandas_expr_func=lambda df: pd.DataFrame({'year': df['ts'].dt.year}))
#SELECT CAST(STRFTIME('%j', "t0"."ts") AS INTEGER) AS "doy" FROM "ibis_test_extractdayofyear" AS "t0"
#CREATE TABLE "ibis_test_extractdayofyear" ("ts" TIMESTAMP)
@pytest.mark.skip(reason="This operation is not yet implemented in the backend")    
def test_op_extract_day_of_year():
    run_test_case(
        op_name='ExtractDayOfYear',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-15', '2024-05-20'])}),
        ibis_expr_func=lambda t: t.select(doy=t.ts.day_of_year()),
        pandas_expr_func=lambda df: pd.DataFrame({'doy': df['ts'].dt.dayofyear}))
def test_op_case():
    run_test_case(
        op_name='Case',
        data=pd.DataFrame({'v': [10, 25, 40]}),
        ibis_expr_func=lambda t: t.select(category=ibis.cases((t.v < 20, "low"), (t.v > 30, "high"), else_="medium")),
        pandas_expr_func=lambda df: pd.DataFrame({'category': pd.cut(df.v, [0, 19, 30, 100], labels=['high', 'low', 'medium'])}))
def test_op_inner_join():
    run_test_case2(
        op_name='InnerJoin',
        data={'t1': pd.DataFrame({'id': [1, 2, 3], 'v1': ['a', 'b', 'c']}), 't2': pd.DataFrame({'id': [1, 3, 4], 'v2': ['x', 'y', 'z']})},
        ibis_expr_func=lambda tables: tables['t1'].inner_join(tables['t2'], tables['t1'].id == tables['t2'].id).select(tables['t1'].id, tables['t1'].v1, tables['t2'].v2),
        pandas_expr_func=lambda dfs: pd.merge(dfs['t1'], dfs['t2'], on='id', how='inner'))

# --- POSTGRES TEST CASES ---

def test_op_approx_count_distinct():
    run_test_case(
        op_name='ApproxCountDistinct',
        data=pd.DataFrame({'value': [1, 2, 1, 3, 2, 4, 5, 1, 3]}),
        ibis_expr_func=lambda t: t.aggregate(approx_nunique=t.value.approx_nunique()),
        pandas_expr_func=lambda df: pd.DataFrame({'approx_nunique': [df['value'].nunique()]}, dtype=np.int64)) # Pandas doesn't have "approx", so use exact
@pytest.mark.skip(reason="ApproxMedian operation is not defined in SQLite.")
def test_op_approx_median():
    run_test_case(
        op_name='ApproxMedian',
        data=pd.DataFrame({'value': [1, 5, 2, 8, 3, 9, 4, 7]}),
        ibis_expr_func=lambda t: t.aggregate(approx_med=t.value.approx_median()),
        pandas_expr_func=lambda df: pd.DataFrame({'approx_med': [df['value'].median()]})) # Pandas doesn't have "approx", so use exact
@pytest.mark.skip(reason="ApproxQuantile operation is not defined in SQLite.")
def test_op_approx_quantile():
    run_test_case(
        op_name='ApproxQuantile',
        data=pd.DataFrame({'value': list(range(1, 101))}),
        ibis_expr_func=lambda t: t.aggregate(approx_q=t.value.approx_quantile(0.5)),
        pandas_expr_func=lambda df: pd.DataFrame({'approx_q': [df['value'].quantile(0.5)]}))
@pytest.mark.skip(reason="UnsupportedBackendType: Array(value_type=Float64(nullable=True), length=None, nullable=True)")
def test_op_approx_multi_quantile():
    run_test_case(
        op_name='ApproxMultiQuantile',
        data=pd.DataFrame({'value': list(range(1, 101))}),
        ibis_expr_func=lambda t: t.aggregate(approx_quantiles=t.value.approx_quantile([0.25, 0.5, 0.75])),
        pandas_expr_func=lambda df: pd.DataFrame({'approx_quantiles': [list(df['value'].quantile([0.25, 0.5, 0.75]))]}))
# SELECT JSON_EXTRACT(JSON_ARRAY("t0"."id", MAX("t0"."value")), '$[0]') AS "id_at_max" FROM "ibis_test_argmax" AS "t0";
@pytest.mark.skip(reason="Function call not supported: json_array(int, int).")
def test_op_arg_max():
    run_test_case(
        op_name='ArgMax',
        data=pd.DataFrame({'id': [1, 2, 3, 4], 'value': [10, 50, 20, 30]}),
        ibis_expr_func=lambda t: t.aggregate(id_at_max=t.id.argmax(t.value)),
        pandas_expr_func=lambda df: pd.DataFrame({'id_at_max': [df.loc[df['value'].idxmax(), 'id']]}))
# SELECT JSON_EXTRACT(JSON_ARRAY("t0"."id", MAX("t0"."value")), '$[0]') AS "id_at_max" FROM "ibis_test_argmax" AS "t0";
@pytest.mark.skip(reason="Function call not supported: json_array(int, int).")
def test_op_arg_min():
    run_test_case(
        op_name='ArgMin',
        data=pd.DataFrame({'id': [1, 2, 3, 4], 'value': [10, 50, 20, 30]}),
        ibis_expr_func=lambda t: t.aggregate(id_at_min=t.id.argmin(t.value)),
        pandas_expr_func=lambda df: pd.DataFrame({'id_at_min': [df.loc[df['value'].idxmin(), 'id']]}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_all():
    run_test_case(
        op_name='ArrayAll',
        data=pd.DataFrame({'values': [[True, True], [True, False], [False, False]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(all_true=t.values.all()),
        pandas_expr_func=lambda df: pd.DataFrame({'all_true': df['values'].apply(all)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_any():
    run_test_case(
        op_name='ArrayAny',
        data=pd.DataFrame({'values': [[True, True], [True, False], [False, False]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(any_true=t.values.any()),
        pandas_expr_func=lambda df: pd.DataFrame({'any_true': df['values'].apply(any)}))
@pytest.mark.skip(reason="ArrayCollect operation is not defined in SQLite.")
def test_op_array_collect():
    run_test_case(
        op_name='ArrayCollect',
        data=pd.DataFrame({'category': ['A', 'A', 'B'], 'value': [1, 2, 3]}),
        ibis_expr_func=lambda t: t.group_by('category').aggregate(collected_values=t.value.collect()),
        pandas_expr_func=lambda df: df.groupby('category', as_index=False).agg(collected_values=('value', lambda x: list(x))))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_concat():
    run_test_case(
        op_name='ArrayConcat',
        data=pd.DataFrame({'arr1': [[1, 2], [3]], 'arr2': [[4], [5, 6]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(concatenated=t.arr1.concat(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'concatenated': df.apply(lambda row: row['arr1'] + row['arr2'], axis=1)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_contains():
    run_test_case(
        op_name='ArrayContains',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5, 6]], 'val': [2, 7]}, dtype=object),
        ibis_expr_func=lambda t: t.select(contains=t.arr.contains(t.val)),
        pandas_expr_func=lambda df: pd.DataFrame({'contains': df.apply(lambda row: row['val'] in row['arr'], axis=1)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_distinct():
    run_test_case(
        op_name='ArrayDistinct',
        data=pd.DataFrame({'arr': [[1, 2, 2, 3], [4, 5, 4]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(distinct_arr=t.arr.distinct()),
        pandas_expr_func=lambda df: pd.DataFrame({'distinct_arr': df['arr'].apply(lambda x: sorted(list(set(x))))})) # Sort for comparison
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_filter():
    run_test_case(
        op_name='ArrayFilter',
        data=pd.DataFrame({'arr': [[1, 2, 3, 4], [5, 6, 7]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(filtered_arr=t.arr.filter(lambda x: x % 2 == 0)),
        pandas_expr_func=lambda df: pd.DataFrame({'filtered_arr': df['arr'].apply(lambda x: [item for item in x if item % 2 == 0])}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_index():
    run_test_case(
        op_name='ArrayIndex',
        data=pd.DataFrame({'arr': [[10, 20, 30], [40, 50, 60]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(first_element=t.arr[0]),
        pandas_expr_func=lambda df: pd.DataFrame({'first_element': df['arr'].apply(lambda x: x[0])}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_intersect():
    run_test_case(
        op_name='ArrayIntersect',
        data=pd.DataFrame({'arr1': [[1, 2, 3], [4, 5]], 'arr2': [[2, 3, 4], [3, 5, 6]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(intersect=t.arr1.intersect(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'intersect': df.apply(lambda row: sorted(list(set(row['arr1']) & set(row['arr2']))), axis=1)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_map():
    run_test_case(
        op_name='ArrayMap',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5, 6]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(mapped=t.arr.map(lambda x: x * 2)),
        pandas_expr_func=lambda df: pd.DataFrame({'mapped': df['arr'].apply(lambda x: [item * 2 for item in x])}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_max():
    run_test_case(
        op_name='ArrayMax',
        data=pd.DataFrame({'arr': [[1, 5, 2], [8, 3, 9]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(array_max=t.arr.max()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_max': df['arr'].apply(max)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_mean():
    run_test_case(
        op_name='ArrayMean',
        data=pd.DataFrame({'arr': [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(array_mean=t.arr.mean()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_mean': df['arr'].apply(np.mean)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_min():
    run_test_case(
        op_name='ArrayMin',
        data=pd.DataFrame({'arr': [[1, 5, 2], [8, 3, 9]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(array_min=t.arr.min()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_min': df['arr'].apply(min)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_mode():
    run_test_case(
        op_name='ArrayMode',
        data=pd.DataFrame({'arr': [[1, 2, 2, 3], [4, 5, 4, 4]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(array_mode=t.arr.mode()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_mode': df['arr'].apply(lambda x: pd.Series(x).mode().tolist())}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_position():
    run_test_case(
        op_name='ArrayPosition',
        data=pd.DataFrame({'arr': [[10, 20, 30], [40, 50, 60]], 'val': [20, 60]}, dtype=object),
        ibis_expr_func=lambda t: t.select(position=t.arr.find(t.val)),
        pandas_expr_func=lambda df: pd.DataFrame({'position': df.apply(lambda row: row['arr'].index(row['val']) if row['val'] in row['arr'] else -1, axis=1)}))
@pytest.mark.skip(reason="Function call not supported: _ibis_repeat(text, int)")
def test_op_array_repeat():
    run_test_case(
        op_name='ArrayRepeat',
        data=pd.DataFrame({'value': ['A', 'B'], 'times': [2, 3]}),
        ibis_expr_func=lambda t: t.select(repeated=t.value.repeat(t.times)),
        pandas_expr_func=lambda df: pd.DataFrame({'repeated': df.apply(lambda row: [row['value']] * row['times'], axis=1)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_slice():
    run_test_case(
        op_name='ArraySlice',
        data=pd.DataFrame({'arr': [[1, 2, 3, 4, 5], [6, 7, 8]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(sliced=t.arr[1:3]),
        pandas_expr_func=lambda df: pd.DataFrame({'sliced': df['arr'].apply(lambda x: x[1:3])}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_sort():
    run_test_case(
        op_name='ArraySort',
        data=pd.DataFrame({'arr': [[3, 1, 2], [6, 4, 5]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(sorted_arr=t.arr.sort()),
        pandas_expr_func=lambda df: pd.DataFrame({'sorted_arr': df['arr'].apply(sorted)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_string_join():
    run_test_case(
        op_name='ArrayStringJoin',
        data=pd.DataFrame({'arr': [['a', 'b', 'c'], ['x', 'y']]}, dtype=object),
        ibis_expr_func=lambda t: t.select(joined=t.arr.join(', ')),
        pandas_expr_func=lambda df: pd.DataFrame({'joined': df['arr'].apply(lambda x: ', '.join(x))}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_sum():
    run_test_case(
        op_name='ArraySum',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5, 6]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(array_sum=t.arr.sum()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_sum': df['arr'].apply(sum)}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_array_union():
    run_test_case(
        op_name='ArrayUnion',
        data=pd.DataFrame({'arr1': [[1, 2], [3, 4]], 'arr2': [[2, 3], [4, 5]]}, dtype=object),
        ibis_expr_func=lambda t: t.select(union=t.arr1.union(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'union': df.apply(lambda row: sorted(list(set(row['arr1']) | set(row['arr2']))), axis=1)}))
def test_op_cast():
    run_test_case(
        op_name='Cast',
        data=pd.DataFrame({'value': [1, 2, 3], 'float_val': [1.1, 2.2, 3.3]}),
        ibis_expr_func=lambda t: t.select(str_val=t.value.cast('string'), int_val=t.float_val.cast('int32')),
        pandas_expr_func=lambda df: pd.DataFrame({'str_val': df['value'].astype(str), 'int_val': df['float_val'].astype(np.int32)}))
@pytest.mark.skip(reason="Correlation operation is not defined in SQLite..")
def test_op_correlation():
    run_test_case(
        op_name='Correlation',
        data=pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [2, 4, 5, 4, 5]}),
        ibis_expr_func=lambda t: t.aggregate(corr=t.x.corr(t.y)),
        pandas_expr_func=lambda df: pd.DataFrame({'corr': [df['x'].corr(df['y'])]}))
#FIXME
@pytest.mark.skip(reason="TypeError: Table.count() takes 1 positional argument but 2 were given.")
def test_op_count_distinct_star():
    run_test_case(
        op_name='CountDistinctStar',
        data=pd.DataFrame({'col1': [1, 1, 2, 2, 3], 'col2': ['a', 'b', 'a', 'b', 'c']}),
        ibis_expr_func=lambda t: t.aggregate(distinct_count=t.count(t.distinct())),
        pandas_expr_func=lambda df: pd.DataFrame({'distinct_count': [len(df.drop_duplicates())]}, dtype=np.int64))
#FIXME
@pytest.mark.skip(reason="AttributeError: module 'ibis' has no attribute 'date_from_ymd'.")
def test_op_date_from_ymd():
    run_test_case(
        op_name='DateFromYMD',
        data=pd.DataFrame({'year': [2023, 2024], 'month': [1, 7], 'day': [15, 20]}),
        ibis_expr_func=lambda t: t.select(date_col=ibis.date_from_ymd(t.year, t.month, t.day)),
        pandas_expr_func=lambda df: pd.DataFrame({'date_col': pd.to_datetime(df[['year', 'month', 'day']])}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_day_of_week_index():
    run_test_case(
        op_name='DayOfWeekIndex',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])}), # Sunday, Monday, Tuesday
        ibis_expr_func=lambda t: t.select(day_of_week_index=t.ts.day_of_week.index()),
        pandas_expr_func=lambda df: pd.DataFrame({'day_of_week_index': df['ts'].dt.dayofweek})) # Monday=0, Sunday=6
#FIXME
@pytest.mark.skip(reason="AttributeError: 'DayOfWeek' object has no attribute 'short_name'.")
def test_op_day_of_week_name():
    run_test_case(
        op_name='DayOfWeekName',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])}),
        ibis_expr_func=lambda t: t.select(day_of_week_name=t.ts.day_of_week.short_name()), # or .full_name()
        pandas_expr_func=lambda df: pd.DataFrame({'day_of_week_name': df['ts'].dt.day_name().str[:3]})) # e.g., 'Sun', 'Mon'
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_extract_epoch_seconds():
    run_test_case(
        op_name='ExtractEpochSeconds',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 00:00:01'])}),
        ibis_expr_func=lambda t: t.select(epoch_seconds=t.ts.epoch_seconds()),
        pandas_expr_func=lambda df: pd.DataFrame({'epoch_seconds': (df['ts'].astype(np.int64) // 10**9).astype(np.int64)}))
@pytest.mark.skip(reason="ExtractIsoYear operation is not defined in SQLite.")
def test_op_extract_iso_year():
    run_test_case(
        op_name='ExtractIsoYear',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-12-31', '2024-01-01'])}), # 2023-12-31 is in ISO week 52 of 2023, 2024-01-01 is in ISO week 1 of 2024
        ibis_expr_func=lambda t: t.select(iso_year=t.ts.iso_year()),
        pandas_expr_func=lambda df: pd.DataFrame({'iso_year': df['ts'].dt.isocalendar().year.astype(np.int32)}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_extract_microsecond():
    run_test_case(
        op_name='ExtractMicrosecond',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:30:00.123456'])}),
        ibis_expr_func=lambda t: t.select(microsecond=t.ts.microsecond()),
        pandas_expr_func=lambda df: pd.DataFrame({'microsecond': df['ts'].dt.microsecond}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_extract_millisecond():
    run_test_case(
        op_name='ExtractMillisecond',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:30:00.123'])}),
        ibis_expr_func=lambda t: t.select(millisecond=t.ts.millisecond()),
        pandas_expr_func=lambda df: pd.DataFrame({'millisecond': (df['ts'].dt.microsecond // 1000).astype(np.int32)}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_extract_second():
    run_test_case(
        op_name='ExtractSecond',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:30:45'])}),
        ibis_expr_func=lambda t: t.select(second=t.ts.second()),
        pandas_expr_func=lambda df: pd.DataFrame({'second': df['ts'].dt.second}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: strftime(unknown type, timestamp)")
def test_op_extract_week_of_year():
    run_test_case(
        op_name='ExtractWeekOfYear',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01', '2023-01-08'])}), # 2023-01-01 is Week 1, 2023-01-08 is Week 2
        ibis_expr_func=lambda t: t.select(week=t.ts.week_of_year()),
        pandas_expr_func=lambda df: pd.DataFrame({'week': df['ts'].dt.isocalendar().week.astype(np.int32)}))
#FIXME
@pytest.mark.skip(reason="ibis.common.annotations.SignatureValidationError.")
def test_op_find_in_set():
    run_test_case(
        op_name='FindInSet',
        data=pd.DataFrame({'haystack': ['a,b,c', 'x,y'], 'needle': ['b', 'z']}),
        ibis_expr_func=lambda t: t.select(found=ibis.literal(',').join([t.haystack]).find_in_set(t.needle)), # This Ibis expression might vary
        pandas_expr_func=lambda df: pd.DataFrame({'found': df.apply(lambda row: (row['needle'] in row['haystack'].split(',')) if pd.notna(row['haystack']) else False, axis=1)}))
@pytest.mark.skip(reason="Function call not supported: _ibis_first(text)")
def test_op_first():
    run_test_case(
        op_name='First',
        data=pd.DataFrame({'id': [1, 2, 3], 'value': ['a', 'b', 'c']}),
        ibis_expr_func=lambda t: t.aggregate(first_val=t.value.first()),
        pandas_expr_func=lambda df: pd.DataFrame({'first_val': [df['value'].iloc[0]]}))
#FIXME
@pytest.mark.skip(reason="Hash operation is not defined in SQLite.")
def test_op_hash():
    run_test_case(
        op_name='Hash',
        data=pd.DataFrame({'value': ['string1', 'string2', 'string1']}),
        ibis_expr_func=lambda t: t.select(hashed_val=t.value.hash()),
        pandas_expr_func=lambda df: pd.DataFrame({'hashed_val': df['value'].apply(lambda x: hash(x))})) # Python's hash is not stable across runs/implementations
#FIXME
@pytest.mark.skip(reason="ibis.common.exceptions.IbisError: backend (DuckDB) is not installed.")
def test_op_integer_range():
    # This test case is difficult with run_test_case as it generates a table, not queries an existing one.
    # It would typically be a direct `con.range(start, stop)` or `con.values(value=ibis.range(start, stop))`
    # For a test, we can simulate its output.
    # data is not directly used for table creation, but to define the expected range for pandas.
    start_val, end_val = 1, 5
    run_test_case(
        op_name='IntegerRange',
        data=pd.DataFrame({'value': range(start_val, end_val + 1)}), # Just for schema and expected df
        ibis_expr_func=lambda t: ibis.range(start_val, end_val + 1).name('value_range'), # This will likely fail directly against a table
        pandas_expr_func=lambda df: pd.DataFrame({'value': range(start_val, end_val + 1)}))
@pytest.mark.skip(reason="IsInf operation is not defined in SQLite.")
def test_op_is_inf():
    run_test_case(
        op_name='IsInf',
        data=pd.DataFrame({'value': [1.0, float('inf'), -float('inf'), np.nan]}),
        ibis_expr_func=lambda t: t.select(is_inf=t.value.isinf()),
        pandas_expr_func=lambda df: pd.DataFrame({'is_inf': np.isinf(df['value'])}))
@pytest.mark.skip(reason="IsNan operation is not defined in SQLite.")
def test_op_is_nan():
    run_test_case(
        op_name='IsNan',
        data=pd.DataFrame({'value': [1.0, float('inf'), -float('inf'), np.nan]}),
        ibis_expr_func=lambda t: t.select(is_nan=t.value.isnan()),
        pandas_expr_func=lambda df: pd.DataFrame({'is_nan': np.isnan(df['value'])}))
#FIXME
def test_op_join_link():
    # This is not a direct operation that you test with data and an expression
    # it's part of how Ibis handles complex joins. It would be tested implicitly
    # by successful join operations.
    pass
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'json_get_item'")
def test_op_json_get_item():
    data = pd.DataFrame({'json_data': ['{"a": 1, "b": "hello"}', '{"c": 3}', None]}, dtype=object)
    run_test_case(
        op_name='JSONGetItem',
        data=data,
        ibis_expr_func=lambda t: t.select(item_a=t.json_data.json_get_item("a"), item_b=t.json_data.json_get_item("b")),
        pandas_expr_func=lambda df: pd.DataFrame({
            'item_a': df['json_data'].apply(lambda x: int(eval(x)['a']) if pd.notna(x) and 'a' in eval(x) else np.nan), # eval is dangerous, use json.loads in real code
            'item_b': df['json_data'].apply(lambda x: eval(x)['b'] if pd.notna(x) and 'b' in eval(x) else np.nan)}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: _ibis_last(text)")
def test_op_last():
    run_test_case(
        op_name='Last',
        data=pd.DataFrame({'id': [1, 2, 3], 'value': ['a', 'b', 'c']}),
        ibis_expr_func=lambda t: t.aggregate(last_val=t.value.last()),
        pandas_expr_func=lambda df: pd.DataFrame({'last_val': [df['value'].iloc[-1]]}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: log(numeric, real).")
def test_op_log():
    run_test_case(
        op_name='Log',
        data=pd.DataFrame({'value': [100.0, 8.0, 27.0]}),
        ibis_expr_func=lambda t: t.select(log_base_e=t.value.log()), # natural log by default
        pandas_expr_func=lambda df: pd.DataFrame({'log_base_e': np.log(df['value'])}))
#FIXME
@pytest.mark.skip(reason="Function call not supported: log2(real).")
def test_op_log2():
    run_test_case(
        op_name='Log2',
        data=pd.DataFrame({'value': [1.0, 2.0, 4.0, 8.0]}),
        ibis_expr_func=lambda t: t.select(log2_val=t.value.log2()),
        pandas_expr_func=lambda df: pd.DataFrame({'log2_val': np.log2(df['value'])}))
#FIXME
@pytest.mark.skip(reason="TypeError: Cannot construct a parametric Array datatype based on the type itself")
def test_op_map():
    # This is for creating map literals or columns of map type. SqreamDB might not have direct map types.
    run_test_case(
        op_name='MapLiteral',
        data=pd.DataFrame({'key_col': ['a', 'b'], 'value_col': [1, 2]}),
        ibis_expr_func=lambda t: t.select(my_map=ibis.map([t.key_col], [t.value_col])), # This is a conceptual representation
        pandas_expr_func=lambda df: pd.DataFrame({'my_map': df.apply(lambda row: {row['key_col']: row['value_col']}, axis=1)}))
#FIXME
@pytest.mark.skip(reason="ProgrammingError: Trying to insert unsuitable types to column number 1 of type ftBlob")
def test_op_map_get():
    # Similar to JSONGetItem but for Ibis map types.
    data = pd.DataFrame({'map_col': [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}]})
    run_test_case(
        op_name='MapGet',
        data=data,
        ibis_expr_func=lambda t: t.select(val_a=t.map_col['a']),
        pandas_expr_func=lambda df: pd.DataFrame({'val_a': df['map_col'].apply(lambda x: x.get('a'))}))
#FIXME
@pytest.mark.skip(reason="ProgrammingError: Trying to insert unsuitable types to column number 1 of type ftBlob")
def test_op_map_keys():
    data = pd.DataFrame({'map_col': [{'a': 1, 'b': 2}, {'c': 3}]})
    run_test_case(
        op_name='MapKeys',
        data=data,
        ibis_expr_func=lambda t: t.select(keys=t.map_col.keys()),
        pandas_expr_func=lambda df: pd.DataFrame({'keys': df['map_col'].apply(lambda x: sorted(list(x.keys())))}))
#FIXME
@pytest.mark.skip(reason="ProgrammingError: Trying to insert unsuitable types to column number 1 of type ftBlob")
def test_op_map_length():
    data = pd.DataFrame({'map_col': [{'a': 1, 'b': 2}, {'c': 3}]})
    run_test_case(
        op_name='MapLength',
        data=data,
        ibis_expr_func=lambda t: t.select(length=t.map_col.length()),
        pandas_expr_func=lambda df: pd.DataFrame({'length': df['map_col'].apply(len)}))
#FIXME
@pytest.mark.skip(reason="ProgrammingError: Trying to insert unsuitable types to column number 1 of type ftBlob")
def test_op_map_merge():
    data = pd.DataFrame({'map1': [{'a': 1, 'b': 2}, {'x': 10}], 'map2': [{'b': 3, 'c': 4}, {'y': 20}]})
    run_test_case(
        op_name='MapMerge',
        data=data,
        ibis_expr_func=lambda t: t.select(merged=t.map1.merge(t.map2)),
        pandas_expr_func=lambda df: pd.DataFrame({'merged': df.apply(lambda row: {**row['map1'], **row['map2']}, axis=1)}))
#FIXME
@pytest.mark.skip(reason="ProgrammingError: Trying to insert unsuitable types to column number 1 of type ftBlob")
def test_op_map_values():
    data = pd.DataFrame({'map_col': [{'a': 1, 'b': 2}, {'c': 3}]})
    run_test_case(
        op_name='MapValues',
        data=data,
        ibis_expr_func=lambda t: t.select(values=t.map_col.values()),
        pandas_expr_func=lambda df: pd.DataFrame({'values': df['map_col'].apply(lambda x: sorted(list(x.values())))}))
@pytest.mark.skip(reason="Median operation is not defined in SQLite.")
def test_op_median():
    run_test_case(
        op_name='Median',
        data=pd.DataFrame({'value': [1, 5, 2, 8, 3, 9, 4, 7]}),
        ibis_expr_func=lambda t: t.aggregate(med=t.value.median()),
        pandas_expr_func=lambda df: pd.DataFrame({'med': [df['value'].median()]}))
@pytest.mark.skip(reason="Function call not supported: _ibis_mode(int)")
def test_op_mode():
    run_test_case(
        op_name='Mode',
        data=pd.DataFrame({'value': [1, 2, 2, 3, 3, 3, 4]}),
        ibis_expr_func=lambda t: t.aggregate(mode_val=t.value.mode()),
        pandas_expr_func=lambda df: pd.DataFrame({'mode_val': [df['value'].mode().iloc[0]]})) # pandas mode returns Series, take first
def test_op_modulus():
    run_test_case(
        op_name='Modulus',
        data=pd.DataFrame({'a': [10, 7, 5], 'b': [3, 2, 5]}),
        ibis_expr_func=lambda t: t.select(mod_result=t.a % t.b),
        pandas_expr_func=lambda df: pd.DataFrame({'mod_result': df['a'] % df['b']}))
#FIXME
@pytest.mark.skip(reason="UnsupportedBackendType: Unsupported type: Array(value_type=Float64(nullable=True), length=None, nullable=True)")
def test_op_multi_quantile():
    run_test_case(
        op_name='MultiQuantile',
        data=pd.DataFrame({'value': list(range(1, 101))}),
        ibis_expr_func=lambda t: t.aggregate(quantiles=t.value.quantile([0.25, 0.5, 0.75])),
        pandas_expr_func=lambda df: pd.DataFrame({'quantiles': [list(df['value'].quantile([0.25, 0.5, 0.75]))]}))
@pytest.mark.skip(reason="Quantile operation is not defined in SQLite.")
def test_op_quantile():
    run_test_case(
        op_name='Quantile',
        data=pd.DataFrame({'value': list(range(1, 101))}),
        ibis_expr_func=lambda t: t.aggregate(q50=t.value.quantile(0.5)),
        pandas_expr_func=lambda df: pd.DataFrame({'q50': [df['value'].quantile(0.5)]}))
#FIXME
@pytest.mark.skip(reason="TypeError: range() missing 1 required positional argument: 'step'")
def test_op_range():
    # Similar to IntegerRange, this generates a table.
    start_val, end_val = 0.0, 5.0
    run_test_case(
        op_name='RangeFloat',
        data=pd.DataFrame({'value': np.arange(start_val, end_val + 1.0)}), # Just for schema and expected df
        ibis_expr_func=lambda t: ibis.range(start_val, end_val + 1.0).name('value_range'),
        pandas_expr_func=lambda df: pd.DataFrame({'value': np.arange(start_val, end_val + 1.0)}))
#FIXME
@pytest.mark.skip(reason="TypeError: StringValue.re_extract() missing 1 required positional argument: 'index'")
def test_op_regex_extract():
    run_test_case(
        op_name='RegexExtract',
        data=pd.DataFrame({'s': ['hello world', 'foo bar baz']}),
        ibis_expr_func=lambda t: t.select(extracted=t.s.re_extract(r'(\w+)\s+(\w+)')),
        pandas_expr_func=lambda df: pd.DataFrame({'extracted': df['s'].str.extract(r'(\w+)\s+(\w+)').apply(lambda row: row.tolist() if pd.notna(row[0]) else None, axis=1)})) # Returns a tuple, Ibis might return a string or list
@pytest.mark.skip(reason="StringToTimestamp operation is not defined in SQLite.")
def test_op_string_to_time():
    run_test_case(
        op_name='StringToTime',
        data=pd.DataFrame({'date_str': ['2023-01-01 10:00:00', '2024-02-29 14:30:00']}),
        ibis_expr_func=lambda t: t.select(ts_val=t.date_str.to_timestamp('%Y-%m-%d %H:%M:%S')),
        pandas_expr_func=lambda df: pd.DataFrame({'ts_val': pd.to_datetime(df['date_str'], format='%Y-%m-%d %H:%M:%S')}))
#FIXME
@pytest.mark.skip(reason="TypeError: struct() got an unexpected keyword argument 'a'")
def test_op_struct_column():
    run_test_case(
        op_name='StructColumn',
        data=pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']}),
        ibis_expr_func=lambda t: t.select(my_struct=ibis.struct(a=t.a, b=t.b)),
        pandas_expr_func=lambda df: pd.DataFrame({'my_struct': df.apply(lambda row: {'a': row['a'], 'b': row['b']}, axis=1)}))
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'a'")
def test_op_struct_field():
    data = pd.DataFrame({'my_struct': [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]})
    run_test_case(
        op_name='StructField',
        data=data,
        ibis_expr_func=lambda t: t.select(field_a=t.my_struct.a),
        pandas_expr_func=lambda df: pd.DataFrame({'field_a': df['my_struct'].apply(lambda x: x['a'])}))
@pytest.mark.skip(reason="Array types aren't supported in SQLite.")
def test_op_table_unnest():
    run_test_case(
        op_name='TableUnnest',
        data=pd.DataFrame({'id': [1, 2], 'tags': [['red', 'green'], ['blue']]}, dtype=object),
        ibis_expr_func=lambda t: t.unnest('tags'),
        pandas_expr_func=lambda df: df.explode('tags'))
@pytest.mark.skip(reason="TypeError: TimestampValue.bucket() got some positional-only arguments passed as keyword arguments: 'interval'")
def test_op_timestamp_bucket():
    run_test_case(
        op_name='TimestampBucket',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:05:00', '2023-01-01 10:15:00', '2023-01-01 10:25:00'])}),
        ibis_expr_func=lambda t: t.select(bucket=t.ts.bucket(interval='10 minutes')),
        pandas_expr_func=lambda df: pd.DataFrame({'bucket': df['ts'].dt.floor('10min')}))
@pytest.mark.skip(reason="AttributeError: module 'ibis' has no attribute 'timestamp_from_ymdhms'.")
def test_op_timestamp_from_ymdhms():
    run_test_case(
        op_name='TimestampFromYMDHMS',
        data=pd.DataFrame({'y': [2023], 'mo': [1], 'd': [1], 'h': [10], 'mi': [30], 's': [0]}),
        ibis_expr_func=lambda t: t.select(ts_col=ibis.timestamp_from_ymdhms(t.y, t.mo, t.d, t.h, t.mi, t.s)),
        pandas_expr_func=lambda df: pd.DataFrame({'ts_col': pd.to_datetime(df[['y', 'mo', 'd', 'h', 'mi', 's']])}))
@pytest.mark.skip(reason="AttributeError: module 'ibis' has no attribute 'to_json_array'.")
def test_op_to_json_array():
    run_test_case(
        op_name='ToJSONArray',
        data=pd.DataFrame({'id': [1, 2], 'value': [10, 20], 'name': ['A', 'B']}),
        ibis_expr_func=lambda t: t.select(json_array=ibis.to_json_array([t.id, t.value, t.name])),
        pandas_expr_func=lambda df: pd.DataFrame({'json_array': df.apply(lambda row: [row['id'], row['value'], row['name']], axis=1).apply(lambda x: json.dumps(x))})) # needs import json
@pytest.mark.skip(reason="TryCast operation is not defined in SQLite.")
def test_op_try_cast():
    run_test_case(
        op_name='TryCast',
        data=pd.DataFrame({'s': ['123', 'abc', '456']}),
        ibis_expr_func=lambda t: t.select(num_val=t.s.try_cast('int64')),
        pandas_expr_func=lambda df: pd.DataFrame({'num_val': pd.to_numeric(df['s'], errors='coerce').astype(pd.Int64Dtype())})) # Use nullable integer dtype for NaNs
#FIXME
def test_op_type_of():
    # This is not a direct operation for query. It's for inspecting Ibis expressions.
    pass
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'json_extract_scalar_as_boolean'")
def test_op_unwrap_json_boolean():
    run_test_case(
        op_name='UnwrapJSONBoolean',
        data=pd.DataFrame({'json_bool': ['true', 'false', 'null', '{"key": true}']}),
        ibis_expr_func=lambda t: t.select(bool_val=t.json_bool.json_extract_scalar_as_boolean('$.key')), # Assuming a path
        pandas_expr_func=lambda df: pd.DataFrame({'bool_val': df['json_bool'].apply(lambda x: True if 'true' in x else (False if 'false' in x else None))})) # Simplistic
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'json_extract_scalar_as_float'")
def test_op_unwrap_json_float64():
    run_test_case(
        op_name='UnwrapJSONFloat64',
        data=pd.DataFrame({'json_float': ['1.23', '4.5e-1', 'null', '{"val": 7.89}']}),
        ibis_expr_func=lambda t: t.select(float_val=t.json_float.json_extract_scalar_as_float('$.val')),
        pandas_expr_func=lambda df: pd.DataFrame({'float_val': df['json_float'].apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else np.nan)})) # Simplistic
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'json_extract_scalar_as_int'")
def test_op_unwrap_json_int64():
    run_test_case(
        op_name='UnwrapJSONInt64',
        data=pd.DataFrame({'json_int': ['123', 'null', '{"count": 456}']}),
        ibis_expr_func=lambda t: t.select(int_val=t.json_int.json_extract_scalar_as_int('$.count')),
        pandas_expr_func=lambda df: pd.DataFrame({'int_val': df['json_int'].apply(lambda x: int(x) if x.isdigit() else np.nan)})) # Simplistic
#FIXME
@pytest.mark.skip(reason="AttributeError: 'StringColumn' object has no attribute 'json_extract_scalar_as_string'")
def test_op_unwrap_json_string():
    run_test_case(
        op_name='UnwrapJSONString',
        data=pd.DataFrame({'json_str': ['"hello"', '"world"', 'null', '{"name": "Alice"}']}),
        ibis_expr_func=lambda t: t.select(str_val=t.json_str.json_extract_scalar_as_string('$.name')),
        pandas_expr_func=lambda df: pd.DataFrame({'str_val': df['json_str'].apply(lambda x: x.strip('"') if x.startswith('"') else None)})) # Simplistic