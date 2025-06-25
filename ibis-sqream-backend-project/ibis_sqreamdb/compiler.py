# ibis_sqreamdb/compiler.py

import ibis.expr.operations as ops
from ibis.backends.sql.compilers.postgres import PostgresCompiler
#from ibis.backends.sql.dialects.postgres import PyDialect

import sqlglot.expressions as sge


# It is cleaner to define a simple dialect for SQREAM rather than inheriting
# all the specifics from the Postgres compiler.
#class SqreamDialect(PyDialect):
#    """A class to represent the SQREAM dialect for sqlglot."""
#    pass

class SqreamCompiler(PostgresCompiler):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",PostgresCompiler)
    """
    The Ibis compiler for the SQREAM backend.

    This class translates Ibis expressions into SQL by implementing
    special "visitor" methods for operations that SQREAM handles
    uniquely.
    """

    # Tell the compiler which SQL dialect to use for generating strings.
    #dialect = SqreamDialect

    def visit_Aggregate(self, op: ops.Aggregate, *, table, groups, metrics):
        print("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")
        """
        This is the special visitor function that Ibis calls when it sees an
        Aggregate operation in the expression tree. This is the key to fixing
        the .group_by().aggregate() issue.

        Args:
            op: The Ibis Aggregate operation node.
            table: The compiled sqlglot expression for the source table.
            groups: A list of compiled sqlglot expressions for the grouping keys.
            metrics: A list of compiled sqlglot expressions for the aggregate metrics.

        Returns:
            A sqlglot SELECT statement with the correct GROUP BY clause.
        """
        # The columns in our SELECT statement will be the grouping keys plus
        # the aggregate function calls.
        selects = groups + metrics

        # Start building the sqlglot SELECT statement from the table.
        query = sge.select(*selects).from_(table)

        # If the 'groups' list is not empty, it means we have a GROUP BY.
        # The base compiler prepares this 'groups' list for us from the
        # Ibis expression's `.groups` attribute.
        if groups:
            # Add the GROUP BY clause to our sqlglot query object.
            query = query.group_by(*groups)

        # IMPORTANT: Return the fully formed sqlglot query object, NOT None.
        return query


