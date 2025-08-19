// nvcc -g -std=c++17 -Xcompiler -fPIC mt_sort.cpp\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include/\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include/python3.11\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib\
 -lpthread -ldl -lutil -lm -lpython3.11

#include <iostream>
#include <vector>
#include <random>
#include <stdexcept>
#include <thread> // Added for multithreading
#include <sstream> // Added for creating thread-specific messages
#include <Python.h>
#include <cuda_runtime.h>

// Macro to check for CUDA errors and report them.
#define CHECK_CUDA(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error at %s:%d - %s\n", __FILE__, __LINE__, cudaGetErrorString(err)); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

// --- Function Prototypes ---
void print_array(const std::string& title, const int* arr, int size);
int do_thing(int thread_id);

/**
 * @brief Prints the contents of an integer array to the console.
 * @param title A title to print before the array contents.
 * @param arr Pointer to the array.
 * @param size The number of elements in the array.
 */
void print_array(const std::string& title, const int* arr, int size) {
    std::cout << title << ": [";
    for (int i = 0; i < size; ++i) {
        std::cout << arr[i] << (i == size - 1 ? "" : ", ");
    }
    std::cout << "]" << std::endl;
}

/**
 * @brief The core workload function executed by each thread.
 *
 * This function handles data initialization, GPU memory management, calling a Python
 * script for sorting, and retrieving the results. It is designed to be
 * thread-safe.
 * @param thread_id A unique identifier for the thread for logging purposes.
 * @return 0 on success, -1 on failure.
 */
int do_thing(int thread_id) {
    // --- Configuration ---
    const int NUM_ARRAYS = 10; // Reduced for clearer multithreaded output
    const int ARRAY_SIZE = 7;
    const char* SCRIPT_NAME = "sort";
    const char* FUNCTION_NAME = thread_id % 2 ? "sort_gpu_arrays" : "max_gpu_arrays";

    // Create a string prefix for all output from this thread for clarity.
    std::stringstream ss;
    ss << "\033[3" << (thread_id % 6 + 1) << "m" // Assign a color to the thread
       << "[Thread " << thread_id << "]\033[m ";
    std::string prefix = ss.str();

    // --- Host Data Structures ---
    std::vector<int*> h_initial_data(NUM_ARRAYS);
    std::vector<int*> h_sorted_data(NUM_ARRAYS);
    std::vector<int*> d_pointers(NUM_ARRAYS);
    std::vector<int*> d_sorted_pointers(NUM_ARRAYS);

    // --- 1. Initialize Host Data and Allocate on GPU ---
    std::cout << prefix << "Initializing data on CPU and allocating on GPU..." << std::endl;
    // Use a thread-local random engine for thread safety and better randomness.
    thread_local std::default_random_engine generator(std::hash<std::thread::id>{}(std::this_thread::get_id()));
    std::uniform_int_distribution<int> distribution(1, 100);

    for (int i = 0; i < NUM_ARRAYS; ++i) {
        h_initial_data[i] = new int[ARRAY_SIZE];
        h_sorted_data[i] = new int[ARRAY_SIZE];
        for (int j = 0; j < ARRAY_SIZE; ++j) {
            h_initial_data[i][j] = distribution(generator);
        }

        // Allocate device memory and copy data to it
        CHECK_CUDA(cudaMalloc(&d_pointers[i], ARRAY_SIZE * sizeof(int)));
        CHECK_CUDA(cudaMemcpy(d_pointers[i], h_initial_data[i], ARRAY_SIZE * sizeof(int), cudaMemcpyHostToDevice));
    }
    std::cout << prefix << "Finished data initialization." << std::endl;


    // --- Python Interaction Section ---
    // Acquire the Global Interpreter Lock (GIL) before interacting with Python.
    // This is crucial for thread safety in a multithreaded C++ application
    // that embeds Python.
    PyGILState_STATE gstate = PyGILState_Ensure();

    // --- 2. Load Python Module and Function ---
    PyObject *pName, *pModule, *pFunc, *pArgs, *pReturnValue, *pList;

    pName = PyUnicode_FromString(SCRIPT_NAME);
    pModule = PyImport_Import(pName);
    Py_DECREF(pName);

    if (pModule == nullptr) {
        PyErr_Print();
        std::cerr << prefix << "Error: Failed to load Python script '"
                  << SCRIPT_NAME << ".py'" << std::endl;
        PyGILState_Release(gstate);
        return -1;
    }

    pFunc = PyObject_GetAttrString(pModule, FUNCTION_NAME);
    if (!pFunc || !PyCallable_Check(pFunc)) {
        if (PyErr_Occurred()) PyErr_Print();
        std::cerr << prefix << "Error: Cannot find function '" << FUNCTION_NAME
                  << "'" << std::endl;
        Py_DECREF(pModule);
        PyGILState_Release(gstate);
        return -1;
    }

    // --- 3. Prepare Arguments and Call Python Function ---
    pList = PyList_New(NUM_ARRAYS);
    for (int i = 0; i < NUM_ARRAYS; ++i) {
        PyObject* pValue = PyLong_FromLongLong(
            reinterpret_cast<long long>(d_pointers[i]));
        if (!pValue) {
            std::cerr << prefix
                      << "Error: Cannot convert pointer to Python long."
                      << std::endl;
            Py_DECREF(pList);
            Py_DECREF(pModule);
            PyGILState_Release(gstate);
            return -1;
        }
        PyList_SetItem(pList, i, pValue); // SetItem steals the reference
    }

    pArgs = PyTuple_New(3);
    PyTuple_SetItem(pArgs, 0, pList);
    PyTuple_SetItem(pArgs, 1, PyLong_FromLong(ARRAY_SIZE));
    PyTuple_SetItem(pArgs, 2, PyUnicode_FromString("int32"));

    std::cout << prefix << "Calling Python function with GPU pointers..." << std::endl;
    pReturnValue = PyObject_CallObject(pFunc, pArgs);
    Py_DECREF(pArgs);

    // --- 4. Process the Return Value from Python ---
    if (pReturnValue == nullptr) {
        PyErr_Print();
        std::cerr << prefix << "Error: Python function call failed.\n";
    } else {
        if (!PyList_Check(pReturnValue) || PyList_Size(pReturnValue) != NUM_ARRAYS) {
            std::cerr << prefix << "Error: Python function did not return a list of the correct size." << std::endl;
        } else {
            std::cout << prefix << "Received pointers to sorted arrays from Python." << std::endl;
            for (int i = 0; i < NUM_ARRAYS; ++i) {
                PyObject* pItem = PyList_GetItem(pReturnValue, i);
                d_sorted_pointers[i] = reinterpret_cast<int*>(PyLong_AsLongLong(pItem));
            }
        }
        Py_DECREF(pReturnValue);
    }

    // --- 5. Cleanup Python Objects ---
    Py_XDECREF(pFunc);
    Py_DECREF(pModule);

    // Release the GIL now that we are done with Python calls.
    PyGILState_Release(gstate);
    // --- End of Python Interaction Section ---


    // --- 6. Copy Sorted Data Back to Host and Verify ---
    std::cout << prefix << "Copying sorted data from GPU to CPU for verification..." << std::endl;
    for (int i = 0; i < NUM_ARRAYS; ++i) {
        if (d_sorted_pointers[i] != nullptr) {
            CHECK_CUDA(cudaMemcpy(h_sorted_data[i], d_sorted_pointers[i], ARRAY_SIZE * sizeof(int), cudaMemcpyDeviceToHost));
            // Optional: Print arrays to verify. Can be noisy with many threads.
            // print_array(prefix + "Original Array " + std::to_string(i), h_initial_data[i], ARRAY_SIZE);
            // print_array(prefix + "Sorted Array " + std::to_string(i), h_sorted_data[i], ARRAY_SIZE);
        }
    }

    // --- 7. Cleanup C++/CUDA Resources ---
    std::cout << prefix << "Cleaning up resources..." << std::endl;
    for (int i = 0; i < NUM_ARRAYS; ++i) {
        CHECK_CUDA(cudaFree(d_pointers[i]));
        // Note: The Python script is responsible for freeing the sorted pointers.
        delete[] h_initial_data[i];
        delete[] h_sorted_data[i];
    }

    std::cout << prefix << "\033[32;1mExecution finished successfully.\033[m" << std::endl;
    return 0;
}

