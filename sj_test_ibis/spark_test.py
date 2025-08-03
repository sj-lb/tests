import os
import sys
import logging
import pandas as pd
import numpy as np
import pytest
import ibis
from ibis.expr import operations as ops
from ibis import _
import traceback
# Use the direct connect function that is known to work
from ibis_sqreamdb import connect
from crcmod.predefined import mkCrcFun # requires python3.11 -m pip install crcmod
import ibis.expr.datatypes as dt

# from ibis import datatypes as dt # Import datatypes

HOST = os.environ.get("IBIS_SQREAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
USER = os.environ.get("IBIS_SQREAM_USER", "sqream")
PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")
CLUSTERED = os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"
ibis_con = connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

ibis.set_backend('sqream://sqream:sqream@192.168.4.31:5000')

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/ibis_sqream_all_ops_test.log", mode='w'),
        logging.StreamHandler(sys.stdout)])


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
    logging.info(f"--- Running Test: {op_name} ---")
    
    table_name = f"ibis_test_{op_name.lower()}"
    
    try:
        schema_dict = {
            name: pandas_dtype_to_ibis_string(dtype, data[col]) for col, (name, dtype) in zip(data.columns, data.dtypes.items())}
        schema = ibis.schema(schema_dict)
        
        ibis_con.create_table(table_name, schema=schema, overwrite=True)
        logging.info(f"Created empty table '{table_name}' with schema: {schema}")

        ibis_con.insert(table_name, obj=data)
        logging.info(f"Inserted data into '{table_name}'")
        
        ibis_table = ibis_con.table(table_name)
        ibis_expr = ibis_expr_func(ibis_table)
        
        expected_df = pandas_expr_func(data)
            
        logging.info("Executing Ibis query...")
        ibis_result_df = ibis_expr.execute()

        # Standardize dataframes for robust comparison
        if isinstance(ibis_result_df, pd.Series):
            ibis_result_df = ibis_result_df.to_frame().reset_index(drop=True)
        if isinstance(expected_df, pd.Series):
            expected_df = expected_df.to_frame().reset_index(drop=True)

        for col in expected_df.columns:
            if col in ibis_result_df.columns:
                try:
                    expected_df[col] = expected_df[col].dt.tz_localize('UTC')
                    ibis_result_df[col] = ibis_result_df[col].dt.tz_localize('UTC')
                except:
                    pass
                ibis_result_df[col] = ibis_result_df[col].astype(expected_df[col].dtype)
        print(f'\033[32;1mibis result:\033[33m\n{ibis_result_df}\033[32m\nexpected result:\033[33m\n{expected_df}\033[m')
        logging.info("Ibis Result:\n%s", ibis_result_df)
        logging.info("Pandas Expected Result:\n%s", expected_df)

        pd.testing.assert_frame_equal(ibis_result_df, expected_df, check_dtype=True)
        logging.info(f"✅ Assertion successful for operation: {op_name}")
    except Exception as e:
        print(f'\033[31mERROR: {e}\n{traceback.format_exc()}\033[m')
        raise e
    finally:
        logging.info(f"Cleaning up table '{table_name}'...")
        try:
            ibis_con.drop_table(table_name, force=True)
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

    # ibis_con = connect(
    #     host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

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

            ibis_con.create_table(table_name, schema=schema, overwrite=True)
            logging.info(f"Created empty table '{table_name}' with schema: {schema}")

            ibis_con.insert(table_name, obj=df)
            logging.info(f"Inserted data into '{table_name}'")

            ibis_tables[table_key] = ibis_con.table(table_name)

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
                ibis_con.drop_table(table_name_to_drop, force=True)
                logging.info(f"Cleaned up table '{table_name_to_drop}'")
            except Exception as e:
                logging.error(f"Could not drop table {table_name_to_drop}. Reason: {e}")

def test_op_arbitrary():
    run_test_case(
        op_name='Arbitrary',
        data=pd.DataFrame({'key': [1, 1, 2, 2], 'value': ['a', 'b', 'c', 'd']}),
        ibis_expr_func=lambda t: t.group_by('key').aggregate(arbitrary_val=t.value.arbitrary()),
        pandas_expr_func=lambda df: df.groupby('key', as_index=False).agg(arbitrary_val=('value', lambda x: x.iloc[0])))

