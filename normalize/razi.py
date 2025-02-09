import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize, StandardScaler
import numpy as np

def l2_normalize_chunked(data, chunk_size=100):
    """
    Apply L2 normalization (row-wise) to a dataset in chunks.
    Each row is scaled so that its L2 norm (Euclidean norm) is 1.
    :param data: List of lists (2D array) where each inner list is a data sample.
    :param chunk_size: Number of rows to process at a time.
    :return: Generator yielding L2-normalized dataset in chunks.
    """
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        normalized_chunk = []
        for row in chunk:
            norm = np.sqrt(sum(x ** 2 for x in row))
            if norm == 0:
                print('\033[33;1m0 norm encountered\033[m')
            normalized_row = [x / norm if norm != 0 else 0 for x in row]
            normalized_chunk.append(normalized_row)
        yield normalized_chunk


def standardize_chunked(data, chunk_size=100):
    """
    Apply standardization (z-score normalization) to a dataset in chunks.
    Each column is scaled to have a mean of 0 and a standard deviation of 1.
    :param data: List of lists (2D array) where each inner list is a data sample.
    :param chunk_size: Number of rows to process at a time.
    :return: Generator yielding standardized dataset in chunks.
    """
    data_np = np.array(data)  # Convert to NumPy array for efficient calculations

    n_cols = data_np.shape[1]
    means = np.zeros(n_cols)
    stds = np.zeros(n_cols)

    # Calculate means and stds in chunks
    for i in range(0, len(data), chunk_size):
        chunk = data_np[i:i + chunk_size]
        means += np.mean(chunk, axis=0) * len(chunk)
        stds += np.std(chunk, axis=0) * len(chunk)
    
    means /= len(data)  # Average to get the true mean
    stds /= len(data)  # Average to get the true std
    stds[stds == 0] = 1 # avoid division by zero
    
    for i in range(0, len(data), chunk_size):
        chunk = data_np[i:i + chunk_size]
        standardized_chunk = (chunk - means) / stds
        yield standardized_chunk.tolist()  # Convert back to list of lists


# Generate a dataset with 1000 rows
data = [[i % 10, i % 10 + 1, i % 10 + 2, i % 10 + 3] for i in range(100000)]

my_norm_data = []
# Process data in chunks
for chunk in l2_normalize_chunked(data, chunk_size=100):
    my_norm_data.extend(chunk)

sk_norm_data = normalize(data)

scaler = StandardScaler()
scaler.fit(data)
sk_scaled_data = scaler.transform(data)

my_scaled_data = []

for chunk in standardize_chunked(data, chunk_size=100):
    my_scaled_data.extend(chunk)

print(f'\033[36moriginal data:\033[33;1m\n{pd.DataFrame(data)}\033[m')
print(f'\033[36m\nindependently normalized data:\033[33;1m\n{pd.DataFrame(my_norm_data)}\033[m')
print(f'\033[36m\nsklearn normalized data:\033[33;1m\n{pd.DataFrame(sk_norm_data)}\033[m')
print(f'\033[36m\nindependently scaled data:\033[33;1m\n{pd.DataFrame(my_scaled_data)}\033[m')
print(f'\033[36m\nsklearn scaled data:\033[33;1m\n{pd.DataFrame(sk_scaled_data)}\033[m')

print('\033[36m\nsklearn normalize vs independent func:\033[m')
x = sk_norm_data == my_norm_data
print(x)
if x.all():
    print('\033[32;1mall good!\033[m')
else:
    diff = sk_norm_data - my_norm_data
    print(f'\033[31mdifference detected:\033[33;1m\n{pd.DataFrame(diff)}\033[m')
    print(f'\033[36mmax difference:\033[33;1m {max(abs(diff.min()), diff.max())}\033[m')

print('\033[36m\nsklearn StandardScaler vs independent func:\033[m')
x2 = sk_scaled_data == my_scaled_data
print(x2)
if x2.all():
    print('\033[32;1mall good!\033[m')
else:
    diff = sk_scaled_data - my_scaled_data
    print(f'\033[31mdifference detected:\033[33;1m\n{pd.DataFrame(diff)}\033[m')
    print(f'\033[36mmax difference:\033[33;1m {max(abs(diff.min()), diff.max())}\033[m')