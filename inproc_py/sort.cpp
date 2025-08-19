// nvcc -g -std=c++17 -Xcompiler -fPIC sort.cpp\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include/\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include/python3.11\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib\
 -lpthread -ldl -lutil -lm -lpython3.11

#include <iostream>
#include <vector>
#include <random>
#include <stdexcept>
#include <Python.h>
#include <cuda_runtime.h>

#define CHECK_CUDA(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA Error at %s:%d - %s\n", __FILE__, __LINE__, cudaGetErrorString(err)); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

// Function to print an array for verification
void print_array(const std::string& title, const int* arr, int size) {
    std::cout << title << ": [";
    for (int i = 0; i < size; ++i) {
        std::cout << arr[i] << (i == size - 1 ? "" : ", ");
    }
    std::cout << "]" << std::endl;
}

int do_thing() {
    // --- Configuration ---
    const int NUM_ARRAYS = 1'048'576;
    const int ARRAY_SIZE = 7;
    const char* SCRIPT_NAME = "sort";
    const char* FUNCTION_NAME = "sort_gpu_arrays";

    // --- Host Data Structures ---
    std::vector<int*> h_initial_data(NUM_ARRAYS);
    std::vector<int*> h_sorted_data(NUM_ARRAYS);
    std::vector<int*> d_pointers(NUM_ARRAYS);
    std::vector<int*> d_sorted_pointers(NUM_ARRAYS);

    // --- 1. Initialize Host Data and Allocate on GPU ---
    std::cout << "[C++] Initializing data on CPU and allocating on GPU..." << std::endl;
    std::default_random_engine generator;
    std::uniform_int_distribution<int> distribution(1, 100);

    for (int i = 0; i < NUM_ARRAYS; ++i) {
        // Allocate and fill host memory
        h_initial_data[i] = new int[ARRAY_SIZE];
        h_sorted_data[i] = new int[ARRAY_SIZE];
        for (int j = 0; j < ARRAY_SIZE; ++j) {
            h_initial_data[i][j] = distribution(generator);
        }
        print_array("Original Array " + std::to_string(i), h_initial_data[i], ARRAY_SIZE);

        // Allocate device memory and copy data to it
        CHECK_CUDA(cudaMalloc(&d_pointers[i], ARRAY_SIZE * sizeof(int)));
        CHECK_CUDA(cudaMemcpy(d_pointers[i], h_initial_data[i], ARRAY_SIZE * sizeof(int), cudaMemcpyHostToDevice));
    }

    if (!Py_IsInitialized()) {
        std::cout << "\n\033[34;1m[C++] Initializing Python interpreter...\033[m\n";
        Py_Initialize();
    }

    // Add current directory to Python's system path to find the script
    PyObject* py_syspath = PySys_GetObject("path");
    PyList_Append(py_syspath, PyUnicode_FromString("."));

    // --- 3. Load Python Module and Function ---
    PyObject *pName, *pModule, *pFunc, *pArgs, *pReturnValue, *pList;

    pName = PyUnicode_FromString(SCRIPT_NAME);
    pModule = PyImport_Import(pName);
    Py_DECREF(pName);

    if (pModule == nullptr) {
        PyErr_Print();
        std::cerr << "Error: Failed to load Python script '" << SCRIPT_NAME << ".py'" << std::endl;
        return -1;
    }

    pFunc = PyObject_GetAttrString(pModule, FUNCTION_NAME);
    if (!pFunc || !PyCallable_Check(pFunc)) {
        if (PyErr_Occurred()) PyErr_Print();
        std::cerr << "Error: Cannot find function '" << FUNCTION_NAME << "'" << std::endl;
        Py_DECREF(pModule);
        return -1;
    }
    std::cout << "[C++] Successfully loaded Python function '" << FUNCTION_NAME << "'." << std::endl;


    // --- 4. Prepare Arguments and Call Python Function ---
    // Create a Python list to hold the GPU pointers
    pList = PyList_New(NUM_ARRAYS);
    for (int i = 0; i < NUM_ARRAYS; ++i) {
        // Convert the pointer (address) to a Python long integer
        PyObject* pValue = PyLong_FromLongLong(reinterpret_cast<long long>(d_pointers[i]));
        if (!pValue) {
            std::cerr << "Error: Cannot convert pointer to Python long." << std::endl;
            Py_DECREF(pList);
            Py_DECREF(pModule);
            return -1;
        }
        PyList_SetItem(pList, i, pValue); // Note: SetItem steals the reference
    }

    // Create a tuple for the function arguments (pointers_list, size, dtype)
    pArgs = PyTuple_New(3);
    PyTuple_SetItem(pArgs, 0, pList); // Steals reference
    PyTuple_SetItem(pArgs, 1, PyLong_FromLong(ARRAY_SIZE));
    PyTuple_SetItem(pArgs, 2, PyUnicode_FromString("int32"));

    std::cout << "[C++] Calling Python function with GPU pointers..." << std::endl;
    pReturnValue = PyObject_CallObject(pFunc, pArgs);
    Py_DECREF(pArgs); // pList is part of pArgs, so it's decref'd too

    // --- 5. Process the Return Value from Python ---
    if (pReturnValue == nullptr) {
        PyErr_Print();
        std::cerr << "Error: Python function call failed." << std::endl;
        Py_DECREF(pFunc);
        Py_DECREF(pModule);
        return -1;
    }

    if (!PyList_Check(pReturnValue) || PyList_Size(pReturnValue) != NUM_ARRAYS) {
        std::cerr << "Error: Python function did not return a list of the correct size." << std::endl;
    } else {
        std::cout << "\n[C++] Received pointers to sorted arrays from Python." << std::endl;
        for (int i = 0; i < NUM_ARRAYS; ++i) {
            PyObject* pItem = PyList_GetItem(pReturnValue, i);
            d_sorted_pointers[i] = reinterpret_cast<int*>(PyLong_AsLongLong(pItem));
        }
    }
    Py_DECREF(pReturnValue);


    // --- 6. Copy Sorted Data Back to Host and Print ---
    std::cout << "[C++] Copying sorted data from GPU to CPU for verification..." << std::endl;
    for (int i = 0; i < NUM_ARRAYS; ++i) {
        if (d_sorted_pointers[i] != nullptr) {
            CHECK_CUDA(cudaMemcpy(h_sorted_data[i], d_sorted_pointers[i], ARRAY_SIZE * sizeof(int), cudaMemcpyDeviceToHost));
            print_array("Sorted Array " + std::to_string(i), h_sorted_data[i], ARRAY_SIZE);
        }
    }

    // --- 7. Cleanup ---
    std::cout << "\n[C++] Cleaning up resources..." << std::endl;
    Py_XDECREF(pFunc);
    Py_DECREF(pModule);

    for (int i = 0; i < NUM_ARRAYS; ++i) {
        CHECK_CUDA(cudaFree(d_pointers[i]));
        delete[] h_initial_data[i];
        delete[] h_sorted_data[i];
    }
    
    std::cout << "[C++] Execution finished successfully." << std::endl;
    return 0;
}

int main() {
    for (int i = 0; i < 3; ++i) {
        do_thing();
        std::cout << "\033[32;1mDID THE THING \033[33m" << i + 1
                  << "\033[32m TIMES\033[m\n";
    }

    if (Py_FinalizeEx() < 0)
        return 120;
    return 0;
}