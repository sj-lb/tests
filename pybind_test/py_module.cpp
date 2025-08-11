// g++ -g -Wall -shared -std=c++11 -fPIC\
 -isystem /usr/local/sqream-prerequisites/package-install/python-3.11.7-11.1.0/include/python3.11\
 -isystem /home/johnny/.local/lib/python3.11/site-packages/pybind11/include\
 py_module.cpp\
 -o py_module`python3-config --extension-suffix`

#include <pybind11/pybind11.h>
#include <iostream>

int add(int i, int j) {
    std::cout << "adding " << i << " and " << j << ": " << i + j << std::endl;
    return i + j;
}

PYBIND11_MODULE(a, m) {
    m.doc() = "pybind11 example plugin"; // optional module docstring

    // Expose the 'add' function
    m.def("add", &add, "A function that adds two numbers");
}