from pyspark.sql import SparkSession

spark = SparkSession.builder\
    .appName("IcebergParquetApp")\
    .config("spark.jars.packages", (
        "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0,"
        "org.apache.iceberg:iceberg-aws-bundle:1.7.0"))\
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")\
    .config("spark.sql.catalog.my_catalog",
            "org.apache.iceberg.spark.SparkCatalog")\
    .config("spark.sql.catalog.my_catalog.type", "rest")\
    .config("spark.sql.catalog.my_catalog.uri", "http://192.168.5.82:8181")\
    .config("spark.sql.catalog.my_catalog.warehouse", "s3://warehouse")\
    .config("spark.sql.defaultCatalog", "my_catalog")\
    .config("spark.sql.catalog.my_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")\
    .config("spark.sql.catalog.my_catalog.s3.endpoint", "http://192.168.5.82:9000")\
    .config("spark.sql.catalog.my_catalog.s3.path-style-access", "true")\
    .config("spark.sql.catalog.my_catalog.s3.access-key-id", "admin")\
    .config("spark.sql.catalog.my_catalog.s3.secret-access-key", "password")\
    .config("spark.sql.catalog.my_catalog.client.region", "us-east-1")\
    .getOrCreate()

prq_data = spark.read.parquet("/path/to/data.parquet")
prq_data.writeTo("my_catalog.my_namespace.my_table").append()