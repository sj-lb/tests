# SJ Utilities Package

A collection of utility modules for data processing and Spark operations.

## Installation

From the utils directory:

```bash
cd utils
pip install -e .
```

Or install from git:

```bash
pip install -e git+https://github.com/yourname/sj.git#subdirectory=utils
```

## Usage

```python
from sj.utils.pyspark import get_session
from sj.utils.avro_to_json import convert

# Get a configured Spark session
spark = get_session()

# Convert Avro files to JSON
convert("data.avro")
```

## Modules

- `sj.utils.pyspark`: Spark session utilities with Iceberg/S3 configuration
- `sj.utils.avro_to_json`: Convert Avro files to JSON format
