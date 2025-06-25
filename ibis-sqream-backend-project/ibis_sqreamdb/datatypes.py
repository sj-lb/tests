# ibis_sqreamdb/datatypes.py
from __future__ import annotations
import ibis.expr.datatypes as dt
from ibis.backends.sql.datatypes import PostgresType

class SqreamType(PostgresType):
    @classmethod
    def to_string(cls, dtype: dt.DataType) -> str:
        if isinstance(dtype, dt.String):
            # Return a type with a size that SQreamDB accepts
            return "TEXT" 
        # For all other types, use the default behavior
        return super().to_string(dtype)
