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
# ARRAYS
arr_df = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "tags": [
        ["sql", "ibis", "python"],
        ["sqream"],
        ["data", "etl"],
        [],
        ["ml", "qa", "backend", "arrays"]
    ],
    "age": [
        [14, 17, 21],
        [101, 99],
        [55],
        [],
        [None, 34, None, 68]
    ]
})

# Define Ibis table schema
arr_schema_dict = {
    "id": "int64",
    "tags": "array<string>",
    "age": "array<int32>",
}
#  arr_schema = ibis.schema(arr_schema_dict)
#  con.create_table("arrays", schema=arr_schema, overwrite=True)
#  con.insert("arrays", obj=arr_df)
#  arrays = con.table('arrays')



#  t1_df = pd.DataFrame({
    #  "id": [1, 2],
    #  "value": ["A", "B"]
#  })
#  t2_df = pd.DataFrame({
    #  "id": [3, 4],
    #  "value": ["C", "D"]
#  })

create_table(con, "t_array", arr_df)
t1 = con.table('t_array')
#  create_table(con, "t_union1", t1_df)
#  create_table(con, "t_union2", t2_df)
#  t1 = con.table('t_union1')
#  t2 = con.table('t_union2')


# NEW FUNCTION BY JOHNNY
#  q_index = arrays.select(
    #  arrays.id,
    #  arrays.age.array_max().name("max_value")
#  )
#  ar1 = q_index.execute()
#  logging.info(f'Result: {ar1 = }')




print('\033[33;1m-- q1 --\033[m')
x1 = t1.age.maxs()
q1 = x1.compile()
print(f'SQL Compiled: {q1}')
try:
    a1 = t1.select(x1).execute()
    print(f'Result:\n{a1}')
except Exception as e:
    print(f'\033[31mError during execution: {e}\033[m')
