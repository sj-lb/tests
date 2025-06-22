#include <iostream>
#include <cstdint>
#include <cstddef>
#include <vector>

// Typedefs for clarity
using sq_datetime = int64_t;
using date = int64_t;
using cuda_error_type = int;  // Dummy error type

#define UNUSED_PARAMETER(x) (void)(x)

// ---- Function Definitions ----

sq_datetime addMilliseconds(sq_datetime dt, int64_t ms, cuda_error_type* err) {
    UNUSED_PARAMETER(err);
    return dt + ms;
}

sq_datetime addDaysdt2dt(sq_datetime dt, int64_t i, cuda_error_type* err) {
    int hour = static_cast<int>(dt & 0x00000000FFFFFFFF);
    int64_t day = static_cast<int64_t>((dt & 0xFFFFFFFF00000000) >> 32);
    day += i;
    UNUSED_PARAMETER(err);  // Placeholder for overflow check
    return static_cast<sq_datetime>(hour + (day << 32));
}

sq_datetime addMillisecondsdt2dt(sq_datetime dt, int64_t i, cuda_error_type* err) {
    sq_datetime tm = addMilliseconds(dt, (i % 86400000), err);
    if (i >= 86400000 || i <= -86400000) {
        tm = addDaysdt2dt(tm, (i / 86400000), err);
    }
    return tm;
}

sq_datetime from_unixtsms(int64_t unixts, cuda_error_type* err) {
    return addMillisecondsdt2dt(3090091530518528LL, unixts, err);
}

void sqfy_datetime_cpu(int64_t* dates, size_t N) {
    for (size_t i = 0; i < N; ++i) {
        dates[i] = static_cast<int64_t>(from_unixtsms(dates[i], nullptr));
    }
}

// ---- Main ----

int main() {
    std::vector<int64_t> timestamps = {
     1672531200123456789,
1704067200123456789,
1735689600123456789,
       
    };

    std::cout << "Original timestamps:\n";
    for (auto ts : timestamps) {
        std::cout << ts << " ";
    }
    std::cout << "\n";

    sqfy_datetime_cpu(timestamps.data(), timestamps.size());

    std::cout << "Transformed sq_datetime:\n";
    for (auto ts : timestamps) {
        std::cout << ts << " ";
    }
    std::cout << "\n";

    return 0;
}

// g++ -std=c++17 -fsanitize=address,undefined -fno-omit-frame-pointer -g -o razi.out razi.cpp