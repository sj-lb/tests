#include <iostream>
#include <algorithm>
#include <vector>
#include <queue>
#include <cmath>

std::string str(const std::vector<std::pair<int, int>>& v) {
    std::string s = "[";
    for (const auto& p : v)
        s += "{" + std::to_string(p.first) + ", " + std::to_string(p.second) + "}, ";
    return s.substr(0, s.size() - 2) + "]";
}

std::vector<std::pair<int, int>> k_closest(std::vector<std::pair<int, int>>& points, int k) {
    k = std::min(k, static_cast<int>(points.size()));
    auto dist = [](const std::pair<int, int>& a, const std::pair<int, int>& b) {
        return a.first * a.first + a.second * a.second > b.first * b.first + b.second * b.second;};
    std::priority_queue<std::pair<int, int>,
                        std::vector<std::pair<int, int>>,
                        decltype(dist)>
                        pq{dist, points}; // O(n) using make_heap, but copies everything
                                          // alternatively fill max heap with k elements in O(n log k)

    std::vector<std::pair<int, int>> res;
    res.reserve(k);
    while (k--) {
        res.emplace_back(pq.top());
        pq.pop();
    }
    return res;
}

int main() {
    std::vector<std::pair<int, int>> pts1{{1,5}};
    std::vector<std::pair<int, int>> pts10{
        {1,5}, {-2,4}, {3,3}, {5,1}, {-2,3}, {-1,-1}, {2,2}, {4,4}, {-3,-3}, {6,6}};
    std::cout << str(k_closest(pts1, 2)) << std::endl;
    std::cout << str(k_closest(pts10, 2)) << std::endl;
    std::cout << str(k_closest(pts10, 5)) << std::endl;
    return 0;
}