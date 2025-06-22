import ibis
from ibis.backends import sqream , postgres
import pandas as pd
# import sqClient
from ibis import examples, util
import ibis.backends
import ibis.backends.postgres
import ibis.expr.datatypes as dt


_backend = ibis.connect("sqream://sqream:sqream@192.168.4.60:5000/master")


# _backend = ibis.postgres.connect(
#    host="192.168.1.12",
#    port=5432,
#    user="postgres",
#    password="pgsql"
# )


def read_table(name):
    table = _backend.table(name)
    return PandasLikeFrame(table)


class PandasLikeFrame:
    def __init__(self, expr):

        self._expr = expr

    def __getitem__(self, key):

        # Filtering
        if isinstance(key, ibis.expr.types.BooleanColumn):
            return PandasLikeFrame(self._expr.filter(key))
        # Single column
        elif isinstance(key, str):
            return self._expr[key]
        # Column selection
        elif isinstance(key, list):
            return PandasLikeFrame(self._expr[[*key]])
        else:
            raise ValueError("Unsupported key type")

    def groupby(self, by):
        return PandasLikeGroupBy(self._expr, by)

    def execute(self, debug=False):
        if isinstance(self._expr, list):
            results = [expr.execute() for expr in self._expr]
            # Assuming all expressions in the list result in PandasLikeSeries
            # and they have the same length (representing columns of the same DataFrame)
            # We need a way to combine these Series into a PandasLikeFrame.
            # The exact method depends on your PandasLikeFrame implementation.
            # Here's a placeholder assuming a constructor that takes a list of Series.
            return results
        else:
            return self._expr.execute()
    def columns(self):
        return self._expr.schema().names
        
    def isnull(self):
        columns = self._expr.schema().names
        isnull_exprs = [self._expr[col].isnull().name(col) for col in columns]
        return PandasLikeFrame(isnull_exprs)

    def notnull(self, column):
        if isinstance(column, str):
            return self._expr[column].notnull()
        else:
            raise ValueError("Column name must be a string")

    def quantile(self, q, axis=0, numeric_only=True, interpolation='linear'):
        if axis != 0:
            raise ValueError("Axis must be 0")
        if not numeric_only:
            raise ValueError("numeric_only must be True")
        if isinstance(q, float):
            columns = self._expr.schema().names
            quantile_exprs = [self._expr[col].quantile(q).name(f"{col}_quantile_{q}") for col in columns]
            executed_quantiles = self._backend.execute(ibis.union_all(*quantile_exprs))
            return pd.Series(executed_quantiles.iloc[0], index=[f"{col}_quantile_{q}" for col in columns])
        elif isinstance(q, list):
            results = {}
            for quantile_val in q:
                columns = self._expr.schema().names
                quantile_exprs = [self._expr[col].quantile(quantile_val).name(f"{col}_quantile_{quantile_val}") for col in columns]
                executed_quantiles = self._backend.execute(ibis.union_all(*quantile_exprs))
                results[quantile_val] = pd.Series(executed_quantiles.iloc[0], index=[f"{col}_quantile_{quantile_val}" for col in columns])
            return pd.DataFrame(results).T
        else:
            raise ValueError("q must be a float or a list of floats")

    def median(self, axis=0, numeric_only=True):
        return self.quantile(0.5, axis=axis, numeric_only=numeric_only)
    
    def drop(self,column, axis=0):
        if isinstance(column, str):
            return self._expr[column].drop(column).execute()
        else:
            raise ValueError("Column name must be a string")
    
    def quantile(self, q, column):
        if isinstance(column, str):
            return self._expr[column].quantile(q)
        else:
            raise ValueError("Column name must be a string")

    def median(self, column):
        if isinstance(column, str):
            return self._expr[column].median()
        else:
            raise ValueError("Column name must be a string")
        
    def corr(self, method='pearson', min_periods=None):
            numeric_cols = [col for col, dtype in self._expr.schema().items() if dtype.is_numeric()]
            if not numeric_cols:
                return pd.DataFrame()

            corr_exprs = []
            for i in range(len(numeric_cols)):
                for j in range(i, len(numeric_cols)):
                    col1 = self._expr[numeric_cols[i]]
                    col2 = self._expr[numeric_cols[j]]
                    corr_expr = ibis.correlation(col1, col2).name(f"corr({numeric_cols[i]}, {numeric_cols[j]})")
                    corr_exprs.append(corr_expr)

            if not corr_exprs:
                return pd.DataFrame(index=numeric_cols, columns=numeric_cols).fillna(1.0)

            executed_correlations = self._backend.execute(ibis.union_all(*corr_exprs))

            corr_df = pd.DataFrame(index=numeric_cols, columns=numeric_cols)
            for row in executed_correlations.itertuples(index=False):
                col_names = row[0].split('(')[1].split(')')[0].split(', ')
                corr_value = row[1]
                corr_df.loc[col_names[0], col_names[1]] = corr_value
                corr_df.loc[col_names[1], col_names[0]] = corr_value

            # Fill diagonal with 1.0 (correlation of a column with itself)
            for col in numeric_cols:
                corr_df.loc[col, col] = 1.0

            return corr_df
    
    def head(self, n=5):
        """
        Returns the first n rows of the DataFrame.

        Args:
            n (int): Number of rows to return. Default is 5.
        """
        return self._expr.limit(n).execute()
    
    def rows(self):
        return self._expr.count()
    
    def isnullandsum(self):
        total_rows = self._expr.count()
        columns = self._expr.schema().names
        aggregations  = {}

        for col in columns:
            aggregations[col] = total_rows - self._expr[col].count()

        # Create a new Ibis expression for the aggregation
        aggregated_expr = self._expr.aggregate(**aggregations).limit(1)

        # Execute the aggregation and return as a PandasLikeFrame
        return PandasLikeFrame(aggregated_expr)
    
    # def drop(self, columns_to_drop: list[str]):
    #     """Removes specified columns from the Ibis table expression.

    #     Args:
    #         columns_to_drop: A list of column names to remove.

    #     Returns:
    #         A new PandasLikeFrame instance with the specified columns dropped.
    #     """
    #     existing_columns = self._expr.columns
    #     columns_to_keep = [col for col in existing_columns if col not in columns_to_drop]
    #     self._expr = self._expr.select(columns_to_keep)
    
    def drop_table_column(self, column):
        table_name = self._expr.get_name()
        if not table_name:
            raise ValueError("Underlying Ibis expression does not have a name (not a table)")

        if isinstance(column, str):
            columns_to_drop = [column]
        elif isinstance(column, list):
            columns_to_drop = column
        else:
            raise ValueError("column must be a string or a list of strings")
        # self = self.drop(columns_to_drop)
        with _backend.con.cursor() as cursor:
            for col_to_drop in columns_to_drop:
                try:
                    drop_statement = f"ALTER TABLE {table_name} DROP COLUMN {col_to_drop}"
                    cursor.execute(drop_statement)
                    _backend.con.commit()
                except Exception as e:
                    _backend.con.rollback()
                    print(f"Error dropping column '{col_to_drop}' from table '{table_name}': {e}")
        self._expr = read_table(table_name)._expr

    def sqream_python_module(self, func, new_table = ""):
        table_name = self._expr.get_name()

        columns = self.columns()

        if not isinstance(func, str):
            raise ValueError("Underlying Ibis expression only supports string functions names")

        select_clause = ", ".join(columns)
        
        with _backend.con.cursor() as cursor:
            try:
                if new_table == "":
                    statement = f"create or replace  TABLE {table_name}_tempxx43 as select {select_clause},semi_funcs.{func}() from {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    statement = f"drop table {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    statement = f"ALTER TABLE {table_name}_tempxx43 rename to {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    self._expr = read_table(table_name)._expr
                    self.drop_table_column([func])
                else:
                    statement = f"create or replace  TABLE {new_table} as select {select_clause},semi_funcs.{func}() from {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    new_t = read_table(new_table)
                    new_t.drop_table_column([func])
            except Exception as e:
                _backend.con.rollback()
                print(f"Error with place_holder column '{statement}' from table '{table_name}': {e}")
        return self
    #check if this is pandas function if not move 
    def replace_outliers_with_median(self, column_name, lower_bound, upper_bound):
        if not isinstance(column_name, str):
            raise ValueError("column_name must be a string")

        col = self._expr[column_name]
        median_val = col.median()

        # Use ibis.cases() with (condition, result) tuples
        replaced_col = ibis.cases(
            (col > upper_bound, median_val),
            (col < lower_bound, median_val),
            else_=col
        ).name(column_name)

        # Create a new Ibis table expression with the replaced column
        cols_to_select = [c for c in self.columns() if c != column_name] + [replaced_col]
        new_expr = self._expr.select(*cols_to_select)

        return PandasLikeFrame(new_expr)
    #check if this is pandas function if not move 
    def update_outliers_with_median(self, column_names, threshold=1.5):
        """
        Updates outliers in specified columns with the median value using the IQR method, using a single UPDATE statement.

        Args:
            column_names (str or list of str): The name(s) of the column(s) to update.
            threshold (float, optional): The IQR multiplier. Defaults to 1.5.
        """
        if isinstance(column_names, str):
            column_names = [column_names]

        if not all(isinstance(col, str) for col in column_names):
            raise ValueError("column_names must be a string or a list of strings")

        table_name = self._expr.get_name()
        if not table_name:
            raise ValueError(
                "Cannot update a temporary or unnamed table. The Ibis expression must be a named table.")

        with _backend.con.cursor() as cursor:
            # Calculate all quantiles and medians at once for all columns
            quantile_exprs = {}
            for col_name in column_names:
                col = self._expr[col_name]
                quantile_exprs[f"{col_name}_q1"] = col.quantile(0.25)
                quantile_exprs[f"{col_name}_q3"] = col.quantile(0.75)
                quantile_exprs[f"{col_name}_median"] = col.median()

            # Execute the quantile calculations
            quantiles = self._expr.aggregate(**quantile_exprs).execute()

            # Construct a single UPDATE statement
            update_statements = []
            for col_name in column_names:
                q1 = quantiles[f"{col_name}_q1"][0]
                q3 = quantiles[f"{col_name}_q3"][0]
                median_val = quantiles[f"{col_name}_median"][0]
                iqr = q3 - q1
                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr

                update_statements.append(
                    f"{col_name} = CASE "
                    f"WHEN {col_name} < {lower_bound} OR {col_name} > {upper_bound} THEN {median_val} "
                    f"ELSE {col_name} END"
                )
            if update_statements:
                set_clause = ", ".join(update_statements)
                update_statement = f"UPDATE {table_name} SET {set_clause}"
                cursor.execute(update_statement)
                _backend.con.commit()

        self._expr = read_table(table_name)._expr
        return self
    
def execute_from_file(file_path):
    """
    Reads a SQL query from the specified file and executes it against the SQream database.

    Args:
        file_path (str): The path to the file containing the SQL query.

    Returns:
        pandas.DataFrame: The result of the executed query as a Pandas DataFrame.
    """
    try:
        with open(file_path, 'r') as f:
            sql_query = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error reading file '{file_path}': {e}")

    if not sql_query:
        raise ValueError("The SQL query file is empty.")

    try:
        with _backend.con.cursor() as cursor:
            cursor.execute(sql_query)
            _backend.con.commit()

    except Exception as e:
        _backend.con.rollback()
        raise RuntimeError(f"Error executing SQL query: {e}\nQuery: {sql_query}")

def read_csv_to_sqream(table_name, file_path):
    """
    Reads a SQL query from the specified file and executes it against the SQream database.

    Args:
        file_path (str): The path to the file containing the SQL query.

    Returns:
        pandas.DataFrame: The result of the executed query as a Pandas DataFrame.
    """

    sql_query = f"copy {table_name} from wrapper csv_fdw options (location = '{file_path}');"
    try:
        with _backend.con.cursor() as cursor:
            cursor.execute(sql_query)
            _backend.con.commit()

    except Exception as e:
        _backend.con.rollback()
        raise RuntimeError(f"Error executing SQL query: {e}\nQuery: {sql_query}")

#likely dont need      
class PandasLikeGroupBy:
    def __init__(self, expr, by):
        self._expr = expr
        self._by = [by] if isinstance(by, str) else by

    def aggregate(self, **aggregations):
        agg_exprs = {
            key: getattr(self._expr[col], agg_func)()
            for key, (col, agg_func) in aggregations.items()
        }
        grouped = self._expr.group_by(self._by).aggregate(**agg_exprs)
        return PandasLikeFrame(grouped)

    def agg(self, **kwargs):
        return self.aggregate(**kwargs)
    
    def quantile(self, q, column):
        if isinstance(column, str):
            return self._expr[column].quantile(q).name(f"{column}_quantile_{q}")
        else:
            raise ValueError("Column name must be a string")

    def median(self, column):
        if isinstance(column, str):
            return self._expr[column].median().name(f"{column}_median")
        else:
            raise ValueError("Column name must be a string")

    def execute(self):
        # Execute the grouped and aggregated expression
        return self._expr.execute()


execute_from_file("/home/johnny/git/sj/sj_test_ibis/create_table.sql")
read_csv_to_sqream("semi_cond2","/home/johnny/git/sj/sj_test_ibis/secom_combined.csv")
data = {'col1': [1, 2, 3, 4, 5],
        'col2': [5, 4, 3, 2, 1],
        'col3': [1, 3, 5, 7, 9]}
df2 = pd.DataFrame(data)
print(df2)
df_original = read_table("semi_cond2")
df_original = df_original.isnullandsum().head()
print(df_original)
df_original.drop_table_column(["t"])
total_rows = df_original.rows().execute()
cols_to_drop = []
for col in df_original.columns():
    first_element = df_original[col][0]
    if first_element / total_rows > 0.9:
        cols_to_drop.append(col)
df_original.drop_table_column(cols_to_drop)
print(df_original.head(10))