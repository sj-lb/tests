from sqlglot import exp
from sqlglot.dialects.dialect import Dialect
from ibis.expr import types as ir
from sqlglot.parser import Parser
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
        NULL_ORDERING_SUPPORTED = False
        
        TRANSFORMS = {
            exp.Array: lambda self, e: f"ARRAY[{self.expressions(e)}]",
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

        def datatype_sql(self, expression: exp.DataType) -> str:
            if expression.is_type(exp.DataType.Type.ARRAY):
                if expression.expressions:
                    values = self.expressions(expression, key="values", flat=True)
                    return f"{self.expressions(expression, flat=True)}[{values}]"
                return 'ARRAY'
            return super().datatype_sql(expression)
        def ordered_sql(self, expression: exp.Ordered) -> str:
            desc = expression.args.get("desc")

            this = self.sql(expression, "this")

            sort_order = " DESC" if desc else (" ASC" if desc is False else "")

            with_fill = self.sql(expression, "with_fill")
            with_fill = f" {with_fill}" if with_fill else ""

            return f"{this}{sort_order}{with_fill}"

    class Parser(Parser):
        FUNCTIONS = {
            **Parser.FUNCTIONS,
            "CHARINDEX": lambda substr, arg: exp.func('CHARINDEX', substr, arg, dialect=SQreamDialect)
        }