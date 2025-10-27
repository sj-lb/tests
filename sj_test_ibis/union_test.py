import os
import ibis
import pandas as pd

# from ibis import _
# Use the direct connect function that is known to work
from ibis_sqreamdb import connect

# --- Database Connection Details ---
HOST = os.environ.get("IBIS_SQREAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
USER = os.environ.get("IBIS_SQREAM_USER", "sqream")
PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")
CLUSTERED = os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"
con = connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE, clustered=CLUSTERED)

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

# Helper function: create & insert table from pandas DataFrame
def create_table(con, table_name, data):
    schema_dict = {
        name: pandas_dtype_to_ibis_string(dtype, data[col]) for col, (name, dtype) in zip(data.columns, data.dtypes.items())}
    schema = ibis.schema(schema_dict)
    con.create_table(table_name, schema=schema, overwrite=True)
    con.insert(table_name, obj=data)
    return 


# --- 4. union tables ---
t1_df = pd.DataFrame({
    "id": [1, 2],
    "value": ["A", "B"]
})
t2_df = pd.DataFrame({
    "id": [3, 4],
    "value": ["C", "D"]
})

create_table(con, "t_union1", t1_df)
create_table(con, "t_union2", t2_df)
t1 = con.table('t_union1')
t2 = con.table('t_union2')

print('\033[33;1m-- q1: distinct=False --\033[m')
x1 = t1.union(t2, distinct=False)
q1 = x1.compile()
print(f'SQL Compiled: {q1}')
try:
    a1 = x1.execute()
    print(f'Result:\n{a1}')
except Exception as e:
    print(f'\033[31mError during execution: {e}\033[m')

print('\033[33;1m-- q2: default (distinct=False) --\033[m')
x2 = t1.union(t2)
q2 = x2.compile()
print(f'SQL Compiled: {q2}')
try:
    a2 = x2.execute()
    print(f'Result:\n{a2}')
except Exception as e:
    print(f'\033[31mError during execution: {e}\033[m')

print('\033[33;1m-- q3: distinct=True --\033[m')
x3 = t1.union(t2, distinct=True)
q3 = x3.compile()
print(f'SQL Compiled: {q3}')
try:
    a3 = x3.execute()
    print(f'Result:\n{a3}')
except Exception as e:
    print(f'\033[31mError during execution: {e}\033[m')

# ARRAY LENGTH TEST
print('\033[33;1m-- array length test --\033[m')
t_arr_df = pd.DataFrame({
    "id": [1, 2],
    "value": [["A", "B"], ["C"]]
})

create_table(con, "t_array", t_arr_df)
t_arr = con.table('t_array')

x_arr = t_arr.value.length()
q_arr = x_arr.compile()
print(f'SQL Compiled: {q_arr}')
try:
    a_arr = x_arr.execute()
    print(f'Result:\n{a_arr}')
except Exception as e:
    print(f'\033[31mError during execution: {e}\033[m')