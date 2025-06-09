import pandas as pd

def combine_secom_data(data_file, labels_file, output_file):
    """
    Reads data from secom.data and secom_labels.data, combines them,
    and saves the result to a new CSV file.

    Args:
        data_file (str): Path to the secom.data file (space-separated).
        labels_file (str): Path to the secom_labels.data file (space-separated).
        output_file (str): Path to the output CSV file.
    """
    try:
        # Read the data file
        df_data = pd.read_csv(data_file, sep=' ', header=None, skipinitialspace=True)

        # Read the labels file
        df_labels = pd.read_csv(labels_file, sep=' ', header=None, skipinitialspace=True)
        df_labels.rename(columns={0: 'Pass/Fail'}, inplace=True)

        # Check if the number of rows matches
        if len(df_data) != len(df_labels):
            raise ValueError("Number of rows in data and labels files do not match.")

        # Concatenate the data and labels DataFrames
        df_combined = pd.concat([df_data, df_labels], axis=1)

        # Save the combined DataFrame to a new CSV file
        df_combined.to_csv(output_file, index=False)

        print(f"Successfully combined '{data_file}' and '{labels_file}' into '{output_file}'.")

    except FileNotFoundError:
        print("Error: One or both of the input files were not found.")
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    data_file = 'test_ibis/data/secom.data'
    labels_file = 'test_ibis/data/secom_labels.data'
    output_file = 'test_ibis/data/secom_combined.csv'
    combine_secom_data(data_file, labels_file, output_file)