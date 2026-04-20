from pyspark.sql import SparkSession

def get_session(ip: str = "http://192.168.0.103", **kwargs):
    defaults = {
        "warehouse": "s3://warehouse",
        "id": "admin",
        "password": "password",
        "region": "us-east-1"
    }
    config = {**defaults, **kwargs}

    if not ip.startswith("http://"):
        ip = f"http://192.168.{ip}" if ip.count('.') == 1 else f"http://{ip}"

    return SparkSession.builder\
        .appName("IcebergParquetApp")\
        .config("spark.jars.packages", (
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0,"
            "org.apache.iceberg:iceberg-aws-bundle:1.7.0"))\
        .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")\
        .config("spark.sql.catalog.my_catalog",
            "org.apache.iceberg.spark.SparkCatalog")\
        .config("spark.sql.catalog.my_catalog.type", "rest")\
        .config("spark.sql.catalog.my_catalog.uri", f"{ip}:8181")\
        .config("spark.sql.catalog.my_catalog.warehouse", config["warehouse"])\
        .config("spark.sql.defaultCatalog", "my_catalog")\
        .config("spark.sql.catalog.my_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")\
        .config("spark.sql.catalog.my_catalog.s3.endpoint", f"{ip}:9000")\
        .config("spark.sql.catalog.my_catalog.s3.path-style-access", "true")\
        .config("spark.sql.catalog.my_catalog.s3.access-key-id", config["id"])\
        .config("spark.sql.catalog.my_catalog.s3.secret-access-key", config["password"])\
        .config("spark.sql.catalog.my_catalog.client.region", config["region"])\
        .getOrCreate()

#fdb.sql('show namespaces[ in <namespace>]).show()

# fdb.sql("CREATE NAMESPACE IF NOT EXISTS sj")
# data = [(1, "2024-01-01 10:00:00", "hello"), (2, "2024-01-01 11:00:00", "world")]
# df = fdb.createDataFrame(data, ["id", "timestamp", "str"])
# df.writeTo("sj.t1").createOrReplace()
# fdb.sql("SELECT * FROM sj.t1").show()
# fdb.sql("ALTER TABLE sj.t1 DROP COLUMN timestamp")
# fdb.sql("ALTER TABLE sj.t1 ADD COLUMN timestamp timestamp after id")
# fdb.sql("INSERT INTO sj.t1 VALUES (3, CAST('2024-01-01 12:00:00' AS TIMESTAMP), 'bla')")
# fdb.sql("SELECT * FROM sj.t1").show()

# promote iceberg table column from int to long:
# fdb.sql("ALTER TABLE sj.t1 ALTER COLUMN id TYPE bigint")