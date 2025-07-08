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

# --- MSSQL TEST CASES ---

# SELECT SUBSTRING("t0"."s" FROM CASE WHEN (1 + 1) >= 1 THEN 1 + 1 ELSE 1 + 1 + LENGTH("t0"."s") END FOR 4) AS "sub" FROM "ibis_test_substring" AS "t0";
@pytest.mark.skip(reason='SQreamError: Internal compiler error:\nError at RelationalAlgebra phase during Convert\nInvalid function in stringToScalarFun: \'!substring\'')
def test_op_substring():
    run_test_case(
        op_name='Substring',
        data=pd.DataFrame({'s': ['hello world', 'ibis', 'python']}),
        ibis_expr_func=lambda t: t.select(sub=t.s.substr(1, 4)), # Ibis is 0-indexed for substr start by default
        pandas_expr_func=lambda df: pd.DataFrame({'sub': df['s'].str[1:5]})) # Pandas slicing is exclusive end, so +1
# SELECT "t0"."group_col", GROUP_CONCAT("t0"."value", ', ') AS "concatenated" FROM "ibis_test_groupconcat" AS "t0" GROUP BY 1;
@pytest.mark.skip(reason='SQreamError: column \"t0.value\" must appear in the GROUP BY clause or be used in an aggregate function')
def test_op_group_concat():
    run_test_case(
        op_name='GroupConcat',
        data=pd.DataFrame({'group_col': ['A', 'A', 'B', 'B'], 'value': ['foo', 'bar', 'baz', 'qux']}),
        ibis_expr_func=lambda t: t.group_by('group_col').aggregate(concatenated=t.value.group_concat(', ')),
        pandas_expr_func=lambda df: df.groupby('group_col', as_index=False)['value'].apply(lambda x: ', '.join(x)).reset_index())
def test_op_count_star():
    run_test_case(
        op_name='CountStar',
        data=pd.DataFrame({'a': [1, 2, None, 4], 'b': ['x', 'y', 'z', None]}),
        ibis_expr_func=lambda t: t.aggregate(total_rows=t.count()),
        pandas_expr_func=lambda df: pd.DataFrame({'total_rows': [len(df)]}, dtype=np.int64))
@pytest.mark.skip(reason='timestamp')
def test_op_date_timestamp_truncate():
    run_test_case(
        op_name='DateTimestampTruncate',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-05-15 14:35:10', '2024-01-01 00:00:00'])}),
        ibis_expr_func=lambda t: t.select(truncated_month=t.ts.truncate('month')),
        pandas_expr_func=lambda df: pd.DataFrame({'truncated_month': df['ts'].dt.to_period('M').dt.start_time}))
@pytest.mark.skip(reason='timestamp')
def test_op_date():
    run_test_case(
        op_name='Date',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-05-15 14:35:10', '2024-01-01 00:00:00'])}),
        ibis_expr_func=lambda t: t.select(date_only=t.ts.date()),
        pandas_expr_func=lambda df: pd.DataFrame({'date_only': df['ts'].dt.date.astype('datetime64[ns]')})) # Convert to datetime64[ns] for consistent dtype comparison
@pytest.mark.skip(reason='timestamp')
def test_op_datetime_delta_seconds():
    run_test_case(
        op_name='DateTimeDeltaSeconds',
        data=pd.DataFrame({
            'ts1': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-01 11:00:00']),
            'ts2': pd.to_datetime(['2023-01-01 10:00:10', '2023-01-01 10:59:00'])
        }),
        ibis_expr_func=lambda t: t.select(diff_seconds=(t.ts1 - t.ts2).total_seconds()),
        pandas_expr_func=lambda df: pd.DataFrame({'diff_seconds': (df['ts1'] - df['ts2']).dt.total_seconds()}))
@pytest.mark.skip(reason='timestamp')
def test_op_extract_temporal_component_hour():
    # This is effectively the same as ExtractHour, but illustrates the generic method
    run_test_case(
        op_name='ExtractTemporalComponentHour',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:30:00', '2023-01-01 23:59:59'])}),
        ibis_expr_func=lambda t: t.select(hour=t.ts.hour()), # Ibis uses direct methods for common components
        pandas_expr_func=lambda df: pd.DataFrame({'hour': df['ts'].dt.hour}))
@pytest.mark.skip(reason='TimestampFromUNIX operation is not defined')
def test_op_timestamp_from_unix():
    run_test_case(
        op_name='TimestampFromUNIX',
        data=pd.DataFrame({'unix_seconds': [1672531200, 1672531200 + 3600]}), # 2023-01-01 00:00:00 UTC, + 1 hour
        ibis_expr_func=lambda t: t.select(ts=t.unix_seconds.to_timestamp()),
        pandas_expr_func=lambda df: pd.DataFrame({'ts': pd.to_datetime(df['unix_seconds'], unit='s')}))
def test_op_mean():
    run_test_case(
        op_name='MeanAggregation', # Changed name slightly for clarity against array_mean
        data=pd.DataFrame({'value': [10.0, 20.0, 30.0, None, 40.0]}),
        ibis_expr_func=lambda t: t.aggregate(average_val=t.value.mean()),
        pandas_expr_func=lambda df: pd.DataFrame({'average_val': [df['value'].mean()]}))
def test_op_not():
    run_test_case(
        op_name='Not',
        data=pd.DataFrame({'b': [True, False, True, False]}),
        ibis_expr_func=lambda t: t.select(not_b=~t.b),
        pandas_expr_func=lambda df: pd.DataFrame({'not_b': ~df['b']}))
