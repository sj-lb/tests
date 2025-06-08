import cuml
from cuml.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification
import cudf
import inspect
print(f"\033[34;1mPath of installed cuml: \033[33m{cuml.__file__}\033[m")
# You can also try to get the source code if available
try:
    print(f"Source file for LogisticRegression: {inspect.getsourcefile(cuml.linear_model.LogisticRegression)}")
except TypeError:
    print("\033[31mSource code for LogisticRegression not directly available via inspect (likely compiled)\033[m")
# 1. Generate some synthetic data
# We'll use sklearn's make_classification for simplicity.
# For CuML, it's often beneficial to work with data that fits on the GPU.
n_samples = 100000
n_features = 20
X, y = make_classification(n_samples=n_samples, n_features=n_features, n_informative=10,
                           n_redundant=5, n_classes=2, random_state=42)

# 2. Split data into training and testing sets
# CuML can work directly with NumPy arrays, but converting to cuDF DataFrames
# or cuPy arrays can sometimes optimize performance further.
X_train_np, X_test_np, y_train_np, y_test_np = train_test_split(X, y, test_size=0.2, random_state=42)

# Convert to cuDF DataFrames (recommended for CuML)
X_train_cudf = cudf.DataFrame(X_train_np)
X_test_cudf = cudf.DataFrame(X_test_np)
y_train_cudf = cudf.Series(y_train_np)
y_test_cudf = cudf.Series(y_test_np)
X_train_cudf.to_csv('xtrain.csv', header=False, index=False)
X_test_cudf.to_csv('xtest.csv', header=False, index=False)
cudf.DataFrame(y_train_cudf).to_csv('ytrain.csv', header=False, index=False)
cudf.DataFrame(y_test_cudf).to_csv('ytest.csv', header=False, index=False)

# 3. Initialize and train the Logistic Regression model
# CuML's LogisticRegression API is very similar to scikit-learn's.
# Key parameters to consider:
#   - penalty: 'l1' or 'l2' (default 'l2')
#   - C: Inverse of regularization strength (default 1.0)
#   - fit_intercept: Whether to fit an intercept (default True)
#   - solver: 'qn' (quasi-Newton) or 'admm' (alternating direction method of multipliers)
#             'qn' is generally faster for larger datasets.
#   - tol: Tolerance for stopping criteria (default 1e-4)
#   - max_iter: Maximum number of iterations (default 1000)

model = LogisticRegression(
    penalty='l2',
    C=1.0,
    fit_intercept=True,
    solver='qn',
    max_iter=1000,
    tol=1e-4,
    random_state=42 # For reproducibility of internal stochastic processes if any
)

print(f"Training Logistic Regression model on {n_samples * 0.8} samples and {n_features} features...")
model.fit(X_train_cudf, y_train_cudf)
print("Training complete.")

# 4. Make predictions
y_pred_cudf = model.predict(X_test_cudf)
y_pred_proba_cudf = model.predict_proba(X_test_cudf)

# Convert predictions back to NumPy for easier evaluation if needed
y_pred_np = y_pred_cudf.to_numpy()
y_pred_proba_np = y_pred_proba_cudf.to_numpy()

# 5. Evaluate the model
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

print("\nModel Evaluation:")
accuracy = accuracy_score(y_test_np, y_pred_np)
print(f"Accuracy: {accuracy:.4f}")

# For ROC AUC, we need the probability of the positive class (class 1)
roc_auc = roc_auc_score(y_test_np, y_pred_proba_np[:, 1])
print(f"ROC AUC: {roc_auc:.4f}")

print("\nClassification Report:")
print(classification_report(y_test_np, y_pred_np))

# Accessing model coefficients and intercept
print(f"\nModel Coefficients (first 5): {model.coef_.to_numpy()}")
print(f"Model Intercept: {model.intercept_.to_numpy()[0]}")