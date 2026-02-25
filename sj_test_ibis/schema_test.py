import os
from ibis_sqreamdb import connect
# ==========================================
# 1. SETUP & CONNECT
# ==========================================
conn = connect(
    host=os.environ.get("IBIS_SQREAM_HOST", "127.0.0.1"),
    port=int(os.environ.get("IBIS_SQREAM_PORT", 5000)),
    user=os.environ.get("IBIS_SQREAM_USER", "sqream"),
    password=os.environ.get("IBIS_SQREAM_PASSWORD", "sqream"),
    database=os.environ.get("IBIS_SQREAM_DATABASE", "master"),
    clustered=os.environ.get("IBIS_SQREAM_CLUSTERED", "false").lower() == "true"
)
# ==========================================
# 2. DEFINE 1 TABLE & 1 QUERY
# ==========================================
# Table: store_sales
store_sales = conn.table('ext_table')
store_sales = conn.table('s_ext_table', database = 's')