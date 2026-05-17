#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>

static const int directions[8][2]{{-1,-1},{-1,0},{-1,1},{0,-1},{0,1},{1,-1},{1,0},{1,1}};

std::string str(const std::vector<unsigned int>& v) {
    std::string s = "[";
    for (int x : v)
        s += std::to_string(x) + ", ";
    return s.substr(0, s.size() - 2) + "]";
}

int bfs(std::vector<std::vector<int>>& grid) {
    int n = grid.size();
    if (grid[0][0] == 1 || grid[n-1][n-1] == 1) return -1;
    
    std::queue<std::pair<int, int>> q;
    q.push({0, 0});
    grid[0][0] = 1; // Mark as visited by setting distance in-place
    
    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();
        
        if (r == n - 1 && c == n - 1) return grid[r][c];
        
        for (auto& dir : directions) {
            int nr = r + dir[0], nc = c + dir[1];
            if (nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0) {
                q.push({nr, nc});
                grid[nr][nc] = grid[r][c] + 1; // Store distance
            }
        }
    }
    return -1;
}

int a_star(std::vector<std::vector<int>>& grid) {
    int n = grid.size(), n_ = n - 1;

    if (grid[0][0] == 1 || grid[n-1][n-1] == 1) return -1;

    std::vector<std::vector<unsigned int>> g_score(n, std::vector<unsigned int>(n, -1u));
    g_score[0][0] = 1;

    std::priority_queue<std::vector<int>, std::vector<std::vector<int>>, std::greater<>> pq;
    
    auto heuristic = [n_](int r, int c) {
        return std::max(abs(n_ - r), abs(n_ - c));};

    pq.push({1 + heuristic(0, 0), 0, 0});

    while (!pq.empty()) {
        std::cout << "g_score:" << std::endl;
        for (auto bla : g_score)
            std::cout << str(bla) << std::endl;
        auto curr = pq.top();
        pq.pop();
        int f = curr[0], r = curr[1], c = curr[2];
        std::cout << "f: " << f << ", r: " << r << ", c: " << c << std::endl;

        if (r == n_ && c == n_) return f;

        for (auto& dir : directions) {
            int nr = r + dir[0], nc = c + dir[1];
            
            if (nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0) {
                int tentative_g = g_score[r][c] + 1;
                
                if (tentative_g < g_score[nr][nc]) {
                    g_score[nr][nc] = tentative_g;
                    pq.push({tentative_g + heuristic(nr, nc), nr, nc});
                }
            }
        }
    }
    return -1;
}

int bibfs(std::vector<std::vector<int>>& grid) {
    int n = grid.size();
    if (grid[0][0] == 1 || grid[n-1][n-1] == 1) return -1;
    if (n == 1) return 1;

    std::vector<std::vector<int>> dist_fwd(n, std::vector<int>(n, 0));
    std::vector<std::vector<int>> dist_bwd(n, std::vector<int>(n, 0));

    std::queue<std::pair<int, int>> q_fwd, q_bwd;

    q_fwd.push({0, 0});
    dist_fwd[0][0] = 1;

    q_bwd.push({n-1, n-1});
    dist_bwd[n-1][n-1] = 1;

    while (!q_fwd.empty() && !q_bwd.empty()) {
        int sz_fwd = q_fwd.size();
        for (int i = 0; i < sz_fwd; ++i) {
            auto [r, c] = q_fwd.front();
            q_fwd.pop();

            for (auto& dir : directions) {
                int nr = r + dir[0], nc = c + dir[1];
                if (nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0 && dist_fwd[nr][nc] == 0) {
                    dist_fwd[nr][nc] = dist_fwd[r][c] + 1;
                    q_fwd.push({nr, nc});
                    
                    if (dist_bwd[nr][nc] > 0) return dist_fwd[nr][nc] + dist_bwd[nr][nc] - 1;
                }
            }
        }

        int sz_bwd = q_bwd.size();
        for (int i = 0; i < sz_bwd; ++i) {
            auto [r, c] = q_bwd.front();
            q_bwd.pop();

            for (auto& dir : directions) {
                int nr = r + dir[0], nc = c + dir[1];
                if (nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0 && dist_bwd[nr][nc] == 0) {
                    dist_bwd[nr][nc] = dist_bwd[r][c] + 1;
                    q_bwd.push({nr, nc});
                    
                    if (dist_fwd[nr][nc] > 0) return dist_fwd[nr][nc] + dist_bwd[nr][nc] - 1;
                }
            }
        }
    }
    return -1;
}

int shortestPathBinaryMatrix(std::vector<std::vector<int>>& grid) {return bibfs(grid);}

int main() {
    std::vector<std::vector<int>> grid{
        {0, 1, 1, 0, 1, 1},
        {0, 1, 0, 1, 0, 1},
        {0, 1, 0, 1, 0, 1},
        {0, 1, 0, 1, 0, 1},
        {0, 1, 0, 1, 0, 1},
        {1, 0, 1, 1, 1, 0}};
    std::vector<std::vector<int>> g0{{0}};

    std::cout << shortestPathBinaryMatrix(grid) << std::endl;
    std::cout << shortestPathBinaryMatrix(g0) << std::endl;
    return 0;
}