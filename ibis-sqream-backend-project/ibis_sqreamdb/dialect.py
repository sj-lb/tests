from sqlglot import exp
from sqlglot.dialects.dialect import Dialect
from sqlglot.generator import Generator
from sqlglot.tokens import Tokenizer, TokenType


class SQreamDialect(Dialect):
    class Tokenizer(Tokenizer):
        # QUOTES = ["'", '"']  # Strings can be delimited by either single or double quotes
        IDENTIFIERS = ['"']  # Identifiers can be delimited by backticks

        # Associates certain meaningful words with tokens that capture their intent
        KEYWORDS = {
            **Tokenizer.KEYWORDS,
            "INT64": TokenType.BIGINT,
            "FLOAT64": TokenType.DOUBLE,
        }

    class Generator(Generator):
        # Specifies how AST nodes, i.e. subclasses of exp.Expression, should be converted into SQL
        TRANSFORMS = {
            exp.Array: lambda self, e: f"[{self.expressions(e)}]",
        }

        # Specifies how AST nodes representing data types should be converted into SQL
        TYPE_MAPPING = {
            exp.DataType.Type.BOOLEAN: "BOOL",
            exp.DataType.Type.CHAR: "TEXT",
            exp.DataType.Type.NCHAR: "TEXT",
            exp.DataType.Type.VARCHAR: "TEXT",
            exp.DataType.Type.TINYTEXT: "TEXT",
            exp.DataType.Type.FLOAT: "REAL",
            exp.DataType.Type.DECIMAL: "NUMERIC",
        }