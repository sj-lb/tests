# Import necessary libraries
import traceback
import ibis
import datetime
import decimal
import os

# Try importing PySQream. If not available, we'll mock it for demonstration.
try:
    import pysqream
except ImportError:
    print("PySQream not found. Mocking the connection for demonstration purposes.")
    exit(1)

from ibis_sqreamdb import Backend, connect as sq_con

class IbisSQreamTester:
    def __init__(self, host, port, username, password, database):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.connection = None
        self.ibis_con = None
        self.test_results = {}

    def connect(self):
        """Establishes connection to SQream and Ibis."""
        try:
            # Connect to SQream using PySQream
            # IMPORTANT: Replace with your actual SQream connection details
            self.connection = pysqream.connect(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database
            )
            print("Successfully connected to SQream via PySQream.")

            # Create an Ibis connection using the PySQream connection
            # Ibis's PostgreSQL backend can often work with PostgreSQL-compliant databases
            # like SQream. If specific SQream dialect is needed, this might change.
            self.ibis_con = sq_con(host=self.host,
                                   port=self.port,
                                   user=self.username,
                                   password=self.password,
                                   database=self.database,
                                   clustered=False)
            print("Successfully established Ibis connection to SQream.")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            traceback.print_exc()
            return False

    def close(self):
        """Closes the connections."""
        # if self.ibis_con:
        #     self.ibis_con.close() # Ibis close might close the underlying connection
        #     print("Ibis connection closed.")
        if self.connection:
            self.connection.close()
            print("PySQream connection closed.")

    def run_test(self, test_name, test_function):
        """
        Runs a single test case and records its result.
        :param test_name: Name of the test.
        :param test_function: A callable (function) containing the test logic.
        """
        print(f"\n--- Running test: {test_name} ---")
        try:
            # Check if ibis_con is initialized before running the test
            if self.ibis_con is None:
                raise RuntimeError("Ibis connection not established. Cannot run test.")
            test_function(self.ibis_con)
            self.test_results[test_name] = {"status": "PASSED"}
            print(f"--- Test '{test_name}' PASSED ---")
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            self.test_results[test_name] = {"status": "FAILED", "error_type": error_type, "message": error_message}
            print(f"--- Test '{test_name}' FAILED: {error_type} ---")
            traceback.print_exc() # Print full traceback

    def summarize_results(self):
        """Prints a summary of all test results."""
        print("\n" + "="*50)
        print("Test Summary:")
        print("="*50)

        passed_count = sum(1 for r in self.test_results.values() if r["status"] == "PASSED")
        failed_count = sum(1 for r in self.test_results.values() if r["status"] == "FAILED")

        print(f"Total tests: {len(self.test_results)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")

        if failed_count > 0:
            print("\nFailed Tests:")
            for test_name, result in self.test_results.items():
                if result["status"] == "FAILED":
                    print(f"- {test_name}: Error Type: {result['error_type']}, Message: {result['message']}")
        print("="*50)

