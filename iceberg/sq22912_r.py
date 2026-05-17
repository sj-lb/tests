from sj.utils.pyspark import get_session
from time import sleep

# 1. Initialize SparkSession 
spark = get_session('0.103')

# 2. Setup Namespace and ensure clean table
spark.sql("CREATE NAMESPACE IF NOT EXISTS sq22912")
spark.sql("DROP TABLE IF EXISTS sq22912.t")

# 3. Create Table with a diverse initial partition scheme
# Using: identity, bucket, truncate, and time-based transforms
print("\n--- INITIAL STATE: Comprehensive Partitioning ---")
spark.sql("""
CREATE TABLE sq22912.t (
    id BIGINT,
    category STRING,
    user_id INT,
    event_date DATE,
    ts TIMESTAMP
)
USING iceberg
PARTITIONED BY (
    days(event_date),      -- Date transform
    bucket(16, user_id),   -- Hash-based transform
    truncate(4, category), -- Prefix-based transform
    id                     -- Identity transform
)
""")

# Insert 1 (Snapshot 1)
spark.sql("""
INSERT INTO sq22912.t VALUES 
(1, 'analytics', 101, CAST('2023-10-01' AS DATE), CAST('2023-10-01 10:00:00' AS TIMESTAMP))
""")

# 4. Alter Partition: ADD (Years, Months)
print("\n--- ALTER 1: Adding Year and Month transforms ---")
# Iceberg allows multiple transforms on the same column or different ones
spark.sql("ALTER TABLE sq22912.t ADD PARTITION FIELD years(ts)")
spark.sql("ALTER TABLE sq22912.t ADD PARTITION FIELD months(event_date)")

# Insert 2 (Snapshot 2)
spark.sql("""
INSERT INTO sq22912.t VALUES 
(2, 'billing', 202, CAST('2023-11-01' AS DATE), CAST('2023-11-01 12:00:00' AS TIMESTAMP))
""")

# 5. Alter Partition: REPLACE (Days to Hours)
print("\n--- ALTER 2: Replace days(event_date) with hours(ts) ---")
# Note: You can replace existing partition fields to evolve the layout
spark.sql("ALTER TABLE sq22912.t REPLACE PARTITION FIELD days(event_date) WITH hours(ts)")

# Insert 3 (Snapshot 3)
spark.sql("""
INSERT INTO sq22912.t VALUES 
(3, 'security', 303, CAST('2023-12-01' AS DATE), CAST('2023-12-01 14:30:00' AS TIMESTAMP))
""")

# 6. Print snapshot history for Time Travel
print("\n--- EXACT TIMESTAMPS FOR SQREAM TIME TRAVEL ---")
spark.sql("""
    SELECT 
        snapshot_id,
        operation,
        date_format(committed_at, 'yyyy-MM-dd HH:mm:ss.SSS') as exact_timestamp
    FROM sq22912.t.snapshots
    ORDER BY committed_at ASC
""").show(truncate=False)

# 7. Verify Partitioning Layout
print("\n--- CURRENT PARTITION SPEC ---")
spark.sql("DESCRIBE TABLE sq22912.t").show(truncate=False)

spark.stop()