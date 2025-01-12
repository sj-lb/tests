
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error as sk_mean_squared_error, r2_score as sk_r2_score
import pandas as pd
from cuml.linear_model import LinearRegression as cuml_LinearRegression
from cuml.metrics import mean_squared_error as cu_mean_squared_error, r2_score as cu_r2_score
import cudf

def remove_nan_rows(X_train, y_train):
    combined = pd.concat([X_train, y_train], axis=1)
    combined = combined.dropna(subset=[y_train.name])
    X_train_cleaned = combined.iloc[:, :-1]  # All columns except the last (features)
    y_train_cleaned = combined.iloc[:, -1]  # Last column (target)
    return X_train_cleaned, y_train_cleaned

def load_data(train_data, test_data, train_column, target_column):
    X_train = train_data.drop(columns=[target_column])
    y_train = train_data[target_column]
    X_train, y_train = remove_nan_rows(X_train, y_train)
    X_test = test_data.drop(columns=[target_column])
    y_test = test_data[target_column]
    X_test, y_test = remove_nan_rows(X_test, y_test)
    print("xtrain", type(X_train))
    print("y_test", type(y_test))
    return X_train, y_train, X_test, y_test

def cu_train_model(X_train, y_train, normalization):
    scaler = StandardScaler()
    if(normalization):
        X_train = scaler.fit_transform(X_train)
        print("x shape:", X_train.shape)
        cudf.DataFrame({"x": X_train.reshape((X_train.shape[0],)), "y": y_train}).to_csv("train_norm.csv", index=False, header=False)
    model = cuml_LinearRegression()
    model.fit(X_train, y_train)
    print("\033[36mweights:\033[33m", model.coef_, model.intercept_, "\033[m")
    return model, scaler

def sk_evaluate_model(y_pred, y_test):
    mse = sk_mean_squared_error(y_test, y_pred)
    r2 = sk_r2_score(y_test, y_pred)
    return mse, r2

def cu_evaluate_model(y_pred, y_test):
    mse = cu_mean_squared_error(y_test, y_pred)
    r2 = cu_r2_score(y_test, y_pred)
    return mse, r2

# Calculate MSE
def calculate_mse(y_actual, y_predicted):
    # Convert lists to arrays for calculation
    print("actual:" ,y_actual)
    print("predicted:", y_predicted)
    n = len(y_actual)
    mse = 0
    for a, p in zip(y_actual, y_predicted):
        print("a:",a)
        print("p:",p)
        mse += (a - p) ** 2
        print("current mse: ", mse)
    mse = mse / n
    print("final mse:", mse)
    return mse

# Calculate R-squared
def calculate_r2(y_actual, y_predicted):
    # Convert lists to arrays for calculation
    y_mean = sum(y_actual) / len(y_actual)
    ss_total = sum((a - y_mean) ** 2 for a in y_actual)  # TSS
    ss_residual = sum((a - p) ** 2 for a, p in zip(y_actual, y_predicted))  # RSS
    r2 = 1 - (ss_residual / ss_total)
    return r2

def get_cuml_prediction(train_data, test_data, train_column, target_column):
    X_train, y_train, X_test, y_test = load_data(train_data, test_data, train_column, target_column)
    # Convert to cuDF DataFrame
    X_train.columns = [f'x_{i}' for i in range(X_train.shape[1])]
    X_cudf = cudf.DataFrame.from_pandas(X_train).to_cupy().get()
    y_cudf = cudf.Series(y_train)

    # Initialize and train the model
    model, scaler = cu_train_model(X_cudf, y_cudf, normalization=True)

    # Make predictions
    X_test = scaler.transform(X_test)
    # print(X_test)
    cudf.DataFrame(X_test).to_csv("test_norm.csv", index=False, header=False)

    cuml_pred = model.predict(X_test)
    cuml_mse, cuml_r2 = cu_evaluate_model(cuml_pred, y_test)
    return cuml_pred, cuml_mse, cuml_r2

if __name__ == '__main__':
    # ------- TEST CONFIGURATION ------- #
    train_column = 'x'
    target_column = 'y'
    # ---------------------------------- #
    mse_r2_test_results = []
    train_filename = "linreg_y_is_x_train_data.csv"
    test_filename = "linreg_y_is_x_test_data.csv"

    train_data = pd.DataFrame({'x': range(1,4000000), 'y': range(1,4000000)})
    test_data = pd.DataFrame({'x':range(4000000, 4000002), 'y': range(4000000,4000002)})

    train_data.to_csv(train_filename, index=False, header=False)
    test_data.to_csv(test_filename, index=False, header=False)

    cuml_pred, cuml_mse, cuml_r2 = get_cuml_prediction(train_data, test_data, train_column=train_column, target_column=target_column)

    print(cuml_pred)

    # Export incrementally results to results.csv
    res = [train_data.shape[0], test_data.shape[0], cuml_mse, cuml_r2]
    mse_r2_test_results.append(res)
    pd.DataFrame(mse_r2_test_results).to_csv("mse_r2_results.csv", index=False, header=True)
