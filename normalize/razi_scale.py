import numpy as np
from sklearn.preprocessing import StandardScaler
class MyStandardScaler:
    def __init__(self):
        self.mean = None
        self.std = None
    def fit(self, data_batches):
        """Compute global mean and std across all batches."""
        total_sum = 0
        total_sq_sum = 0
        total_count = 0
        # First pass: Compute sum and squared sum for mean & std
        for batch in data_batches:
            batch_np = np.array(batch)
            total_sum += batch_np.sum(axis=0)
            total_sq_sum += (batch_np ** 2).sum(axis=0)
            total_count += batch_np.shape[0]
        # Compute global mean and std
        self.mean = total_sum / total_count
        variance = (total_sq_sum / total_count) - (self.mean ** 2)
        self.std = np.sqrt(variance)
    def transform(self, batch):
        """Apply Standard Scaling using global mean and std."""
        batch_np = np.array(batch)
        return (batch_np - self.mean) / self.std
    def fit_transform(self, data_batches):
        """Fit and then transform data."""
        self.fit(data_batches)
        return [self.transform(batch) for batch in data_batches]
# Generate dataset (1000 rows, process 100 at a time)
data = [[i % 10 + 1, (i % 10 + 2), (i % 10 + 3)] for i in range(1000)]
batch_size = 100
data_batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
# Create StandardScaler and process in batches
scaler = MyStandardScaler()
scaler.fit(data_batches)  # Compute global mean/std
scaled_batches = [scaler.transform(batch) for batch in data_batches]
scaled_data = np.vstack(scaled_batches)  # Merge batches
# Print first 5 rows
print('Manual Standard Scaler (First 5 Rows):')
print(scaled_data[:5])
# Compare with sklearn StandardScaler
sklearn_scaler = StandardScaler()
sklearn_scaled = sklearn_scaler.fit_transform(np.array(data))
print('\nsklearn Standard Scaler (First 5 Rows):')
print(sklearn_scaled[:5])
# Verify they are equal
print('\nAre they the same?', np.allclose(scaled_data, sklearn_scaled))
# x = scaled_data == sklearn_scaled
# print('\nAre they the same?', x.all())