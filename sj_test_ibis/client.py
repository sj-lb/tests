import ibis
from ibis.backends import sqream , postgres
import pandas as pd
# import sqClient
from ibis import examples, util
import ibis.backends
import ibis.backends.postgres
import ibis.expr.datatypes as dt


_backend = ibis.connect("sqream://sqream:sqream@192.168.4.68:5000/master")


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
                    statement = f"create or replace  TABLE {table_name}_tempxx as select {select_clause},semi_funcs.{func}() from {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    statement = f"drop table {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                    statement = f"ALTER TABLE {table_name}_tempxx rename to {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
                else:
                    statement = f"create or replace  TABLE {new_table} as select {select_clause},semi_funcs.{func}() from {table_name}"
                    cursor.execute(statement)
                    _backend.con.commit()
            except Exception as e:
                _backend.con.rollback()
                print(f"Error with place_holder column '{statement}' from table '{table_name}': {e}")
        self._expr = read_table(table_name)._expr
        self.drop_table_column([func])
        return self

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
    
    def replace_outliers_with_median(self, column_name, lower_bound, upper_bound):
        if not isinstance(column_name, str):
            raise ValueError("column_name must be a string")

        col = self._expr[column_name]
        median_val = col.median()

        replaced_col = ibis.cases(
            (col > upper_bound, median_val),
            (col < lower_bound, median_val),
            else_=col
        ).name(column_name)

        cols_to_select = [c for c in self.columns() if c != column_name] + [replaced_col]
        new_expr = self._expr.select(*cols_to_select)
        compiled_sql = ibis.to_sql(new_expr)
        print("Ibis Expression (Compiled SQL):\n", compiled_sql)

        return PandasLikeFrame(new_expr)
    #good but slow!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # def update_outliers_with_median(self, column_names, threshold=1.5):
    #     """
    #     Updates outliers in specified columns with the median value using the IQR method.
    #     This function generates and executes an UPDATE statement.

    #     Args:
    #         column_names (str or list of str): The name(s) of the column(s) to update.
    #         threshold (float, optional): The IQR multiplier. Defaults to 1.5.
    #     """
    #     if isinstance(column_names, str):
    #         column_names = [column_names]

    #     if not all(isinstance(col, str) for col in column_names):
    #         raise ValueError("column_names must be a string or a list of strings")

    #     table_name = self._expr.get_name()  # Get the table name
    #     if not table_name:
    #         raise ValueError("Cannot update a temporary or unnamed table.  The Ibis expression must be a named table.")

    #     with _backend.con.cursor() as cursor:
    #         for col_name in column_names:
    #             col = self._expr[col_name]
    #             q1 = col.quantile(0.25).execute()  # Execute to get scalar value
    #             q3 = col.quantile(0.75).execute()  # Execute to get scalar value
    #             iqr = q3 - q1
    #             median_val = col.median().execute()  # Execute to get scalar value

    #             lower_bound = q1 - threshold * iqr
    #             upper_bound = q3 + threshold * iqr

    #             # Construct the UPDATE statement.  Crucially, use string formatting
    #             # to insert the *values* of lower_bound, upper_bound, and median_val.
    #             update_statement = f"""
    #                 UPDATE {table_name}
    #                 SET {col_name} = {median_val}
    #                 WHERE {col_name} < {lower_bound} OR {col_name} > {upper_bound}
    #             """
    #             print(f"Executing: {update_statement}")  # Very important for debugging
    #             cursor.execute(update_statement)
    #         _backend.con.commit()  # Commit the changes after all updates

    #     # To reflect the changes in the PandasLikeFrame's internal expression,
    #     # you might need to re-read the table.  This depends on your use case.
    #     self._expr = read_table(table_name)._expr #refresh the table.
    #     return self #important to return self      
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
                print(f"Executing: {update_statement}")
                cursor.execute(update_statement)
                _backend.con.commit()

        self._expr = read_table(table_name)._expr
        return self
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




def test_join():
    table1 = read_table('int_float_str')
    table2 = read_table('int_float_str')  # Using the same table for simplicity

    # Perform an inner join on the 'id' column
    merged_table = table1.groupby('id').aggregate(sum_int=('id', 'sum'))._expr.inner_join(
        table2._expr, table1._expr.id == table2._expr.id
    )
    joined_df = PandasLikeFrame(merged_table).execute()

    # Basic assertion to check if the join produced a DataFrame
    assert isinstance(joined_df, pd.DataFrame)
    assert 'id' in joined_df.columns

    print("test_join passed")
    print(joined_df.head())

def test_nested_join():
    table1 = read_table('int_float_str')
    table2 = read_table('int_float_str')
    table3 = read_table('int_float_str') # Using a third instance

    merged_inner_expr = table1.groupby('id').aggregate(sum_int=('id', 'sum'))._expr.inner_join(
        table2._expr, table1._expr.id == table2._expr.id
    )
    merged_inner_pl = PandasLikeFrame(merged_inner_expr)


    # Print the schema of the intermediate result to see the column names
    print("Schema of merged_inner_pl._expr:")
    print(merged_inner_pl._expr.schema())
    print("Schema of table3.._expr:")
    print(table3._expr.schema())

    # To avoid ambiguity, explicitly refer to the 'id' from the first joined result
    # Assuming Ibis might add a suffix like '_x' or '_left' to the 'id' from the left table.
    # Let's try accessing it directly. If name collisions are handled with suffixes,
    # you might need to adjust the column name accordingly.
    nested_merged = merged_inner_pl.groupby('id').aggregate(sum_int=('id', 'sum'))._expr.inner_join(
        table3._expr, merged_inner_pl._expr['id'] == table3._expr['id']
    )
    nested_joined_df = PandasLikeFrame(nested_merged).execute()

    # Basic assertions to check the nested join
    assert isinstance(nested_joined_df, pd.DataFrame)
    assert 'id' in nested_joined_df.columns
    assert 'sum_int' in nested_joined_df.columns

    print("test_nested_join passed")
    print(nested_joined_df.head())


import time
import pandas as pd

def bench_ibis():
    """
    Wraps the original (assumed non-Pandas/cuDF) code and its Pandas
    implementation in timed blocks.

    Note: This function assumes the existence of placeholder functions
    like 'read_table', 'isnullandsum', 'execute', 'columns', and
    'drop_table_column' for the original logic. You'll need to
    replace these with actual implementations if you want to run
    the original code. This function also omits the cuDF implementation
    as requested.
    """
    print("Benchmarking Ibis-like logic and Pandas...")
    print("-" * 40)

    # Original logic with timers
    start_time_original = time.time()
    try:


        df_original = read_table("semi_test3")
        df2_original = df_original.isnullandsum().execute()
        
        print("\nOriginal:")
        print(df2_original)
        total_rows = df_original.rows().execute()
        cols_to_drop = []
        for col in df_original.columns():
            first_element = df2_original[col][0]
            if first_element/total_rows > 0.9:
                cols_to_drop.append(col)
        df_original.drop_table_column(cols_to_drop)
        print("done (original)")

        df_original.knn_place_holder()

    except NameError as e:
        print(f"Error in original code placeholder: {e}. Ensure the necessary library is imported and functions exist.")
    except Exception as e:
        print(f"An error occurred in the original code placeholder: {e}")

    end_time_original = time.time()
    elapsed_time_original = end_time_original - start_time_original
    print(f"Elapsed time (original placeholder): {elapsed_time_original:.4f} seconds\n")


data = {'col1': [1, 2, 3, 4, 5],
        'col2': [5, 4, 3, 2, 1],
        'col3': [1, 3, 5, 7, 9]}

df2 = pd.DataFrame(data)
df2

df_original = read_table("semi_cond2")
print(df_original.execute())

# df_original.drop_table_column(["t"])

# df2_original = df_original.isnullandsum().execute()
# df2_original.head()

# total_rows = df_original.rows().execute()
# cols_to_drop = []
# for col in df_original.columns():
#     first_element = df2_original[col][0]
#     if first_element/total_rows > 0.9:
#         cols_to_drop.append(col)
# df_original.drop_table_column(cols_to_drop)
# df_original.execute().head()

# df_feature = df_original.sqream_python_module("knn")
# df_feature.execute().head()

df_feature = df_original
def replace_outliers_with_median_without_case(df, column_name, lower_bound, upper_bound):
        if not isinstance(column_name, str):
            raise ValueError("column_name must be a string")

        col = df._expr[column_name]
        median_val = col.median()

        # Create boolean masks for values outside the bounds
        upper_outlier = col > upper_bound
        lower_outlier = col < lower_bound

        # Use ibis.where to conditionally replace values
        replaced_col = ibis.ifelse(upper_outlier | lower_outlier, median_val, col).name(column_name)

        # Create a new Ibis table expression with the replaced column
        cols_to_select = [c for c in df.columns() if c != column_name] + [replaced_col]
        new_expr = df._expr.select(*cols_to_select)

        return PandasLikeFrame(new_expr)


# def outliers(df: PandasLikeFrame):
#     features = df.columns()[:-1]
#     for j in features:
#         Q1 = df.quantile(q=0.25, column=j).execute()
#         Q3 = df.quantile(q=0.75, column=j).execute()
#         IQR = Q3 - Q1
#         upper_bound = Q3 + 1.5 * IQR
#         lower_bound = Q1 - 1.5 * IQR

#         col = df._expr[j]
#         median_val = df.median(column=j).exeute()

#         replaced_col = ibis.ifelse((col > upper_bound) | (col < lower_bound), median_val, col).name(j)
#         cols_to_select = [c for c in df.columns() if c != j] + [replaced_col]
#         new_expr = df._expr.select(*cols_to_select)
#         df = PandasLikeFrame(new_expr) # Update the df with the modified column
#     return df

# df_feature = outliers(df_feature)
# df_feature.execute().head()

def outliers_create_new_table(df: PandasLikeFrame, new_table_name: str):
    features = df.columns()[:-1]
    modified_exprs = []
    for j in features:
        Q1 = df.quantile(q=0.25, column=j)
        Q3 = df.quantile(q=0.75, column=j)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR
        lower_bound = Q1 - 1.5 * IQR
        median_val = df.median(column=j)

        col = df._expr[j]
        replaced_col = ibis.ifelse((col > upper_bound) | (col < lower_bound), median_val, col).name(j)
        modified_exprs.append(replaced_col)

    # Select all original columns, replacing the modified ones
    select_exprs = []
    original_cols = df.columns()[:-1]
    for col_name in original_cols:
        if col_name in features:
            # Find the replaced expression for this feature
            for expr in modified_exprs:
                if expr.get_name() == col_name:
                    select_exprs.append(expr)
                    break
        else:
            select_exprs.append(df._expr[col_name])

    create_table_expr = _backend.table(df._expr.get_name()).select(*select_exprs)
    
    # Compile the Ibis expression to SQL
    compiled_sql = ibis.to_sql(create_table_expr)
    print("Ibis Expression (Compiled SQL):\n", compiled_sql)

    # Execute the SQL using the cursor
    table_name = df._expr.get_name()
    with _backend.con.cursor() as cursor:
        try:
            execute_statement = f"CREATE OR REPLACE TABLE {new_table_name} AS {compiled_sql}"
            cursor.execute(execute_statement)
            _backend.con.commit()
            print(f"Table '{new_table_name}' created successfully.")
        except Exception as e:
            _backend.con.rollback()
            print(f"Error creating table '{new_table_name}': {e}")

    return read_table(new_table_name)

# # Example usage:
# new_table = outliers_create_new_table(df_feature, 'df_feature_cleaned')
# new_table.execute().head()

# def outliers_without_window_percentile_where(df: PandasLikeFrame, new_table_name: str):
#     table_node = _backend.table(df._expr.get_name())
#     original_cols = df.columns()[:-1]  # Exclude the label column

#     percentile_aggs = {}
#     for col_name in original_cols:
#         percentile_aggs[f"{col_name}_q1"] = (col_name, lambda x: x.quantile(0.25))
#         percentile_aggs[f"{col_name}_median"] = (col_name, lambda x: x.median())
#         percentile_aggs[f"{col_name}_q3"] = (col_name, lambda x: x.quantile(0.75))

#     percentiles_table = table_node.aggregate(**percentile_aggs)

#     modified_cols = []
#     for col_name in original_cols:
#         q1_expr = percentiles_table[f"{col_name}_q1"]
#         median_expr = percentiles_table[f"{col_name}_median"]
#         q3_expr = percentiles_table[f"{col_name}_q3"]
#         iqr_expr = q3_expr - q1_expr
#         upper_bound_expr = q3_expr + 1.5 * iqr_expr
#         lower_bound_expr = q1_expr - 1.5 * iqr_expr

#         is_outlier = (table_node[col_name] > upper_bound_expr) | (table_node[col_name] < lower_bound_expr)

#         modified_col = _backend.where(is_outlier, median_expr, table_node[col_name]).name(col_name)
#         modified_cols.append(modified_col)

#     select_exprs = [*modified_cols, table_node['passfail']]  # Include the label
#     create_table_expr = _backend.table(df._expr.get_name()).select(*select_exprs)

#     compiled_sql = _backend.to_sql(create_table_expr)
#     print("Ibis Expression (Compiled SQL):\n", compiled_sql)

#     with _backend.con.cursor() as cursor:
#         try:
#             execute_statement = f"CREATE OR REPLACE TABLE {new_table_name} AS {compiled_sql}"
#             cursor.execute(execute_statement)
#             _backend.con.commit()
#             print(f"Table '{new_table_name}' created successfully.")
#         except Exception as e:
#             _backend.con.rollback()
#             print(f"Error creating table '{new_table_name}': {e}")

#     return read_table(new_table_name)

# for col_name in df_feature.columns()[:-1]:
#     q1_expr = df_feature.quantile(q=0.25, column=col_name).execute()
#     median_expr = df_feature.median(column=col_name).execute()
#     q3_expr = df_feature.quantile(q=0.75, column=col_name).execute()
#     iqr_expr = q3_expr - q1_expr
#     upper_bound_expr = q3_expr + 1.5 * iqr_expr
#     lower_bound_expr = q1_expr - 1.5 * iqr_expr

# filtered_table = outliers_create_new_table(df_feature,"dude")
# filtered_table.execute().head()



# Example usage:

def remove_corr(df):

    df.sqream_python_module("find_corr","corr")

df_feature = remove_corr(df_feature)




# filtered_table = df_feature.update_outliers_with_median(df_feature.columns()[:-1])
# filtered_table.execute().head()


# if __name__ == "__main__":
#     bench_ibis()

    # df = read_table("orders")


    # print(df.isnullandsum().execute())
    # # Example of using notnull()
    # result_notnull = df[df.notnull("customer_id")].execute()
    # print("\nRows where customer_id is not null:")
    # print(result_notnull)

    # result = (
    #     df[df["amount"] > 100]
    #     .groupby("customer_id")
    #     .agg(total=("amount", "sum"))
    #     .execute()
    # )

    # print(result)

    # df = read_table("semi_test2")
    # df2 = df.isnullandsum().execute()

    # print(df2)
    # for col in df.columns():
    #   first_element = df2[col][0]
    #   print(first_element)
    #   if first_element > 700:
    #     df.drop_table_column(col)
    # print("done")
    # # print(df.replace('col576'))

    # # print(df.isnull().execute())
    # print(df.quantile(0.25,'col576').execute())
    # # print(df.corr().execute())
    # print("done")

    # test_join()
    # test_nested_join()




# Define the table schema
# schema = ibis.schema(
#     names=['id'],
#     types=[dt.int64]
# )

# Create the table expression
# table_name = 'etai'
# _backend.drop_table(table_name)
#table = _backend.create_table(table_name, schema)


# df = read_table("orders")


# # Example of using notnull()
# result_notnull = df[df.notnull("customer_id")].execute()
# print("\nRows where customer_id is not null:")
# print(result_notnull)

# result = (
#     df[df["amount"] > 100]
#     .groupby("customer_id")
#     .agg(total=("amount", "sum"))
#     .execute()
# )

# print(result)





# ibis_table = _backend.create_table("semi_test", obj=df)
# print(ibis_table)
# data = {'col1': [1, 2, 3, 4, 5],
#         'col2': [5, 4, 3, 2, 1],
#         'col3': [1, 3, 5, 7, 9]}
# df2 = pd.DataFrame(data)

# # Calculate the correlation matrix
# correlation_matrix = df2.corr()
# print(correlation_matrix)

# df = read_table("semi_test")
# # print(df.replace('col576'))

# # print(df.isnull().execute())
# print(df.quantile(0.25,'col576').execute())
# # print(df.corr().execute())
# print("done")



