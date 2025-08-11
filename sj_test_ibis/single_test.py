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

# from ibis import datatypes as dt # Import datatypes


HOST = os.environ.get("IBIS_SQREAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
USER = os.environ.get("IBIS_SQREAM_USER", "sqream")
PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")
CLUSTERED = os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"
ibis_con = connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

ibis.set_backend('sqream://sqream:sqream@127.0.0.1:5000')

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
            ibis_result_df = ibis_result_df.to_frame()
        if isinstance(expected_df, pd.Series):
            expected_df = expected_df.to_frame()

        for col in expected_df.columns:
            if col in ibis_result_df.columns:
                try:
                    expected_df[col] = expected_df[col].dt.tz_localize('UTC')
                    ibis_result_df[col] = ibis_result_df[col].dt.tz_localize('UTC')
                except:
                    pass
                ibis_result_df[col] = ibis_result_df[col].astype(expected_df[col].dtype)
        expected_df = expected_df.reset_index(drop=True)
        ibis_result_df = ibis_result_df.reset_index(drop=True)
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

# def test_op_arg_max():
#     run_test_case(
#         op_name='ArgMax',
#         data=pd.DataFrame({'id': [1, 2, 3, 4], 'value': [10, 50, 20, 30]}),
#         ibis_expr_func=lambda t: t.aggregate(id_at_max=t.id.argmax(t.value)),
#         pandas_expr_func=lambda df: pd.DataFrame({'id_at_max': [df.loc[df['value'].idxmax(), 'id']]}))

# def test_op_find_in_set():
#     run_test_case(
#         op_name='FindInSet',
#         data=pd.DataFrame({'haystack': ['a,b,c', 'x,y'], 'needle': ['b', 'z']}),
#         ibis_expr_func=lambda t: t.select(found=ibis.literal(',').join([t.haystack]).find_in_set(t.needle)), # This Ibis expression might vary
#         pandas_expr_func=lambda df: pd.DataFrame({'found': df.apply(lambda row: (row['needle'] in row['haystack'].split(',')) if pd.notna(row['haystack']) else False, axis=1)}))


# def test_op_first():
#     run_test_case(
#         op_name='First',
#         data=pd.DataFrame({'id': [1, 2, 3], 'value': ['a', 'b', 'c']}),
#         ibis_expr_func=lambda t: t.aggregate(first_val=t.value.first()),
#         pandas_expr_func=lambda df: pd.DataFrame({'first_val': [df['value'].iloc[0]]}))

# def test_op_last():
#     run_test_case(
#         op_name='Last',
#         data=pd.DataFrame({'id': [1, 2, 3], 'value': [100.1, 10.2, 1.3]}),
#         ibis_expr_func=lambda t: t.aggregate(last_val=t.value.last()),
#         pandas_expr_func=lambda df: pd.DataFrame({'last_val': [df['value'].iloc[-1]]}))

# def test_op_group_concat():
#     run_test_case(
#         op_name='GroupConcat',
#         data=pd.DataFrame({'group_col': ['A', 'A', 'B', 'B'], 'value': ['foo', 'bar', 'baz', 'qux']}),
#         ibis_expr_func=lambda t: t.group_by('group_col').aggregate(concatenated=t.value.group_concat(', ')),
#         pandas_expr_func=lambda df: df.groupby('group_col', as_index=False)['value'].apply(lambda x: ', '.join(x)).reset_index())

# def test_op_range():
#     start_val, end_val = 0, 5
#     run_test_case(
#         op_name='RangeFloat',
#         data=pd.DataFrame({'value': []}, dtype=np.int32), # Just for schema and expected df
#         ibis_expr_func=lambda t: ibis.range(start_val, end_val + 1, 1),
#         pandas_expr_func=lambda df: pd.DataFrame({'value': np.arange(start_val, end_val + 1)}))

# def test_op_timestamp_bucket():
#     run_test_case(
#         op_name='TimestampBucket',
#         data=pd.DataFrame({'ts': pd.to_datetime(['2023-01-01 10:05:00', '2023-01-01 10:15:00', '2023-01-01 10:25:00'])}, dtype='datetime64[ms]'),
#         ibis_expr_func=lambda t: t.select(bucket=t.ts.bucket(ibis.interval(10, 'm'))),
#         pandas_expr_func=lambda df: pd.DataFrame({'bucket': df['ts'].dt.floor('10min')}))

# def test_op_integer_range():
#     start_val, end_val = 1, 5
#     run_test_case(
#         op_name='IntegerRange',
#         data=pd.DataFrame({'value': []}, dtype=np.int32),
#         ibis_expr_func=lambda t, ibis_con: ibis_con.insert(t.op().name, obj=ibis.range(start_val, end_val + 1).to_pandas()),
#         pandas_expr_func=lambda df: pd.DataFrame({'value': range(start_val, end_val + 1)}))

# def test_op_pct_change():
#     run_test_case(
#         op_name='PctChange',
#         data=pd.DataFrame({'value': [10.0, 20.0, 15.0, 5.0, 0.0, 10.0, np.nan, 5.0, 0.0, 0.0, 20.0]}),
#         ibis_expr_func=lambda t: t.select(pct_change_val=(t.value - t.value.lag()) / t.value.lag()),
#         pandas_expr_func=lambda df: pd.DataFrame({'pct_change_val': df['value'].pct_change()}))

# def test_op_array_all():
#     run_test_case(
#         op_name='ArrayAll',
#         data=pd.DataFrame({'values': [[True, True], [True, False], [False, False]]}),
#         ibis_expr_func=lambda t: t.select(all_true=t.values.all()),
#         pandas_expr_func=lambda df: pd.DataFrame({'all_true': df['values'].apply(all)}))

# def test_op_array_concat():
#     run_test_case(
#         op_name='ArrayConcat',
#         data=pd.DataFrame({'arr1': [[1, 2], [3]], 'arr2': [[4], [5, 6]]}),
#         ibis_expr_func=lambda t: t.select(concatenated=t.arr1.concat(t.arr2)),
#         pandas_expr_func=lambda df: pd.DataFrame({'concatenated': df.apply(lambda row: row['arr1'] + row['arr2'], axis=1)}))

# def test_op_least():
#     run_test_case(
#         op_name='Least',
#         data=pd.DataFrame({'a': [1, 5, 3], 'b': [4, 2, 6], 'c': [7, 1, 5]}),
#         ibis_expr_func=lambda t: t.select(min_val=ibis.least(t.a, t.b, t.c)),
#         pandas_expr_func=lambda df: pd.DataFrame({'min_val': df[['a', 'b', 'c']].min(axis=1)}))

# def test_op_window_function():
#     run_test_case(
#         op_name='WindowFunction',
#         data=pd.DataFrame({'key': ['A', 'A', 'B', 'B'], 'value': [10, 20, 30, 10]}),
#         ibis_expr_func=lambda t: t.select(key=t.key, value=t.value, rank_val=t.value.rank().over(ibis.window(group_by='key', order_by='value'))),
#         pandas_expr_func=lambda df: df.assign(rank_val=df.groupby('key')['value'].rank(method='min').astype(int))) # method='min' for SQL RANK() behavior

# def test_op_arbitrary():
#     run_test_case(
#         op_name='Arbitrary',
#         data=pd.DataFrame({'key': [1, 1, 2, 2], 'value': ['a', 'b', 'c', 'd']}),
#         ibis_expr_func=lambda t: t.group_by('key').aggregate(arbitrary_val=t.value.arbitrary()),
#         pandas_expr_func=lambda df: df.groupby('key', as_index=False).agg(arbitrary_val=('value', lambda x: x.iloc[0])))
