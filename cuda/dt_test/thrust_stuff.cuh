#include <thrust/sequence.h>
#include <thrust/device_ptr.h>
#include <thrust/extrema.h>

void thrust_sqfy_dt(int64_t* dst, const int64_t* std_dt, size_t N);