int main() {
    const int NUM_THREADS = 3;
    std::vector<std::thread> threads;

    std::cout << "\033[34;1m[Main] Initializing Python interpreter for multithreading...\033[m" << std::endl;
    // Initialize Python and release the GIL to allow other threads to acquire it.
    Py_Initialize();
    PyEval_InitThreads(); // Crucial for multithreading
    PyEval_SaveThread();  // Releases the GIL

    // Add current directory to Python's system path to find the script
    // This needs to be done from a thread that holds the GIL.
    PyGILState_STATE gstate = PyGILState_Ensure();
    PyObject* py_syspath = PySys_GetObject("path");
    PyList_Append(py_syspath, PyUnicode_FromString("."));
    PyGILState_Release(gstate);


    std::cout << "\033[34;1m[Main] Launching " << NUM_THREADS << " threads...\033[m" << std::endl;
    for (int i = 0; i < NUM_THREADS; ++i) {
        // Launch a thread, calling do_thing with a unique ID
        threads.emplace_back(do_thing, i + 1);
    }

    std::cout << "\033[34;1m[Main] Waiting for all threads to complete...\033[m" << std::endl;
    for (auto& t : threads) {
        if (t.joinable()) {
            t.join(); // Wait for each thread to finish
        }
    }

    // Re-acquire the GIL to finalize the interpreter safely.
    gstate = PyGILState_Ensure();
    std::cout << "\033[34;1m[Main] All threads finished. Finalizing Python interpreter.\033[m" << std::endl;
    if (Py_FinalizeEx() < 0) {
        return 120;
    }

    std::cout << "\033[32;1m[Main] Program finished.\033[m" << std::endl;
    return 0;
}