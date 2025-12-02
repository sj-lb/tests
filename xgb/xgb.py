import cudf
import cupy as cp
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def train_xgboost_model(csv_file_path, target_column_name):
    """
    Loads data, splits it, and trains an XGBoost model with specific parameters.
    """
    
    # 1. Load Data
    print(f"Loading data from {csv_file_path}...")
    df = cudf.read_csv(csv_file_path)
    df = cudf.concat([df] * 7)
    df = cudf.DataFrame(df, dtype=cp.float32)

    # 2. Preprocessing
    # Separate Features (X) and Target (y)
    # NOTE: Ensure your data is numeric. If you have categorical text data,
    # you will need to encode it (e.g., using OneHotEncoder) before this step.
    X = df.drop(columns=[target_column_name])
    y = df[target_column_name]

    # Split into Train and Test sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42
    )
    print(f'\033[35mTraining samples: {len(X_train)}, Testing samples: {len(X_test)}\033[0m')

    # 3. Configure Parameters
    # Mapping user request to valid XGBoost arguments:
    # VERBOSITY='DEBUG' -> verbosity=3 (0=Silent, 1=Warning, 2=Info, 3=Debug)
    # ETA -> learning_rate
    # OBJECTIVE -> binary:logistic (XGBoost uses a colon, not underscore)
    
    model = xgb.XGBClassifier(
        verbosity=3,                  # 'DEBUG'
        tree_method='auto',           # 'auto'
        device='cuda',
        objective='binary:logistic',  # 'binary_logistic'
        learning_rate=0.01,           # 'ETA'
        max_depth=5,                  # MAX_DEPTH
        use_label_encoder=False,
        eval_metric='logloss'         # Removes warning for binary classification
    )

    # 4. Train the Model
    print("\nStarting training...")
    model.fit(X_train, y_train)

    # 5. Evaluate
    print("\nEvaluating model...")
    predictions = model.predict(X_test)
    
    accuracy = accuracy_score(y_test.to_numpy(), predictions)
    print(f"\n--- Results ---")
    print(f"Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test.to_numpy(), predictions))
    
    return model

# --- Execution ---
if __name__ == "__main__":
    # REPLACE 'your_data.csv' with your actual filename
    # REPLACE 'target' with the name of the column you are trying to predict
    csv_file = '/home/johnny/.sqream/data_gen/xgb_SQ19850/big_adult_train_1000.csv'
    target_col = 'target'

    trained_model = train_xgboost_model(csv_file, target_col)