// nvcc -g -c thrust_stuff.cu --extended-lambda\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include

#include "thrust_stuff.cuh"

static constexpr __device__ size_t sq_epoch_time = 3'090'091'530'518'528;
static constexpr __device__ int ms_in_day = 86'400'000;
static constexpr __device__ size_t date_mask = 0xFFFFFFFF00000000;
static constexpr __device__ size_t ms_mask  =  0x00000000FFFFFFFF;

typedef struct {
    int time;
    int date;
} sq_dt;
typedef union {
    int64_t l;
    sq_dt dt;
} dt_u;

inline __device__ int64_t do_it(int64_t i){ // incomplete!
    dt_u dt;
    dt.l = sq_epoch_time;

    dt.dt.time += i;
    if (dt.dt.time >= ms_in_day) {
        int rem = dt.dt.time / ms_in_day;
        dt.dt.time %= ms_in_day;
    }

    return dt.l;
}
void thrust_sqfy_dt(int64_t* dst, const int64_t* std_dt, size_t N) {
    thrust::for_each_n(
        thrust::counting_iterator<size_t>(0),
        N,
        [std_dt, dst] __device__(size_t i) {
            dst[i] = do_it(std_dt[i]);});
}