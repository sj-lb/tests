#include <iostream>
#include <vector>
#include <string>

std::string str(const std::vector<int>& v) {
    std::string s = "[";
    for (int x : v)
        s += std::to_string(x) + ", ";
    return s.substr(0, s.size() - 2) + "]";
}

int sub_series(std::vector<int> v) {
    std::vector<int> dp;
    for (int x : v) {
        auto it = std::lower_bound(dp.begin(), dp.end(), x);
        if (it == dp.end()) dp.push_back(x);
        else *it = x;
    }
    return dp.size();
}

int main() {
    std::cout << sub_series({}) << std::endl;
    std::cout << sub_series({3}) << std::endl;
    std::cout << sub_series({10,9,2,5,3,7,101,18}) << std::endl;
    std::cout << sub_series({10,9,2,5,3,7,101,18,4,5,6}) << std::endl;
    return 0;
}