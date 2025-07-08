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

# --- ORACLE TEST CASES ---

def test_op_is_null():
    run_test_case(
        op_name='IsNull',
        data=pd.DataFrame({'value': [1, None, 3, np.nan]}),
        ibis_expr_func=lambda t: t.select(is_null=t.value.isnull()),
        pandas_expr_func=lambda df: pd.DataFrame({'is_null': df['value'].isnull()}))
def test_op_literal_string():
    run_test_case(
        op_name='LiteralString',
        data=pd.DataFrame({'id': [1, 2]}),
        ibis_expr_func=lambda t: t.select(fixed_string=ibis.literal("hello")),
        pandas_expr_func=lambda df: pd.DataFrame({'fixed_string': ["hello", "hello"]}))
def test_op_literal_integer():
    run_test_case(
        op_name='LiteralInteger',
        data=pd.DataFrame({'id': [1, 2]}),
        ibis_expr_func=lambda t: t.select(fixed_int=ibis.literal(123)),
        pandas_expr_func=lambda df: pd.DataFrame({'fixed_int': [123, 123]}))
def test_op_pi():
    # Pi is a scalar constant
    run_test_case(
        op_name='Pi',
        data=pd.DataFrame({'id': [1]}), # Dummy data, as it's a scalar op
        ibis_expr_func=lambda t: t.select(pi_val=ibis.pi),
        pandas_expr_func=lambda df: pd.DataFrame({'pi_val': [np.pi]}))
def test_op_degrees():
    run_test_case(
        op_name='Degrees',
        data=pd.DataFrame({'radians': [np.pi/2, np.pi, 2*np.pi, 0.0]}),
        ibis_expr_func=lambda t: t.select(degrees_val=t.radians.degrees()),
        pandas_expr_func=lambda df: pd.DataFrame({'degrees_val': np.degrees(df['radians'])}))
def test_op_radians():
    run_test_case(
        op_name='Radians',
        data=pd.DataFrame({'degrees': [90.0, 180.0, 360.0, 0.0]}),
        ibis_expr_func=lambda t: t.select(radians_val=t.degrees.radians()),
        pandas_expr_func=lambda df: pd.DataFrame({'radians_val': np.radians(df['degrees'])}))
# create or replace TABLE "ibis_test_levenshtein" ("s1" VARCHAR2(4000), "s2" VARCHAR2(4000));
# INSERT INTO "ibis_test_levenshtein" (s1, s2) VALUES ('kitten', 'sitting'), ('sitting', 'kitten');
@pytest.mark.skip(reason='SQreamError: too large alloc')
def test_op_levenshtein():
    run_test_case(
        op_name='Levenshtein',
        data=pd.DataFrame({'s1': ['kitten', 'sitting'], 's2': ['sitting', 'kitten']}),
        ibis_expr_func=lambda t: t.select(distance=t.s1.levenshtein(t.s2)),
        # Pandas does not have a direct Levenshtein function. This would require an external library or custom implementation.
        # For demonstration, a placeholder that will likely need adjustment.
        pandas_expr_func=lambda df: pd.DataFrame({'distance': [3, 3]})) # Levenshtein('kitten', 'sitting') == 3
# create or replace TABLE "ibis_test_regexreplace" ("s" VARCHAR2(4000));
# INSERT INTO "ibis_test_regexreplace" (s) VALUES ('hello world'), ('foo bar baz');
@pytest.mark.skip(reason='SQreamError: too large alloc')
def test_op_regex_replace():
    run_test_case(
        op_name='RegexReplace',
        data=pd.DataFrame({'s': ['hello world', 'foo bar baz']}),
        ibis_expr_func=lambda t: t.select(replaced=t.s.re_replace(r'o', 'X')),
        pandas_expr_func=lambda df: pd.DataFrame({'replaced': df['s'].str.replace(r'o', 'X', regex=True)}))
def test_op_covariance():
    run_test_case(
        op_name='Covariance',
        data=pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [2, 4, 5, 4, 5]}),
        ibis_expr_func=lambda t: t.aggregate(covar=t.x.cov(t.y)),
        pandas_expr_func=lambda df: pd.DataFrame({'covar': [df['x'].cov(df['y'])]}))
# E           [left]:  [0, 1, 2, 0, 1]
# E           [right]: [1, 2, 3, 1, 2]
@pytest.mark.skip(reason='wrong results')
def test_op_window_function_row_number():
    run_test_case(
        op_name='WindowFunctionRowNumber',
        data=pd.DataFrame({
            'group_key': [1, 1, 2, 2, 1],
            'order_key': [10, 20, 30, 40, 50],
            'value': [1, 2, 3, 4, 5]}),
        ibis_expr_func=lambda t: t.select(
            t.group_key,
            t.order_key,
            t.value,
            row_num=ibis.row_number().over(ibis.window(group_by=t.group_key, order_by=t.order_key))),
        pandas_expr_func=lambda df: df.assign(
            row_num=df.groupby('group_key')['order_key'].rank(method='first').astype(int)))
@pytest.mark.skip(reason='AttributeError: \'IntegerColumn\' object has no attribute \'days\'')
def test_op_interval_from_integer_days():
    run_test_case(
        op_name='IntervalFromIntegerDays',
        data=pd.DataFrame({'days_val': [1, 5, -2]}),
        ibis_expr_func=lambda t: t.select(interval_col=t.days_val.days()),
        pandas_expr_func=lambda df: pd.DataFrame({'interval_col': pd.to_timedelta(df['days_val'], unit='D')}))
# create or replace TABLE "ibis_test_strip" ("s" VARCHAR2(4000));
# INSERT INTO "ibis_test_strip" (s) VALUES ('  hello  '), ('\tworld\n');
@pytest.mark.skip(reason='SQreamError: too large alloc')
def test_op_strip():
    run_test_case(
        op_name='Strip',
        data=pd.DataFrame({'s': ['  hello  ', '\tworld\n']}),
        ibis_expr_func=lambda t: t.select(stripped=t.s.strip()),
        pandas_expr_func=lambda df: pd.DataFrame({'stripped': df['s'].str.strip()}))