def test_op_array_flatten():
    run_test_case(
        op_name='ArrayFlatten',
        data=pd.DataFrame({'nested_arr': [[[1, 2], [3]], [[4, 5]]]}),
        ibis_expr_func=lambda t: t.select(flattened_arr=t.nested_arr.flatten()),
        pandas_expr_func=lambda df: pd.DataFrame({'flattened_arr': df['nested_arr'].apply(lambda x: [item for sublist in x for item in sublist])}))

def test_op_array_remove():
    run_test_case(
        op_name='ArrayRemove',
        data=pd.DataFrame({'arr': [[1, 2, 2, 3], [4, 5, 4], [10]]}),
        ibis_expr_func=lambda t: t.select(cleaned_arr=t.arr.remove(2)),
        pandas_expr_func=lambda df: pd.DataFrame({'cleaned_arr': df['arr'].apply(lambda x: [elem for elem in x if elem != 2])}))

def test_op_array_zip():
    run_test_case(
        op_name='ArrayZip',
        data=pd.DataFrame({'arr1': [[1, 2], [3, 4]], 'arr2': [['a', 'b'], ['c', 'd']]}),
        ibis_expr_func=lambda t: t.select(zipped_arr=t.arr1.array_zip(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'zipped_arr': df.apply(lambda row: list(zip(row['arr1'], row['arr2'])), axis=1)}))

def test_op_field():
    run_test_case(
        op_name='Field',
        data=pd.DataFrame({'struct_col': [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]}),
        ibis_expr_func=lambda t: t.select(extracted_field=t.struct_col.field('a')),
        pandas_expr_func=lambda df: pd.DataFrame({'extracted_field': df['struct_col'].apply(lambda x: x['a'])}))
        # ibis_schema=ibis.schema({'struct_col': dt.Struct({'a': dt.int64, 'b': dt.string})}))

def test_op_first_value():
    run_test_case(
        op_name='FirstValue',
        data=pd.DataFrame({'key': [1, 1, 2, 2], 'value': [10, 20, 30, 40], 'order_col': [1, 2, 1, 2]}),
        ibis_expr_func=lambda t: t.group_by('key').order_by('order_col').select(first_val=t.value.first()),
        pandas_expr_func=lambda df: df.sort_values('order_col').groupby('key', as_index=False)['value'].transform(lambda x: x.iloc[0]).to_frame('first_val'))
@pytest.mark.skip(reason='not supported in SQream')
def test_op_in_subquery():
    sub_df = pd.DataFrame({'allowed_fruit': ['apple', 'cherry']})

    run_test_case(
        op_name='InSubquery',
        data=pd.DataFrame({'id': [1, 2, 3, 4], 'value': ['apple', 'banana', 'cherry', 'date']}),
        ibis_expr_func=lambda t: t.select(is_allowed=t.value.isin(ibis.memtable(sub_df).allowed_fruit)),
        pandas_expr_func=lambda df: pd.DataFrame({'is_allowed': df['value'].isin(sub_df['allowed_fruit'])}))

def test_op_interval_from_integer():
    run_test_case(
        op_name='IntervalFromInteger',
        data=pd.DataFrame({'date_col': pd.to_datetime(['2023-01-01', '2023-01-01', '2023-01-01']), 'days_val': [5, -3, 0]}),
        ibis_expr_func=lambda t: t.select(new_date=t.date_col + t.days_val.as_interval('D')),
        pandas_expr_func=lambda df: pd.DataFrame({'new_date': df['date_col'] + pd.to_timedelta(df['days_val'], unit='D')}))

def test_op_last_value():
    run_test_case(
        op_name='LastValue',
        data=pd.DataFrame({'key': [1, 1, 2, 2], 'value': [10, 20, 30, 40], 'order_col': [1, 2, 1, 2]}),
        # LAST_VALUE as a window function requires an ORDER BY.
        ibis_expr_func=lambda t: t.group_by('key').order_by('order_col').select(last_val=t.value.last()),
        pandas_expr_func=lambda df: df.sort_values('order_col').groupby('key', as_index=False)['value'].transform(lambda x: x.iloc[-1]).to_frame('last_val'))

def test_op_lstrip():
    run_test_case(
        op_name='LStrip',
        data=pd.DataFrame({'s': ['  hello', 'world  ', '  foo bar  ']}),
        ibis_expr_func=lambda t: t.select(stripped_s=t.s.lstrip()),
        pandas_expr_func=lambda df: pd.DataFrame({'stripped_s': df['s'].str.lstrip()}))

