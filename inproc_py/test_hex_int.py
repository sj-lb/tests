import numpy as np
import os
import csv
import datetime
import time
from typing import List, Tuple
from pysqream import connect
import traceback

# --- Configuration ---
DB_HOST = 'localhost'
DB_PORT = 5000
DB_USER = 'sqream'
DB_PASSWORD = 'sqream'
DB_NAME = 'master'
TABLE_NAME = 'hex_full_scan_test'
CSV_FILE = 'hex_full_scan_results.csv'

# INT32 bounds
MIN_INT = -2_147_483_648
MAX_INT = 2_147_483_647
CHUNK_SIZE = 10_000_000

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(["Timestamp", "Chunk_Start", "Chunk_End", "Matches", "Status", "Error_Msg"])

def log_to_csv(row_data):
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f, delimiter='|')
        writer.writerow(row_data)

def generate_sequential_chunk(start_val: int, size: int) -> Tuple[List[Tuple[int, str]], np.ndarray]:
    """
    Creates a chunk of sequential numbers (not random)
    """
    # Calculate upper bound for this chunk (to not exceed MAX_INT)
    end_val = min(start_val + size, MAX_INT + 1)
    
    # 1. יצירת הרצף (numpy.arange מהיר מאוד)
    # אנו משתמשים ב-int64 בתוך ה-numpy כדי למנוע גלישה בחישובים, אבל הערכים הם בטווח int32
    ground_truth_ints = np.arange(start_val, end_val, dtype=np.int64)
    
    # 2. הכנת הנתונים ל-DB
    db_input_data = []
    
    # Optimization: create the ID relative to start_val or sequential
    # Here we use relative ID within the chunk (0 to 999,999) to simplify verification
    for i, val in enumerate(ground_truth_ints):
        # Convert to Hex. 
        # Note: Python converts negatives to '-0x5'. If DB requires Two's Complement (like FFFFFFFB) need to change here.
        # Currently this is defined as regular Signed Hex.
        hex_str = hex(val).upper().replace("0X", "") # Clean 0x and convert to uppercase
        if val < 0:
             # Handle the minus sign that remains after cleaning (e.g. '-5')
             # If you want to return the 0x or other format, this is the place to change.
             # Currently: hex(-10) -> '-0xa' -> '-A'
             pass

        # Add the prefix only if needed (in the example I removed it to keep it clean, can restore)
        final_hex = f"0x{hex_str}" if val >= 0 else f"-0x{hex_str.replace('-','')}"
        
        db_input_data.append((i, final_hex))
        
    return db_input_data, ground_truth_ints

def run_sequential_sweep_test():
    ts_start = datetime.datetime.now().isoformat()
    conn = None
    print(f"[{ts_start}] Starting Full Range Sweep: {MIN_INT} to {MAX_INT}")
    print(f"Chunk Size: {CHUNK_SIZE}")

    try:
        conn = connect(host=DB_HOST, port=DB_PORT, username=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        
        # Preparation step: create the table once
        with conn.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
            cursor.execute(f"CREATE TABLE {TABLE_NAME} (id INT, hex_val TEXT);")
        
        # --- The main loop ---
        current_val =0 # MIN_INT
        total_chunks = (MAX_INT - MIN_INT) // CHUNK_SIZE + 1
        chunk_counter = 0

        while current_val <= MAX_INT:
            chunk_counter += 1
            #chunk_start_time = time.time()
            
            # 1. Create the data for the current chunk
            print(f"\n--- Chunk {chunk_counter}/{total_chunks} [Start: {current_val}] ---")
            print("start generate_sequential_chunk ")
            db_data, ground_truth = generate_sequential_chunk(current_val, CHUNK_SIZE)
            print("end generate_sequential_chunk ")
            rows_in_chunk = len(ground_truth)
            
            with conn.cursor() as cursor:
                # 2. Clean the table (important!)
                cursor.execute(f"TRUNCATE TABLE {TABLE_NAME};")
                
                # 3. Insert the data
                print("start insert ")
                cursor.executemany(f"INSERT INTO {TABLE_NAME} VALUES (?, ?)", db_data)
                print("end insert")
                chunk_start_time = time.time() 
                # 4. Verification
                query = f"SELECT id,cast_utils.hex_to_int(hex_val) FROM {TABLE_NAME} ORDER BY id ASC"
                cursor.execute(query)
                results = cursor.fetchall()
                duration = time.time() - chunk_start_time   
                # 5. In-memory validation
                matches = 0
                error_msg = ""
                status = "SUCCESS"
                
                if len(results) != rows_in_chunk:
                    status = "FAIL_COUNT"
                    error_msg = f"Expected {rows_in_chunk} rows, got {len(results)}"
                else:
                    # Fast verification
                    # Convert DB results to Numpy array for fast comparison
                    # We assume the DB returns Tuple, we take the second element (the value)
                    db_values = np.array([r[1] for r in results], dtype=np.int64)
                    
                    if np.array_equal(db_values, ground_truth):
                        matches = rows_in_chunk
                    else:
                        status = "FAIL_VALUE"
                        # Find the first difference
                        diff_indices = np.where(db_values != ground_truth)[0]
                        if len(diff_indices) > 0:
                            first_idx = diff_indices[0]
                            error_msg = (f"Mismatch at index {first_idx} (Val: {current_val + first_idx}). "
                                         f"Exp: {ground_truth[first_idx]}, Got: {db_values[first_idx]}")

            # 6. Log and advance
            #duration = time.time() - chunk_start_time
            print(f"   -> Result: {status}. Time: {duration:.2f}s")
            if status != "SUCCESS":
                print(f"   !!! ERROR: {error_msg}")
            
            log_to_csv([datetime.datetime.now(), current_val, current_val + rows_in_chunk, matches, status, error_msg])
            
            # Advance the pointer to the next chunk
            current_val += CHUNK_SIZE
            
            # Protection against infinite loop if we exceeded (despite the while)
            if current_val > MAX_INT:
                break

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
    finally:
        if conn: conn.close()
        print("Test Sequence Finished.")

if __name__ == '__main__':
    init_csv()
    run_sequential_sweep_test()
