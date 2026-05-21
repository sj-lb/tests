#pragma once

#include <functional>
#include <map>
#include <memory>
#include <mutex>

#include "config.hpp"
#include "entity.hpp"

namespace iron_dome_game
{
class Grid
{
public:
    Grid(size_t rows = GRID_ROWS, size_t columns = GRID_COLUMNS);
    ~Grid() = default;

    void draw();
    void refresh();

    uint16_t rows() { return m_grid.size(); }
    uint16_t columns() { return m_grid.empty() ? 0 : m_grid[0].size(); }

    void draw(const std::unique_ptr<Entity>& entity);

    void addEntity(std::unique_ptr<Entity> entity);
    void removeEntity(unsigned int id);
    std::unique_ptr<Entity> getEntity(unsigned int id) { return std::move(m_entities[id]); }
    std::vector<std::pair<unsigned int, std::optional<unsigned int>>> checkHits();

private:
    std::vector<std::string> m_grid;

    mutable std::mutex m_mutex;
    std::map<unsigned int, std::unique_ptr<Entity>> m_entities;
};
}