# --- Example Usage ---
if __name__ == "__main__":
    # IMPORTANT: Replace these with your actual SQream connection details
    # For demonstration, these are dummy values.
    # If pysqream is not installed, a mock connection will be used.
    SQREAM_HOST = os.environ.get("IBIS_SQREAM_HOST", "192.168.4.31")
    SQREAM_PORT = int(os.environ.get("IBIS_SQREAM_PORT", 5000))
    SQREAM_USERNAME = os.environ.get("IBIS_SQREAM_USER", "sqream")
    SQREAM_PASSWORD = os.environ.get("IBIS_SQREAM_PASSWORD", "sqream")
    SQREAM_DATABASE = os.environ.get("IBIS_SQREAM_DATABASE", "master")

    tester = IbisSQreamTester(
        host=SQREAM_HOST,
        port=SQREAM_PORT,
        username=SQREAM_USERNAME,
        password=SQREAM_PASSWORD,
        database=SQREAM_DATABASE
    )

    if tester.connect():
        # --- Define your test functions here ---
        # Each test function takes the ibis connection as an argument
        # and performs operations, raising an exception if something goes wrong.

        # Assumed schema for 'my_table':
        # id: int64
        # value_col: float64 (e.g., for median, correlation, sum, mean, round)
        # string_col: string (e.g., for endsWith, stringContains, regexExtract, stringConcat, findInSet)
        # date_col: date (e.g., for date extractions)
        # timestamp_col: timestamp (e.g., for timestamp functions)
        # bool_col: boolean (e.g., for arrayAll, arrayAny)
        # array_int_col: array<int64> (e.g., for array functions)
        # array_string_col: array<string> (e.g., for arrayStringJoin)
        # map_string_int_col: map<string, int64> (e.g., for map functions)
        # struct_col: struct<name: string, age: int64> (e.g., for struct functions)
        # json_col: json (e.g., for JSON functions)
        # category_col: string (e.g., for mode, group by)
        # another_value_col: float64 (for correlation)

        # Assumed schema for 'other_table' (for join operations, if applicable)
        # id: int64
        # related_value: string


        def test_approx_count_distinct(con):
            """Tests ApproxCountDistinct (approx_distinct)."""
            table = con.table('my_table')
            result = table.id.approx_distinct().execute()
            print(f"ApproxCountDistinct result: {result}")
            assert isinstance(result, (int, float)), "ApproxCountDistinct did not return a number."

        def test_approx_median(con):
            """Tests ApproxMedian (approx_median)."""
            table = con.table('my_table')
            result = table.value_col.approx_median().execute()
            print(f"ApproxMedian result: {result}")
            assert isinstance(result, (int, float)), "ApproxMedian did not return a number."

        def test_approx_multi_quantile(con):
            """Tests ApproxMultiQuantile (approx_quantiles with multiple q)."""
            table = con.table('my_table')
            result = table.value_col.approx_quantiles([0.25, 0.75]).execute()
            print(f"ApproxMultiQuantile result: {result}")
            assert isinstance(result, list) and len(result) == 2, "ApproxMultiQuantile did not return a list of two values."

        def test_approx_quantile(con):
            """Tests ApproxQuantile (approx_quantiles with single q)."""
            table = con.table('my_table')
            result = table.value_col.approx_quantiles(0.5).execute()
            print(f"ApproxQuantile result: {result}")
            assert isinstance(result, (int, float)), "ApproxQuantile did not return a number."

        def test_arg_max(con):
            """Tests ArgMax (argmax)."""
            table = con.table('my_table')
            # Get the string_col value where value_col is max
            result = table.string_col[table.value_col.argmax()].execute()
            print(f"ArgMax result: {result}")
            # This is hard to assert without knowing actual data. Just check for non-None.
            assert result is not None, "ArgMax returned None."

        def test_arg_min(con):
            """Tests ArgMin (argmin)."""
            table = con.table('my_table')
            # Get the string_col value where value_col is min
            result = table.string_col[table.value_col.argmin()].execute()
            print(f"ArgMin result: {result}")
            assert result is not None, "ArgMin returned None."

        def test_array_all(con):
            """Tests ArrayAll (array.all())."""
            table = con.table('my_table')
            # Assumes array_int_col exists and contains numbers for predicate check
            result = table.array_int_col.all(lambda x: x > 0).execute()
            print(f"ArrayAll result: {result}")
            assert isinstance(result, bool), "ArrayAll did not return a boolean."

        def test_array_any(con):
            """Tests ArrayAny (array.any())."""
            table = con.table('my_table')
            result = table.array_int_col.any(lambda x: x == 1).execute()
            print(f"ArrayAny result: {result}")
            assert isinstance(result, bool), "ArrayAny did not return a boolean."

        def test_array_collect(con):
            """Tests ArrayCollect (collect)."""
            table = con.table('my_table')
            result = table.id.collect().execute()
            print(f"ArrayCollect result: {result}")
            assert isinstance(result, list), "ArrayCollect did not return a list."

        def test_array_concat(con):
            """Tests ArrayConcat (array_concat)."""
            table = con.table('my_table')
            # Create a literal array and concatenate with existing column
            result = (table.array_int_col + ibis.array([4, 5])).execute()
            print(f"ArrayConcat result: {result}")
            assert isinstance(result, list) and len(result) > 3, "ArrayConcat did not return a larger list."

        def test_array_contains(con):
            """Tests ArrayContains (array.contains())."""
            table = con.table('my_table')
            result = table.array_int_col.contains(2).execute()
            print(f"ArrayContains result: {result}")
            assert isinstance(result, bool), "ArrayContains did not return a boolean."

        def test_array_distinct(con):
            """Tests ArrayDistinct (array.distinct())."""
            table = con.table('my_table')
            # Assumes array_int_col might have duplicates in some rows
            result = table.array_int_col.distinct().execute()
            print(f"ArrayDistinct result: {result}")
            assert isinstance(result, list), "ArrayDistinct did not return a list."

        def test_array_filter(con):
            """Tests ArrayFilter (array.filter())."""
            table = con.table('my_table')
            result = table.array_int_col.filter(lambda x: x % 2 == 0).execute()
            print(f"ArrayFilter result: {result}")
            assert isinstance(result, list), "ArrayFilter did not return a list."

        def test_array_index(con):
            """Tests ArrayIndex (array[index])."""
            table = con.table('my_table')
            result = table.array_int_col[1].execute() # Get second element
            print(f"ArrayIndex result: {result}")
            assert result is not None, "ArrayIndex returned None."

        def test_array_intersect(con):
            """Tests ArrayIntersect (array_intersect)."""
            table = con.table('my_table')
            result = ibis.array([1, 3, 5]).intersect(table.array_int_col).execute()
            print(f"ArrayIntersect result: {result}")
            assert isinstance(result, list), "ArrayIntersect did not return a list."

        def test_array_map(con):
            """Tests ArrayMap (array.map())."""
            table = con.table('my_table')
            result = table.array_int_col.map(lambda x: x * 2).execute()
            print(f"ArrayMap result: {result}")
            assert isinstance(result, list), "ArrayMap did not return a list."

        def test_array_max(con):
            """Tests ArrayMax (array.max())."""
            table = con.table('my_table')
            result = table.array_int_col.max().execute()
            print(f"ArrayMax result: {result}")
            assert isinstance(result, (int, float)), "ArrayMax did not return a number."

        def test_array_mean(con):
            """Tests ArrayMean (array.mean())."""
            table = con.table('my_table')
            result = table.array_int_col.mean().execute()
            print(f"ArrayMean result: {result}")
            assert isinstance(result, (int, float)), "ArrayMean did not return a number."

        def test_array_min(con):
            """Tests ArrayMin (array.min())."""
            table = con.table('my_table')
            result = table.array_int_col.min().execute()
            print(f"ArrayMin result: {result}")
            assert isinstance(result, (int, float)), "ArrayMin did not return a number."

        def test_array_mode(con):
            """Tests ArrayMode (array.mode())."""
            table = con.table('my_table')
            result = table.array_int_col.mode().execute()
            print(f"ArrayMode result: {result}")
            assert isinstance(result, list), "ArrayMode did not return a list."

        def test_array_position(con):
            """Tests ArrayPosition (array.position())."""
            table = con.table('my_table')
            result = table.array_int_col.position(2).execute()
            print(f"ArrayPosition result: {result}")
            assert isinstance(result, int), "ArrayPosition did not return an integer."

        def test_array_repeat(con):
            """Tests ArrayRepeat (array.repeat())."""
            table = con.table('my_table')
            # Example using a literal array to repeat
            result = ibis.array([1]).repeat(3).execute()
            print(f"ArrayRepeat result: {result}")
            assert isinstance(result, list) and len(result) == 3, "ArrayRepeat did not return a list of repeated elements."

        def test_array_slice(con):
            """Tests ArraySlice (array.slice())."""
            table = con.table('my_table')
            result = table.array_int_col.slice(1, 3).execute() # From index 1 (inclusive) to 3 (exclusive)
            print(f"ArraySlice result: {result}")
            assert isinstance(result, list), "ArraySlice did not return a list."

        def test_array_sort(con):
            """Tests ArraySort (array.sort())."""
            table = con.table('my_table')
            # Assumes array_int_col may not be sorted
            result = table.array_int_col.sort().execute()
            print(f"ArraySort result: {result}")
            assert isinstance(result, list), "ArraySort did not return a list."

        def test_array_string_join(con):
            """Tests ArrayStringJoin (array.string_join())."""
            table = con.table('my_table')
            result = table.array_string_col.string_join('-').execute()
            print(f"ArrayStringJoin result: {result}")
            assert isinstance(result, str), "ArrayStringJoin did not return a string."

        def test_array_sum(con):
            """Tests ArraySum (array.sum())."""
            table = con.table('my_table')
            result = table.array_int_col.sum().execute()
            print(f"ArraySum result: {result}")
            assert isinstance(result, (int, float)), "ArraySum did not return a number."

        def test_array_union(con):
            """Tests ArrayUnion (array_union)."""
            table = con.table('my_table')
            result = ibis.array([3, 4, 5]).union(table.array_int_col).execute()
            print(f"ArrayUnion result: {result}")
            assert isinstance(result, list), "ArrayUnion did not return a list."

        def test_cast(con):
            """Tests Cast (cast)."""
            table = con.table('my_table')
            result = table.id.cast('string').execute()
            print(f"Cast result: {result}")
            assert isinstance(result, str), "Cast did not cast to string."

        def test_correlation(con):
            """Tests Correlation (corr)."""
            table = con.table('my_table')
            result = table.value_col.corr(table.another_value_col).execute()
            print(f"Correlation result: {result}")
            assert isinstance(result, (int, float)), "Correlation did not return a number."

        def test_count_distinct_star(con):
            """Tests CountDistinctStar (count(distinct *))."""
            # This counts distinct rows. Requires more than one column for distinct * to be meaningful.
            # In Ibis, this often translates to `table.distinct().count()`.
            table = con.table('my_table')
            result = table.distinct().count().execute()
            print(f"CountDistinctStar result: {result}")
            assert isinstance(result, int), "CountDistinctStar did not return an integer."

        def test_date_from_ymd(con):
            """Tests DateFromYMD (date)."""
            # Create a date literal from year, month, day
            result = ibis.date(2023, 10, 26).execute()
            print(f"DateFromYMD result: {result}")
            assert isinstance(result, datetime.date), "DateFromYMD did not return a date."

        def test_day_of_week_index(con):
            """Tests DayOfWeekIndex (day_of_week.index())."""
            table = con.table('my_table')
            result = table.date_col.day_of_week.index().execute()
            print(f"DayOfWeekIndex result: {result}")
            assert isinstance(result, int), "DayOfWeekIndex did not return an integer."

        def test_day_of_week_name(con):
            """Tests DayOfWeekName (day_of_week.full_name())."""
            table = con.table('my_table')
            result = table.date_col.day_of_week.full_name().execute()
            print(f"DayOfWeekName result: {result}")
            assert isinstance(result, str), "DayOfWeekName did not return a string."

        def test_ends_with(con):
            """Tests EndsWith (string.endswith())."""
            table = con.table('my_table')
            result = table.string_col.endswith('value').execute()
            print(f"EndsWith result: {result}")
            assert isinstance(result, bool), "EndsWith did not return a boolean."

        def test_extract_day_of_year(con):
            """Tests ExtractDayOfYear (date.day_of_year)."""
            table = con.table('my_table')
            result = table.date_col.day_of_year.execute()
            print(f"ExtractDayOfYear result: {result}")
            assert isinstance(result, int), "ExtractDayOfYear did not return an integer."

        def test_extract_epoch_seconds(con):
            """Tests ExtractEpochSeconds (timestamp.epoch_seconds())."""
            table = con.table('my_table')
            result = table.timestamp_col.epoch_seconds().execute()
            print(f"ExtractEpochSeconds result: {result}")
            assert isinstance(result, (int, float)), "ExtractEpochSeconds did not return a number."

        def test_extract_iso_year(con):
            """Tests ExtractIsoYear (date.iso_year)."""
            table = con.table('my_table')
            result = table.date_col.iso_year.execute()
            print(f"ExtractIsoYear result: {result}")
            assert isinstance(result, int), "ExtractIsoYear did not return an integer."

        def test_extract_microsecond(con):
            """Tests ExtractMicrosecond (timestamp.microsecond)."""
            table = con.table('my_table')
            result = table.timestamp_col.microsecond.execute()
            print(f"ExtractMicrosecond result: {result}")
            assert isinstance(result, int), "ExtractMicrosecond did not return an integer."

        def test_extract_millisecond(con):
            """Tests ExtractMillisecond (timestamp.millisecond)."""
            table = con.table('my_table')
            result = table.timestamp_col.millisecond.execute()
            print(f"ExtractMillisecond result: {result}")
            assert isinstance(result, int), "ExtractMillisecond did not return an integer."

        def test_extract_second(con):
            """Tests ExtractSecond (timestamp.second)."""
            table = con.table('my_table')
            result = table.timestamp_col.second.execute()
            print(f"ExtractSecond result: {result}")
            assert isinstance(result, int), "ExtractSecond did not return an integer."

        def test_extract_week_of_year(con):
            """Tests ExtractWeekOfYear (date.week_of_year)."""
            table = con.table('my_table')
            result = table.date_col.week_of_year.execute()
            print(f"ExtractWeekOfYear result: {result}")
            assert isinstance(result, int), "ExtractWeekOfYear did not return an integer."

        def test_find_in_set(con):
            """Tests FindInSet (string.find_in_set())."""
            table = con.table('my_table')
            # Assumes string_col can contain values like 'apple', 'banana'
            result = table.string_col.find_in_set(['value', 'another']).execute()
            print(f"FindInSet result: {result}")
            assert isinstance(result, bool), "FindInSet did not return a boolean."

        def test_first(con):
            """Tests First (first())."""
            table = con.table('my_table')
            result = table.id.first().execute()
            print(f"First result: {result}")
            assert result is not None, "First returned None."

        def test_hash(con):
            """Tests Hash (hash())."""
            table = con.table('my_table')
            result = table.string_col.hash().execute()
            print(f"Hash result: {result}")
            assert isinstance(result, int), "Hash did not return an integer."

        def test_integer_range(con):
            """Tests IntegerRange (range)."""
            # Creates an integer range literal
            result = ibis.range(0, 5).execute()
            print(f"IntegerRange result: {result}")
            assert isinstance(result, list) and len(result) == 5, "IntegerRange did not return a list of 5 integers."

        def test_is_inf(con):
            """Tests IsInf (isinf())."""
            # Create a literal float, potentially including an inf for testing
            inf_literal = ibis.literal(float('inf')).cast('float64')
            result = inf_literal.isinf().execute()
            print(f"IsInf result (inf): {result}")
            assert result is True, "IsInf did not correctly identify infinity."

            non_inf_literal = ibis.literal(1.0).cast('float64')
            result = non_inf_literal.isinf().execute()
            print(f"IsInf result (non-inf): {result}")
            assert result is False, "IsInf incorrectly identified a non-infinity."


        def test_is_nan(con):
            """Tests IsNan (isnan())."""
            # Create a literal float, potentially including a NaN for testing
            nan_literal = ibis.literal(float('nan')).cast('float64')
            result = nan_literal.isnan().execute()
            print(f"IsNan result (nan): {result}")
            assert result is True, "IsNan did not correctly identify NaN."

            non_nan_literal = ibis.literal(1.0).cast('float64')
            result = non_nan_literal.isnan().execute()
            print(f"IsNan result (non-nan): {result}")
            assert result is False, "IsNan incorrectly identified a non-NaN."

        def test_json_get_item(con):
            """Tests JSONGetItem (json_col['key'] or json_col.foo)."""
            table = con.table('my_table')
            # Assumes json_col is a JSON type with a key 'name'
            result = table.json_col['key'].execute()
            print(f"JSONGetItem result: {result}")
            assert result is not None, "JSONGetItem returned None."

        def test_last(con):
            """Tests Last (last())."""
            table = con.table('my_table')
            result = table.id.last().execute()
            print(f"Last result: {result}")
            assert result is not None, "Last returned None."

        def test_log(con):
            """Tests Log (log())."""
            table = con.table('my_table')
            result = table.value_col.log().execute()
            print(f"Log result: {result}")
            assert isinstance(result, (int, float)), "Log did not return a number."

        def test_log2(con):
            """Tests Log2 (log2())."""
            table = con.table('my_table')
            result = table.value_col.log2().execute()
            print(f"Log2 result: {result}")
            assert isinstance(result, (int, float)), "Log2 did not return a number."

        def test_map(con):
            """Tests Map (map_from_arrays)."""
            # Create a map literal
            result = ibis.map({"k1": 1, "k2": 2}).execute()
            print(f"Map result: {result}")
            assert isinstance(result, dict), "Map did not return a dictionary."

        def test_map_get(con):
            """Tests MapGet (map_col['key'])."""
            table = con.table('my_table')
            result = table.map_string_int_col['k1'].execute()
            print(f"MapGet result: {result}")
            assert isinstance(result, int), "MapGet did not return an integer."

        def test_map_keys(con):
            """Tests MapKeys (map_col.keys())."""
            table = con.table('my_table')
            result = table.map_string_int_col.keys().execute()
            print(f"MapKeys result: {result}")
            assert isinstance(result, list), "MapKeys did not return a list."

        def test_map_length(con):
            """Tests MapLength (map_col.length())."""
            table = con.table('my_table')
            result = table.map_string_int_col.length().execute()
            print(f"MapLength result: {result}")
            assert isinstance(result, int), "MapLength did not return an integer."

        def test_map_merge(con):
            """Tests MapMerge (map_merge)."""
            table = con.table('my_table')
            # Merge existing map_string_int_col with a new literal map
            new_map = ibis.map({"k3": 3})
            result = ibis.map_merge(table.map_string_int_col, new_map).execute()
            print(f"MapMerge result: {result}")
            assert isinstance(result, dict) and 'k3' in result, "MapMerge did not return a merged dictionary."

        def test_map_values(con):
            """Tests MapValues (map_col.values())."""
            table = con.table('my_table')
            result = table.map_string_int_col.values().execute()
            print(f"MapValues result: {result}")
            assert isinstance(result, list), "MapValues did not return a list."

        def test_median(con):
            """Tests Median (median)."""
            table = con.table('my_table')
            result = table.value_col.median().execute()
            print(f"Median result: {result}")
            assert isinstance(result, (int, float)), "Median did not return a number."

        def test_mode(con):
            """Tests Mode (mode)."""
            table = con.table('my_table')
            # Assumes category_col has repeating values
            result = table.category_col.mode().execute()
            print(f"Mode result: {result}")
            # Mode can return a list if multiple modes, or single value
            assert result is not None, "Mode returned None."

        def test_modulus(con):
            """Tests Modulus (mod)."""
            table = con.table('my_table')
            # Assuming id column for modulus operation
            result = (table.id % 2).execute()
            print(f"Modulus result: {result}")
            assert isinstance(result, int), "Modulus did not return an integer."

        def test_multi_quantile(con):
            """Tests MultiQuantile (quantiles with multiple q)."""
            table = con.table('my_table')
            result = table.value_col.quantiles([0.25, 0.75]).execute()
            print(f"MultiQuantile result: {result}")
            assert isinstance(result, list) and len(result) == 2, "MultiQuantile did not return a list of two values."

        def test_quantile(con):
            """Tests Quantile (quantiles with single q)."""
            table = con.table('my_table')
            result = table.value_col.quantiles(0.5).execute()
            print(f"Quantile result: {result}")
            assert isinstance(result, (int, float)), "Quantile did not return a number."

        def test_range(con):
            """Tests Range (column_expr.range())."""
            # This is different from ibis.range. It creates an array from min to max of a column.
            table = con.table('my_table')
            result = table.id.range().execute()
            print(f"Range (column) result: {result}")
            assert isinstance(result, list), "Range (column) did not return a list."

        def test_regex_extract(con):
            """Tests RegexExtract (string.re_extract())."""
            table = con.table('my_table')
            # Assumes string_col has patterns to extract, e.g., 'hello world' -> 'world'
            result = table.string_col.re_extract(r'(\w+)$', 0).execute() # Extract last word
            print(f"RegexExtract result: {result}")
            assert isinstance(result, str), "RegexExtract did not return a string."

        def test_round(con):
            """Tests Round (round())."""
            table = con.table('my_table')
            result = table.value_col.round(0).execute() # Round to 0 decimal places
            print(f"Round result: {result}")
            assert isinstance(result, (int, float, decimal.Decimal)), "Round did not return a number."

        def test_string_concat(con):
            """Tests StringConcat (string + string or string_concat)."""
            table = con.table('my_table')
            result = (table.string_col + '_suffix').execute()
            print(f"StringConcat result: {result}")
            assert isinstance(result, str), "StringConcat did not return a string."

        def test_string_contains(con):
            """Tests StringContains (string.contains())."""
            table = con.table('my_table')
            result = table.string_col.contains('value').execute()
            print(f"StringContains result: {result}")
            assert isinstance(result, bool), "StringContains did not return a boolean."

        def test_string_to_time(con):
            """Tests StringToTime (to_timestamp, to_date, to_time)."""
            # Ibis has various to_timestamp/date/time functions. Pick one.
            # Assuming '2023-10-26 14:30:00' format in a string column or literal
            string_timestamp = ibis.literal('2023-10-26 14:30:00')
            result = string_timestamp.cast('timestamp').execute()
            print(f"StringToTime result: {result}")
            assert isinstance(result, datetime.datetime), "StringToTime did not return a datetime object."

        def test_struct_column(con):
            """Tests StructColumn (struct expression construction)."""
            # This usually involves creating a new struct column.
            # The actual test is whether ibis can compile it.
            table = con.table('my_table')
            new_struct = ibis.struct({'id_val': table.id, 'string_val': table.string_col})
            # Try to select it and limit to ensure it compiles/executes
            result = table.select(new_struct.as_('new_struct')).limit(1).execute()
            print(f"StructColumn result: {result}")
            assert 'new_struct' in result.columns, "StructColumn test failed: new_struct not in result."
            assert isinstance(result['new_struct'][0], dict), "StructColumn did not result in a dict-like structure."

        def test_struct_field(con):
            """Tests StructField (struct_col.field_name)."""
            table = con.table('my_table')
            # Assumes struct_col exists with a field 'name'
            result = table.struct_col.name.execute()
            print(f"StructField result: {result}")
            assert isinstance(result, str), "StructField did not return a string."

        def test_sum(con):
            """Tests Sum (sum)."""
            table = con.table('my_table')
            result = table.value_col.sum().execute()
            print(f"Sum result: {result}")
            assert isinstance(result, (int, float)), "Sum did not return a number."

        def test_table_unnest(con):
            """Tests TableUnnest (unnest)."""
            table = con.table('my_table')
            # Assumes array_int_col exists. Unnest will expand rows.
            # Select id and the unnested array element.
            result = table.select(table.id, table.array_int_col.unnest().as_('unnested_element')).execute()
            print(f"TableUnnest result (first 5 rows): {result.head(5)}")
            # Assert that the number of rows has likely increased (if there are arrays)
            # or at least that the new column exists.
            assert 'unnested_element' in result.columns, "TableUnnest failed: unnested_element column not found."
            assert len(result) >= len(table.execute()), "TableUnnest did not produce more rows."

        def test_timestamp_bucket(con):
            """Tests TimestampBucket (timestamp.bucket())."""
            table = con.table('my_table')
            # Bucket by a common interval, e.g., '1 hour'
            result = table.timestamp_col.bucket('1 hour').execute()
            print(f"TimestampBucket result: {result}")
            assert isinstance(result, datetime.datetime), "TimestampBucket did not return a datetime object."

        def test_timestamp_from_ymdhms(con):
            """Tests TimestampFromYMDHMS (timestamp)."""
            # Create a timestamp literal from year, month, day, hour, minute, second
            result = ibis.timestamp(2023, 10, 26, 14, 30, 0).execute()
            print(f"TimestampFromYMDHMS result: {result}")
            assert isinstance(result, datetime.datetime), "TimestampFromYMDHMS did not return a datetime."

        def test_to_json_array(con):
            """Tests ToJSONArray (to_json_array)."""
            table = con.table('my_table')
            # Converts array column to JSON string representation
            result = table.array_int_col.to_json().execute() # Ibis often uses .to_json() for this
            print(f"ToJSONArray result: {result}")
            assert isinstance(result, str) and result.startswith('[') and result.endswith(']'), \
                "ToJSONArray did not return a JSON array string."

        def test_try_cast(con):
            """Tests TryCast (try_cast)."""
            # Try to cast a string that might fail to an integer
            literal_to_cast = ibis.literal('123').cast('string')
            result = literal_to_cast.try_cast('int64').execute()
            print(f"TryCast result (success): {result}")
            assert isinstance(result, int) and result == 123, "TryCast successful conversion failed."

            fail_literal_to_cast = ibis.literal('abc').cast('string')
            result = fail_literal_to_cast.try_cast('int64').execute()
            print(f"TryCast result (failure): {result}")
            assert result is None, "TryCast failed conversion did not return None."

        def test_unwrap_json_boolean(con):
            """Tests UnwrapJSONBoolean (json_col.boolean_value)."""
            table = con.table('my_table')
            # Assumes json_col has a boolean field, e.g., '{"is_active": true}'
            # For direct access, depends on how ibis maps JSON types.
            # Sometimes direct field access, sometimes via getitem and then cast.
            # Using getitem and then assuming the underlying database can cast
            result = table.json_col['is_active'].cast(ibis.boolean).execute()
            print(f"UnwrapJSONBoolean result: {result}")
            assert isinstance(result, bool), "UnwrapJSONBoolean did not return a boolean."

        def test_unwrap_json_float64(con):
            """Tests UnwrapJSONFloat64 (json_col.float_value)."""
            table = con.table('my_table')
            # Assumes json_col has a float field, e.g., '{"temp": 98.6}'
            result = table.json_col['temp'].cast(ibis.float64).execute()
            print(f"UnwrapJSONFloat64 result: {result}")
            assert isinstance(result, float), "UnwrapJSONFloat64 did not return a float."

        def test_unwrap_json_int64(con):
            """Tests UnwrapJSONInt64 (json_col.int_value)."""
            table = con.table('my_table')
            # Assumes json_col has an int field, e.g., '{"count": 100}'
            result = table.json_col['count'].cast(ibis.int64).execute()
            print(f"UnwrapJSONInt64 result: {result}")
            assert isinstance(result, int), "UnwrapJSONInt64 did not return an integer."

        def test_unwrap_json_string(con):
            """Tests UnwrapJSONString (json_col.string_value)."""
            table = con.table('my_table')
            # Assumes json_col has a string field, e.g., '{"name": "Alice"}'
            result = table.json_col['name'].cast(ibis.string).execute()
            print(f"UnwrapJSONString result: {result}")
            assert isinstance(result, str), "UnwrapJSONString did not return a string."


        # --- Run the tests ---
        tester.run_test("Approximate Count Distinct", test_approx_count_distinct)
        tester.run_test("Approximate Median", test_approx_median)
        tester.run_test("Approximate Multi Quantile", test_approx_multi_quantile)
        tester.run_test("Approximate Quantile", test_approx_quantile)
        tester.run_test("ArgMax", test_arg_max)
        tester.run_test("ArgMin", test_arg_min)
        tester.run_test("Array All", test_array_all)
        tester.run_test("Array Any", test_array_any)
        tester.run_test("Array Collect", test_array_collect)
        tester.run_test("Array Concat", test_array_concat)
        tester.run_test("Array Contains", test_array_contains)
        tester.run_test("Array Distinct", test_array_distinct)
        tester.run_test("Array Filter", test_array_filter)
        tester.run_test("Array Index", test_array_index)
        tester.run_test("Array Intersect", test_array_intersect)
        tester.run_test("Array Map", test_array_map)
        tester.run_test("Array Max", test_array_max)
        tester.run_test("Array Mean", test_array_mean)
        tester.run_test("Array Min", test_array_min)
        tester.run_test("Array Mode", test_array_mode)
        tester.run_test("Array Position", test_array_position)
        tester.run_test("Array Repeat", test_array_repeat)
        tester.run_test("Array Slice", test_array_slice)
        tester.run_test("Array Sort", test_array_sort)
        tester.run_test("Array String Join", test_array_string_join)
        tester.run_test("Array Sum", test_array_sum)
        tester.run_test("Array Union", test_array_union)
        tester.run_test("Cast", test_cast)
        tester.run_test("Correlation", test_correlation)
        tester.run_test("Count Distinct Star", test_count_distinct_star)
        tester.run_test("Date From YMD", test_date_from_ymd)
        tester.run_test("Day Of Week Index", test_day_of_week_index)
        tester.run_test("Day Of Week Name", test_day_of_week_name)
        tester.run_test("Ends With", test_ends_with)
        tester.run_test("Extract Day Of Year", test_extract_day_of_year)
        tester.run_test("Extract Epoch Seconds", test_extract_epoch_seconds)
        tester.run_test("Extract Iso Year", test_extract_iso_year)
        tester.run_test("Extract Microsecond", test_extract_microsecond)
        tester.run_test("Extract Millisecond", test_extract_millisecond)
        tester.run_test("Extract Second", test_extract_second)
        tester.run_test("Extract Week Of Year", test_extract_week_of_year)
        tester.run_test("Find In Set", test_find_in_set)
        tester.run_test("First", test_first)
        tester.run_test("Hash", test_hash)
        tester.run_test("Integer Range", test_integer_range)
        tester.run_test("Is Inf", test_is_inf)
        tester.run_test("Is NaN", test_is_nan)
        tester.run_test("JSON Get Item", test_json_get_item)
        tester.run_test("Last", test_last)
        tester.run_test("Log", test_log)
        tester.run_test("Log2", test_log2)
        tester.run_test("Map", test_map)
        tester.run_test("Map Get", test_map_get)
        tester.run_test("Map Keys", test_map_keys)
        tester.run_test("Map Length", test_map_length)
        tester.run_test("Map Merge", test_map_merge)
        tester.run_test("Map Values", test_map_values)
        tester.run_test("Median", test_median)
        tester.run_test("Mode", test_mode)
        tester.run_test("Modulus", test_modulus)
        tester.run_test("Multi Quantile", test_multi_quantile)
        tester.run_test("Quantile", test_quantile)
        tester.run_test("Range (Column)", test_range)
        tester.run_test("Regex Extract", test_regex_extract)
        tester.run_test("Round", test_round)
        tester.run_test("String Concat", test_string_concat)
        tester.run_test("String Contains", test_string_contains)
        tester.run_test("String To Time", test_string_to_time)
        tester.run_test("Struct Column", test_struct_column)
        tester.run_test("Struct Field", test_struct_field)
        tester.run_test("Sum", test_sum)
        tester.run_test("Table Unnest", test_table_unnest)
        tester.run_test("Timestamp Bucket", test_timestamp_bucket)
        tester.run_test("Timestamp From YMDHMS", test_timestamp_from_ymdhms)
        tester.run_test("To JSON Array", test_to_json_array)
        tester.run_test("Try Cast", test_try_cast)
        tester.run_test("Unwrap JSON Boolean", test_unwrap_json_boolean)
        tester.run_test("Unwrap JSON Float64", test_unwrap_json_float64)
        tester.run_test("Unwrap JSON Int64", test_unwrap_json_int64)
        tester.run_test("Unwrap JSON String", test_unwrap_json_string)

        tester.summarize_results()
        tester.close()
    else:
        print("Skipping tests due to connection failure.")

