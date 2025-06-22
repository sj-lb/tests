import cudf
import cupy as cp
import pandas as pd

_global_sum_x_cudf = {}
_global_sum_y_cudf = {}
_global_sum_x_sq_cudf = {}
_global_sum_y_sq_cudf = {}
_global_sum_xy_cudf = {}
_global_n_cudf = {}

def incremental_corr_cudf(df: cudf.DataFrame):
    """
    Calculates the Pearson correlation coefficient incrementally for chunks of cuDF data.

    Args:
        df (cudf.DataFrame): A chunk of the dataset as a cuDF DataFrame.
                           The DataFrame should contain numerical columns for
                           which you want to calculate the correlation.

    Returns:
        cudf.DataFrame or None: A correlation matrix similar to cuDF .corr(),
                             calculated based on all the chunks processed so far.
                             Returns None if no data has been processed yet.
    """
    global _global_sum_x_cudf, _global_sum_y_cudf, _global_sum_x_sq_cudf, _global_sum_y_sq_cudf, _global_sum_xy_cudf, _global_n_cudf

    if not isinstance(df, cudf.DataFrame) or df.empty:
        return _calculate_final_corr_cudf()

    numeric_cols = df.select_dtypes(include='number').columns

    for col_x in numeric_cols:
        if col_x not in _global_sum_x_cudf:
            _global_sum_x_cudf[col_x] = cp.float64(0)
            _global_sum_y_cudf[col_x] = {}
            _global_sum_x_sq_cudf[col_x] = cp.float64(0)
            _global_sum_y_sq_cudf[col_x] = {}
            _global_sum_xy_cudf[col_x] = {}
            _global_n_cudf[col_x] = {}

        _global_sum_x_cudf[col_x] += df[col_x].sum()
        _global_sum_x_sq_cudf[col_x] += (df[col_x] ** 2).sum()

        for col_y in numeric_cols:
            if col_y not in _global_sum_y_cudf[col_x]:
                _global_sum_y_cudf[col_x][col_y] = cp.float64(0)
                _global_sum_y_sq_cudf[col_x][col_y] = cp.float64(0)
                _global_sum_xy_cudf[col_x][col_y] = cp.float64(0)
                _global_n_cudf[col_x][col_y] = 0

            _global_sum_y_cudf[col_x][col_y] += df[col_y].sum()
            _global_sum_y_sq_cudf[col_x][col_y] += (df[col_y] ** 2).sum()
            _global_sum_xy_cudf[col_x][col_y] += (df[col_x] * df[col_y]).sum()
            _global_n_cudf[col_x][col_y] += len(df)

    return _calculate_final_corr_cudf()

def _calculate_final_corr_cudf():
    """
    Calculates the final correlation matrix based on the accumulated statistics for cuDF.
    """
    if not _global_n_cudf:
        return None

    cols = list(_global_sum_x_cudf.keys())
    corr_matrix = cudf.DataFrame(index=cols, columns=cols)

    for col_x in cols:
        for col_y in cols:
            n = _global_n_cudf[col_x].get(col_y, 0)
            if n < 2:
                corr_matrix.loc[col_x, col_y] = cp.nan
                continue

            sum_x = _global_sum_x_cudf[col_x]
            sum_y = _global_sum_y_cudf[col_x].get(col_y, cp.float64(0))
            sum_x_sq = _global_sum_x_sq_cudf[col_x]
            sum_y_sq = _global_sum_y_sq_cudf[col_x].get(col_y, cp.float64(0))
            sum_xy = _global_sum_xy_cudf[col_x].get(col_y, cp.float64(0))

            numerator = n * sum_xy - sum_x * sum_y
            denominator_x = (n * sum_x_sq - sum_x**2)
            denominator_y = (n * sum_y_sq - sum_y**2)

            if denominator_x <= 0 or denominator_y <= 0:
                corr_matrix.loc[col_x, col_y] = cp.nan
            else:
                correlation = numerator / (cp.sqrt(denominator_x) * cp.sqrt(denominator_y))
                corr_matrix.loc[col_x, col_y] = correlation

    return corr_matrix

# Example Usage:
if __name__ == "__main__":
    # Simulate a large cuDF DataFrame split into chunks
    data1_pdf = pd.DataFrame({'A': [1, 2, 3, 4, 5], 'B': [6, 7, 8, 9, 10]})
    data2_pdf = pd.DataFrame({'A': [6, 7, 8, 9, 10], 'B': [11, 12, 13, 14, 15]})
    data3_pdf = pd.DataFrame({'A': [11, 12, 13, 14, 15], 'B': [16, 17, 18, 19, 20]})

    data1_gdf = cudf.from_pandas(data1_pdf)
    data2_gdf = cudf.from_pandas(data2_pdf)
    data3_gdf = cudf.from_pandas(data3_pdf)

    # Process chunks incrementally with cuDF
    corr_incremental_1_gdf = incremental_corr_cudf(data1_gdf)
    print("Correlation after cuDF chunk 1:\n", corr_incremental_1_gdf)

    corr_incremental_2_gdf = incremental_corr_cudf(data2_gdf)
    print("\nCorrelation after cuDF chunk 2:\n", corr_incremental_2_gdf)

    corr_incremental_3_gdf = incremental_corr_cudf(data3_gdf)
    print("\nCorrelation after cuDF chunk 3:\n", corr_incremental_3_gdf)

    # Calculate the correlation on the entire cuDF dataset at once for comparison
    full_data_gdf = cudf.concat([data1_gdf, data2_gdf, data3_gdf])
    corr_full_gdf = full_data_gdf.corr()
    print("\nCorrelation on the full cuDF dataset:\n", corr_full_gdf)