import os
import sys
import logging
import pandas as pd
import numpy as np
if __name__ != '__main__':
    import pytest
else:
    class pytest_skip:
        @staticmethod
        class mark():
            def skip(reason):
                def decorator(func):
                    return func
                return decorator
    pytest = pytest_skip()
import ibis
from ibis import _
from ibis_sqreamdb import connect

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/ibis_sqream_all_ops_test.log", mode='w'),
        logging.StreamHandler(sys.stdout)])

# --- Database Connection Details ---
HOST = os.environ.get("IBIS_SQREAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
USER = os.environ.get("IBIS_SQREAM_USER", "sqream")
PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")
CLUSTERED = os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"
con = connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)
# --- Helper Function for Running a Single Test Case ---
def pandas_dtype_to_ibis_string(dtype, col=None):
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

        for col in expected_df.columns:
            if col in ibis_result_df.columns:
                try:
                    expected_df[col] = expected_df[col].dt.tz_localize('UTC')
                    ibis_result_df[col] = ibis_result_df[col].dt.tz_localize('UTC')
                except:
                    pass
                ibis_result_df[col] = ibis_result_df[col].astype(expected_df[col].dtype)

        logging.info("Ibis Result:\n%s", ibis_result_df)
        logging.info("Pandas Expected Result:\n%s", expected_df)

        print(f'\033[32;1mibis result:\033[33m\n{ibis_result_df}\033[32m\nexpected result:\033[33m\n{expected_df}\033[m')
        pd.testing.assert_frame_equal(ibis_result_df, expected_df, check_dtype=True)
        logging.info(f"✅ Assertion successful for operation: {op_name}")
    finally:
        logging.info(f"Cleaning up table '{table_name}'...")
        try:
            con.drop_table(table_name, force=True)
            logging.info(f"Cleaned up table '{table_name}'")
        except Exception as e:
            logging.error(f"Could not drop table {table_name}. Reason: {e}")

# --- Test Functions For Each Operation ---
def test_op_array_distinct():
    run_test_case(
        op_name='ArrayDistinct',
        data=pd.DataFrame({'arr': [[1, 2, 2, 3], [4, 5, 4]]}),
        ibis_expr_func=lambda t: t.select(distinct_arr=t.arr.unique()),
        pandas_expr_func=lambda df: pd.DataFrame({'distinct_arr': df['arr'].apply(lambda x: sorted(list(set(x))))})) # Sort for comparison
@pytest.mark.skip(reason='no params yet')
def test_op_array_filter():
    run_test_case(
        op_name='ArrayFilter',
        data=pd.DataFrame({'arr': [[1, 2, 3, 4], [5, 6, 7]]}),
        ibis_expr_func=lambda t: t.select(filtered_arr=t.arr.filter(lambda x: x % 2 == 0)),
        pandas_expr_func=lambda df: pd.DataFrame({'filtered_arr': df['arr'].apply(lambda x: [item for item in x if item % 2 == 0])}))
def test_op_array_intersect():
    run_test_case(
        op_name='ArrayIntersect',
        data=pd.DataFrame({'arr1': [[1, 2, 3], [4, 5]], 'arr2': [[2, 3, 4], [3, 5, 6]]}),
        ibis_expr_func=lambda t: t.select(intersect=t.arr1.intersect(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'intersect': df.apply(lambda row: sorted(list(set(row['arr1']) & set(row['arr2']))), axis=1)}))
@pytest.mark.skip(reason='no params yet')
def test_op_array_map():
    run_test_case(
        op_name='ArrayMap',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5, 6]]}),
        ibis_expr_func=lambda t: t.select(mapped=t.arr.map(lambda x: x * 2)),
        pandas_expr_func=lambda df: pd.DataFrame({'mapped': df['arr'].apply(lambda x: [item * 2 for item in x])}))
def test_op_array_max():
    run_test_case(
        op_name='ArrayMax',
        data=pd.DataFrame({'arr': [[1, 5, 2], [8, 3, 9]]}),
        ibis_expr_func=lambda t: t.select(array_max=t.arr.maxs()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_max': df['arr'].apply(max)}))
def test_op_array_mean():
    run_test_case(
        op_name='ArrayMean',
        data=pd.DataFrame({'arr': [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]}),
        ibis_expr_func=lambda t: t.select(array_mean=t.arr.means()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_mean': df['arr'].apply(np.mean)}))
def test_op_array_min():
    run_test_case(
        op_name='ArrayMin',
        data=pd.DataFrame({'arr': [[1, 5, 2], [8, 3, 9]]}),
        ibis_expr_func=lambda t: t.select(array_min=t.arr.mins()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_min': df['arr'].apply(min)}))
@pytest.mark.skip(reason='no params yet')
def test_op_array_repeat():
    run_test_case(
        op_name='ArrayRepeat',
        data=pd.DataFrame({'value': ['A', 'B'], 'times': [2, 3]}),
        ibis_expr_func=lambda t: t.select(
            repeated=ibis.expr.operations.ArrayRepeat( #TODO: call organically
                arg=ibis.array([t.value]), # Create an array containing the single value
                times=t.times.cast(ibis.expr.datatypes.int32)).to_expr()),
        pandas_expr_func=lambda df: pd.DataFrame({'repeated': df.apply(lambda row: [row['value']] * row['times'], axis=1)}))
@pytest.mark.skip(reason='no params yet')
def test_op_array_slice():
    run_test_case(
        op_name='ArraySlice',
        data=pd.DataFrame({'arr': [[1, 2, 3, 4, 5], [6, 7, 8]]}),
        ibis_expr_func=lambda t: t.select(sliced=t.arr[1:3]),
        pandas_expr_func=lambda df: pd.DataFrame({'sliced': df['arr'].apply(lambda x: x[1:3])}))
def test_op_array_sort():
    run_test_case(
        op_name='ArraySort',
        data=pd.DataFrame({'arr': [[3, 1, 2], [6, 4, 5]]}),
        ibis_expr_func=lambda t: t.select(sorted_arr=t.arr.sort()),
        pandas_expr_func=lambda df: pd.DataFrame({'sorted_arr': df['arr'].apply(sorted)}))
def test_op_array_sum():
    run_test_case(
        op_name='ArraySum',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5, 6]]}),
        ibis_expr_func=lambda t: t.select(array_sum=t.arr.sums()),
        pandas_expr_func=lambda df: pd.DataFrame({'array_sum': df['arr'].apply(sum)}))
def test_op_array_union():
    run_test_case(
        op_name='ArrayUnion',
        data=pd.DataFrame({'arr1': [[1, 2], [3, 4]], 'arr2': [[2, 3], [4, 5]]}),
        ibis_expr_func=lambda t: t.select(union=t.arr1.union(t.arr2)),
        pandas_expr_func=lambda df: pd.DataFrame({'union': df.apply(lambda row: sorted(list(set(row['arr1']) | set(row['arr2']))), axis=1)}))
def test_op_array_length():
    run_test_case(
        op_name='ArrayLength',
        data=pd.DataFrame({'arr': [[1, 2, 3], [4, 5]]}),
        ibis_expr_func=lambda t: t.select(arr_length=t.arr.length()),
        pandas_expr_func=lambda df: pd.DataFrame({'arr_length': df['arr'].apply(len)}))

if __name__ == "__main__":
    test_op_array_max()