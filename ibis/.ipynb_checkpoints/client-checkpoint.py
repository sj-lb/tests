# pandas_like.py
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

    def knn_place_holder(self ):
        table_name = self._expr.get_name()
        if not table_name:
            raise ValueError("Underlying Ibis expression does not have a name (not a table)")

        columns = self.columns()
        # if not isinstance(columns, list):
        #     raise ValueError("column must be a string or a list of strings")
        coalesce_expressions = []

        for col in columns:
            expression = f"COALESCE({col}, 1) AS {col}"
            coalesce_expressions.append(expression)

        select_clause = ", ".join(coalesce_expressions)

        with _backend.con.cursor() as cursor:
          

            try:
                statement = f"create or replace  TABLE {table_name}_tempxx as select {select_clause} from {table_name}"
                cursor.execute(statement)
                _backend.con.commit()
                statement = f"drop table {table_name}"
                cursor.execute(statement)
                _backend.con.commit()
                statement = f"ALTER TABLE {table_name}_tempxx rename to {table_name}"
                cursor.execute(statement)
                _backend.con.commit()
            except Exception as e:
                _backend.con.rollback()
                print(f"Error with place_holder column '{statement}' from table '{table_name}': {e}")
                    
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

    # # Pandas implementation with timers
    # start_time_pandas = time.time()
    # try:
    #     df_pandas = pd.read_csv("test_ibis/data/secom_data100k.csv", sep=',')  # Assuming space-separated, adjust as needed
    #     df2_pandas = pd.DataFrame(df_pandas.isnull().sum()).T

    #     print("\nPandas:")
    #     print(df2_pandas)
    #     for col in df_pandas.columns:
    #         if col in df2_pandas:
    #             first_element_pandas = df2_pandas[col].iloc[0]
    #             if first_element_pandas/len(df_pandas) > 0.9:
    #                 df_pandas.drop(columns=[col], inplace=True)
    #     print("done (pandas)")

    # except FileNotFoundError:
    #     print("Error: semi_test2 not found for pandas.")
    # except Exception as e:
    #     print(f"An error occurred in the pandas implementation: {e}")

    # end_time_pandas = time.time()
    # elapsed_time_pandas = end_time_pandas - start_time_pandas
    # print(f"Elapsed time (pandas): {elapsed_time_pandas:.4f} seconds")

    # # cuDF implementation with timers
    # try:
    #     import cudf
    #     start_time_cudf = time.time()
    #     try:
    #         df_cudf = cudf.read_csv("test_ibis/data/secom_data100k.csv", sep=',') # Assuming space-separated, adjust as needed
    #         df2_cudf = cudf.DataFrame(df_cudf.isnull().sum()).T

    #         print("\ncuDF:")
    #         print(df2_cudf)
    #         for col in df_cudf.columns:
    #             if col in df2_cudf.columns:
    #                 first_element_cudf = df2_cudf[col].iloc[0]
    #                 if first_element_cudf/len(df2_cudf) > 0.9:
    #                     df_cudf = df_cudf.drop(columns=[col])
    #         print("done (cuDF)")

    #     except FileNotFoundError:
    #         print("Error: semi_test2 not found for cuDF.")
    #     except Exception as e:
    #         print(f"An error occurred in the cuDF implementation: {e}")

    #     end_time_cudf = time.time()
    #     elapsed_time_cudf = end_time_cudf - start_time_cudf
    #     print(f"Elapsed time (cuDF): {elapsed_time_cudf:.4f} seconds")

    # except ImportError:
    #     print("cuDF library is not installed. Skipping cuDF implementation.")
    # except Exception as e:
    #     print(f"An unexpected error occurred with cuDF: {e}")

if __name__ == "__main__":
    #bench_ibis()

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



