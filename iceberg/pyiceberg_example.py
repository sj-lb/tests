import pandas as pd
import pyarrow as pa
from pyiceberg.catalog import load_catalog

cat = load_catalog(
    "my_catalog",
    **{
        'type': 'rest',
        'uri': 'http://192.168.5.82:8181',
        # Warehouse Location (Base path for table data)
        'warehouse': 's3://warehouse',
        # I/O Implementation (required for file operations)
        'io-impl': 'pyiceberg.io.pyarrow.PyArrowFileIO',
        # S3/MinIO Connection Details (for PyArrowFileIO to read/write data)
        's3.endpoint': 'http://192.168.5.82:9000',
        's3.path-style-access': 'true',
        's3.access-key-id': 'admin',
        's3.secret-access-key': 'password',
        'client.region': 'us-east-1'
    })
ice_tbl = cat.load_table("my_namespace.t_sj_bla")

df = pd.read_parquet(
    "/home/johnny/00000-0-18c2db9f-72dc-45a4-876c-c5d8bc7672c6.parquet",
    engine="pyarrow",
    dtype_backend="pyarrow")
arw_tbl = pa.Table.from_pandas(df)

ice_tbl.append(arw_tbl)