@pytest.mark.skip(reason='Hash operation is not defined')
def test_op_hash_bytes():
    # This is typically for hashing raw byte data, not directly exposed for string columns usually.
    # The Ibis hash() method is more general.
    # For a test, we'll try with string and expect a numeric hash.
    run_test_case(
        op_name='HashBytes',
        data=pd.DataFrame({'s': ['data1', 'data2', 'data1']}),
        ibis_expr_func=lambda t: t.select(hashed_val=t.s.hash()), # Using generic hash for demonstration
        pandas_expr_func=lambda df: pd.DataFrame({'hashed_val': df['s'].apply(lambda x: hash(x))})) # Python's hash
@pytest.mark.skip(reason='AttributeError: \'StringScalar\' object has no attribute \'checksum\'')
def test_op_hex_digest():
    # This implies a cryptographic hash like MD5, SHA1 etc. which are backend-specific.
    # Ibis has `.hash()` which is a general non-cryptographic hash.
    # A true test for HexDigest would need specific backend support for algorithms.
    # Placeholder using generic hash, result type check.
    run_test_case(
        op_name='HexDigest',
        data=pd.DataFrame({'s': ['text1', 'text2']}),
        ibis_expr_func=lambda t: t.select(hex_hash=ibis.literal('md5').checksum(t.s)), # Example Ibis syntax for crypto hash
        pandas_expr_func=lambda df: pd.DataFrame({'hex_hash': df['s'].apply(lambda x: pd.util.hash_array(np.array([x]).astype('U')).hex())})) # Placeholder, not actual MD5
# SELECT "t1"."category", CASE WHEN "t1"."any_true" THEN 1 ELSE 0 END AS "any_true" FROM (SELECT "t0"."category", MAX(CASE WHEN "t0"."value" THEN 1 ELSE 0 END) AS "any_true" FROM "ibis_test_anyaggregation" AS "t0" GROUP BY "t0"."category") AS "t1";
@pytest.mark.skip(reason='SQreamError: WrongTypes (ScalarType \"bool\") [ ScalarType \"int4\" ]')
def test_op_any_aggregation():
    run_test_case(
        op_name='AnyAggregation',
        data=pd.DataFrame({'category': [1, 1, 2, 2], 'value': [True, False, False, False]}),
        ibis_expr_func=lambda t: t.group_by('category').aggregate(any_true=t.value.any()),
        pandas_expr_func=lambda df: df.groupby('category', as_index=False).agg(any_true=('value', 'any')))
# SELECT "t1"."category", CASE WHEN "t1"."all_true" THEN 1 ELSE 0 END AS "all_true" FROM (SELECT "t0"."category", MIN(CASE WHEN "t0"."value" THEN 1 ELSE 0 END) AS "all_true" FROM "ibis_test_allaggregation" AS "t0" GROUP BY "t0"."category") AS "t1";
@pytest.mark.skip(reason='SQreamError: WrongTypes (ScalarType \"bool\") [ ScalarType \"int4\" ]')
def test_op_all_aggregation():
    run_test_case(
        op_name='AllAggregation',
        data=pd.DataFrame({'category': [1, 1, 2, 2], 'value': [True, True, False, True]}),
        ibis_expr_func=lambda t: t.group_by('category').aggregate(all_true=t.value.all()),
        pandas_expr_func=lambda df: df.groupby('category', as_index=False).agg(all_true=('value', 'all')))
@pytest.mark.skip(reason='timestamp')
def test_op_timestamp_add_seconds():
    run_test_case(
        op_name='TimestampAddSeconds',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-02 11:00:00']), 's': [60, 3600]}),
        ibis_expr_func=lambda t: t.select(new_ts=t.ts + t.s.seconds()),
        pandas_expr_func=lambda df: pd.DataFrame({'new_ts': df['ts'] + pd.to_timedelta(df['s'], unit='s')}))
@pytest.mark.skip(reason='timestamp')
def test_op_timestamp_sub_minutes():
    run_test_case(
        op_name='TimestampSubMinutes',
        data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-02 11:00:00']), 'm': [30, 90]}),
        ibis_expr_func=lambda t: t.select(new_ts=t.ts - t.m.minutes()),
        pandas_expr_func=lambda df: pd.DataFrame({'new_ts': df['ts'] - pd.to_timedelta(df['m'], unit='m')}))
# SELECT _IBIS_LPAD("t0"."s", 5, '0') AS "padded" FROM "ibis_test_lpad" AS "t0";
@pytest.mark.skip(reason='SQreamError: Function call not supported: _ibis_lpad(text, int, unknown type)')
def test_op_lpad():
    run_test_case(
        op_name='LPad',
        data=pd.DataFrame({'s': ['abc', 'defg']}),
        ibis_expr_func=lambda t: t.select(padded=t.s.lpad(5, '0')),
        pandas_expr_func=lambda df: pd.DataFrame({'padded': df['s'].str.pad(5, side='left', fillchar='0')}))
# SELECT _IBIS_RPAD("t0"."s", 5, '0') AS "padded" FROM "ibis_test_lpad" AS "t0";
@pytest.mark.skip(reason='SQreamError: Function call not supported: _ibis_rpad(text, int, unknown type)')
def test_op_rpad():
    run_test_case(
        op_name='RPad',
        data=pd.DataFrame({'s': ['abc', 'defg']}),
        ibis_expr_func=lambda t: t.select(padded=t.s.rpad(5, '*')),
        pandas_expr_func=lambda df: pd.DataFrame({'padded': df['s'].str.pad(5, side='right', fillchar='*')}))