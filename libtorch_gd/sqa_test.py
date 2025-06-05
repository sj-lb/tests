import cudf
import pandas as pd
import random
from sklearn.preprocessing import StandardScaler
from cuml.linear_model import LinearRegression as cuml_LinearRegression
from cuml.metrics import mean_squared_error as cu_mean_squared_error, r2_score as cu_r2_score

def get_linear_regression_data_by_coefs(column_names, total_num_of_rows, a, b):
    total_num_of_rows_range = list(range(1, total_num_of_rows))
    random.shuffle(total_num_of_rows_range)
    train_num_of_rows_range = total_num_of_rows_range[0 : int(len(total_num_of_rows_range)*0.8)]
    test_num_of_rows_range = total_num_of_rows_range[int(len(total_num_of_rows_range)*0.8)+1 : ]
    assert len(column_names) == 2, 'Test failure - Implementation is supported for y=ax+b only'
    train_data = cudf.DataFrame({column_names[0]: [x for x in train_num_of_rows_range],
                               column_names[1]: [a*x + b for x in train_num_of_rows_range]})
    print(f'\033[36mtrain_data:\033[33;1m\n{train_data}')
    test_data = cudf.DataFrame({column_names[0]: [x for x in test_num_of_rows_range],
                              column_names[1]: [a*x + b for x in test_num_of_rows_range]})
    print(f'\033[36mtest_data:\033[33;1m\n{test_data}')
    return train_data, test_data


def remove_nan_rows(X_train, y_train):
    combined = pd.concat([X_train, y_train], axis=1)
    combined = combined.dropna(subset=[y_train.name])
    X_train_cleaned = combined.iloc[:, :-1]  # All columns except the last (features)
    y_train_cleaned = combined.iloc[:, -1]  # Last column (target)
    return X_train_cleaned, y_train_cleaned


def load_data(train_data, test_data, label_col):
    X_train = train_data.drop(columns=[label_col])
    y_train = train_data[label_col]
    X_train, y_train = remove_nan_rows(X_train, y_train)
    X_test = test_data.drop(columns=[label_col])
    y_test = test_data[label_col]
    X_test, y_test = remove_nan_rows(X_test, y_test)
    return X_train, y_train, X_test, y_test


def get_cuml_prediction(model, X_test, y_test):
    cuml_pred = model.predict(X_test)
    cuml_mse = cu_mean_squared_error(y_test, cuml_pred)
    cuml_r2 = cu_r2_score(y_test, cuml_pred)
    return model, cuml_pred, cuml_mse, cuml_r2


if __name__ == '__main__':
    # ------- TEST CONFIGURATION ------- #
    model = cuml_LinearRegression()
    scaler = StandardScaler()
    total_num_of_rows = 5_000_000
    data_cols = ['x', 'y']
    label_col = 'y'
    normalization = True
    # ---------------------------------- #

    # -------- DATA PREPARATION -------- #
    train_data, test_data = get_linear_regression_data_by_coefs(data_cols, total_num_of_rows, 1, 0)
    train_data.to_csv('sqa_train_data.csv', index=False, header=False)
    test_data.to_csv('sqa_test_data.csv', index=False, header=False)
    
    X_train, y_train, X_test, y_test = load_data(train_data, test_data, label_col)

    if normalization:
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        cudf.DataFrame([X_train, y_train]).to_csv('sqa_norm_train_data.csv', index=False, header=False)
        cudf.DataFrame([X_test, y_test]).to_csv('sqa_norm_test_data.csv', index=False, header=False)
    # ---------------------------------- #

    model.fit(X_train, y_train)

    # MSE & R2 Calculation
    cuml_pred, cuml_mse, cuml_r2 = get_cuml_prediction(model, X_test, y_test)

    print(f'\033[36mresults:\nweights=\033[33;1m{model.coef_},{model.intercept_}\033[0;36m \
mse=\033[33;1m{cuml_mse}\033[0;36m\ r2=\033[33;1m{cuml_r2}\n')
    # Check mse results
    # check_mse_results(sq_ml_model.mse, cuml_mse, get_model_comparison_output(sq_ml_model, sk_mse, sk_r2, cuml_mse, cuml_r2))

    # # Check r2 results
    # check_r2_results(sq_ml_model.r2, cuml_r2, get_model_comparison_output(sq_ml_model, sk_mse, sk_r2, cuml_mse, cuml_r2))