def test_op_map_contains():
    run_test_case(
        op_name='MapContains',
        data=pd.DataFrame({'map_col': [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}, {}, None]}),
        ibis_expr_func=lambda t: t.select(has_key_a=t.map_col.contains('a')),
        pandas_expr_func=lambda df: pd.DataFrame({'has_key_a': df['map_col'].apply(lambda x: 'a' in x if x is not None else None)}))

def test_op_non_null_literal():
    run_test_case(
        op_name='NonNullLiteral',
        data=pd.DataFrame({'dummy': [1]}),
        ibis_expr_func=lambda t: t.select(ibis.literal("hello").notnull().name('is_not_null')),
        pandas_expr_func=lambda df: pd.DataFrame({'is_not_null': pd.notna(['hello'])}))

def test_op_not_null():
    run_test_case(
        op_name='NotNull',
        data=pd.DataFrame({'val': [1, None, 3, np.nan, 5]}),
        ibis_expr_func=lambda t: t.select(is_not_null=t.val.notnull()),
        pandas_expr_func=lambda df: pd.DataFrame({'is_not_null': df['val'].notna()}))

def test_op_rstrip():
    run_test_case(
        op_name='RStrip',
        data=pd.DataFrame({'s': ['  hello', 'world  ', '  foo bar  ']}),
        ibis_expr_func=lambda t: t.select(stripped_s=t.s.rstrip()),
        pandas_expr_func=lambda df: pd.DataFrame({'stripped_s': df['s'].str.rstrip()}))

def test_op_time():
    run_test_case(
        op_name='Time',
        data=pd.DataFrame({'ts_col': pd.to_datetime(['2023-07-20 10:30:15', '2023-07-20 00:00:00', '2023-07-20 23:59:59'])}),
        ibis_expr_func=lambda t: t.select(time_val=t.ts_col.time()),
        pandas_expr_func=lambda df: pd.DataFrame({'time_val': df['ts_col'].dt.time}))

def test_op_time_timestamp_range():
    start_ts = pd.Timestamp('2000-01-01 00:00:00')
    end_ts = pd.Timestamp('2000-01-01 03:00:00')
    interval_step = ibis.interval(hours=1)

    expected_range = pd.date_range(start=start_ts, end=end_ts - pd.Timedelta(seconds=1), freq='h')

    run_test_case(
        op_name='TimeTimestampRange',
        data=pd.DataFrame({'value': []}),
        ibis_expr_func=lambda t: ibis.range(start_ts, end_ts, interval_step).unnest().name('value').to_table(),
        pandas_expr_func=lambda df: pd.DataFrame({'value': expected_range}))

def test_op_timestamp_truncate():
    run_test_case(
        op_name='TimestampTruncate',
        data=pd.DataFrame({'ts_col': pd.to_datetime(['2023-05-15 14:35:10.123', '2024-01-01 00:00:00.000'])}),
        ibis_expr_func=lambda t: t.select(truncated_hour=t.ts_col.truncate('hour')),
        pandas_expr_func=lambda df: pd.DataFrame({'truncated_hour': df['ts_col'].dt.floor('h')}))

@ibis.udf.scalar.builtin
def multiply_by_two(x: float) -> float:
    return x * 2

def test_op_vectorized_udf():
    run_test_case(
        op_name='VectorizedUDF',
        data=pd.DataFrame({'value': [1.0, 2.5, 3.0]}),
        ibis_expr_func=lambda t: t.select(doubled_val=multiply_by_two(t.value)),
        pandas_expr_func=lambda df: pd.DataFrame({'doubled_val': df['value'] * 2}))

def test_op_window_aggregate():
    run_test_case(
        op_name='WindowAggregate',
        data=pd.DataFrame({'key': [1, 1, 2, 2], 'value': [10, 20, 30, 40]}),
        ibis_expr_func=lambda t: t.select(key=t.key, value=t.value, sum_over_key=t.value.sum().over(ibis.window(group_by='key'))),
        pandas_expr_func=lambda df: df.assign(sum_over_key=df.groupby('key')['value'].transform('sum')))

def test_op_window_function():
    run_test_case(
        op_name='WindowFunction',
        data=pd.DataFrame({'key': ['A', 'A', 'B', 'B'], 'value': [10, 20, 30, 10]}),
        ibis_expr_func=lambda t: t.select(key=t.key, value=t.value, rank_val=t.value.rank().over(ibis.window(group_by='key', order_by='value'))),
        pandas_expr_func=lambda df: df.assign(rank_val=df.groupby('key')['value'].rank(method='min').astype(int))) # method='min' for SQL RANK() behavior
