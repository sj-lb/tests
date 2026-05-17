from sj.utils.pyspark import get_session
from time import sleep
# 1. Initialize SparkSession 
spark = get_session('0.103')
# 2. Setup Namespace and ensure clean table
spark.sql("CREATE NAMESPACE IF NOT EXISTS sq22912")
spark.sql("DROP TABLE IF EXISTS sq22912.t")
# 3. Create Table with initial partition scheme
print("\n--- INITIAL STATE: Partition by Days ---")
spark.sql("""
CREATE TABLE sq22912.t (
    id BIGINT,
    data STRING,
    ts TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(ts))
""")
# Insert 1 (Snapshot 1)
spark.sql("INSERT INTO sq22912.t VALUES (1, 'v1_initial', CAST('2023-10-01 10:00:00' AS TIMESTAMP))")
# 4. Alter Partition: ADD
print("\n--- ALTER 1: Add 'data' to partition fields ---")
spark.sql("ALTER TABLE sq22912.t ADD PARTITION FIELD data")
# Insert 2 (Snapshot 2 - Partitioned by days(ts) AND data)
spark.sql("INSERT INTO sq22912.t VALUES (2, 'v2_add', CAST('2023-10-02 12:00:00' AS TIMESTAMP))")
# 5. Alter Partition: REPLACE
print("\n--- ALTER 2: Replace days(ts) with hours(ts) ---")
spark.sql("ALTER TABLE sq22912.t REPLACE PARTITION FIELD days(ts) WITH hours(ts)")
# Insert 3 (Snapshot 3 - Partitioned by hours(ts) AND data)
spark.sql("INSERT INTO sq22912.t VALUES (3, 'v3_replace', CAST('2023-10-03 14:30:00' AS TIMESTAMP))")
# 6. Print exact timestamps for SQream Time Travel
print("\n--- EXACT TIMESTAMPS FOR SQREAM TIME TRAVEL ---")
spark.sql("""
    SELECT 
        snapshot_id,
        operation,
        date_format(committed_at, 'yyyy-MM-dd HH:mm:ss.SSS') as exact_timestamp
    FROM sq22912.t.snapshots
    ORDER BY committed_at ASC
""").show(truncate=False)
spark.stop()