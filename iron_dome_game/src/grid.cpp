#include <iostream>

#include "grid.hpp"
#include "entity.hpp"
#include "rocket.hpp"
#include "plate.hpp"

namespace iron_dome_game
{

std::vector<std::string> grid_template(size_t rows, size_t columns)
{
    std::vector<std::string> grid_template(rows, std::string(columns, ' '));
    std::fill(grid_template[0].begin(), grid_template[0].end(), '_');
    for (size_t i = 1; i < rows; ++i)
        grid_template[i] += '\n';
    return grid_template;
}

Grid::Grid(size_t rows, size_t columns)
: m_grid_template(grid_template(rows, columns)), m_grid(m_grid_template) {}

//============================================================================//

void Grid::addEntity(std::unique_ptr<Entity> entity) 
{
    static unsigned int id = 0;

    std::lock_guard<std::mutex> lock(m_mutex);
    m_entities[id++] = std::move(entity);
}

void Grid::removeEntity(unsigned int id) 
{
    std::lock_guard<std::mutex> lock(m_mutex);
    m_entities.erase(id);
}

void Grid::draw() 
{
    for (int i = rows() - 1; i >= 0; --i)
        std::cout << m_grid[i];
    std::cout << std::endl; // only flushed here
}

void Grid::refresh() 
{
    m_grid.clear();
    m_grid = m_grid_template;

    for (const auto& [id, entity] : m_entities)
        draw(entity);
}

void Grid::draw(const std::unique_ptr<Entity>& entity) 
{
    auto shape = entity->shape();
    for (size_t i = 0; i < shape.size(); ++i)
    {
        int row = entity->pos().y + shape.size() - 1 - i;
        int col = entity->pos().x;

        if (row >= 0 && row < rows() && col + entity->width() > 0 && col < columns())
        {
            uint16_t len = std::min(
                static_cast<uint16_t>(shape[i].size()),
                static_cast<uint16_t>(columns() - col));
            m_grid[row].replace(col, len, shape[i].substr(std::max(0, -col), len));
        }
    }
}

bool Grid::clearExpiredAndCheckMisses()
{
    bool has_misses = false;
    std::vector<unsigned int> expired_ids;
    for (const auto& [id, entity] : m_entities)
    {
        auto pos = entity->pos();
        bool is_rocket = dynamic_cast<Rocket*>(entity.get()) != nullptr;

        if (pos.y > rows() && is_rocket) {
            has_misses = true;
            expired_ids.push_back(id);
        }
        else if (pos.x < entity->width() || pos.x >= columns() || pos.y < 0) {
            has_misses |= is_rocket;
            expired_ids.push_back(id);
        }
    }

    for (auto id : expired_ids)
        removeEntity(id);

    return has_misses;
}

std::vector<std::pair<unsigned int, std::optional<unsigned int>>> Grid::checkHits()
{
    std::vector<std::pair<unsigned int, std::optional<unsigned int>>> hits;
    std::vector<std::vector<unsigned int>> hit_map(
        rows(),
        std::vector<unsigned int>(columns(), 0));

    for (const auto& [id, entity] : m_entities)
    {
        auto hit_box = entity->boundingBox();
        if (!hit_box.has_value()) continue;

        for (int row = hit_box->lower_left.y; row <= hit_box->upper_right.y; ++row)
        {
            for (int col = hit_box->lower_left.x; col <= hit_box->upper_right.x; ++col)
            {
                if (row < rows() && col >= 0 && col < columns())
                {
                    if (hit_map[row][col] == 0)
                        hit_map[row][col] = id;
                    else
                    {
                        Plate* plate;
                        if (dynamic_cast<Plate*>(entity.get()) != nullptr)
                            plate = dynamic_cast<Plate*>(entity.get());
                        else
                            plate = dynamic_cast<Plate*>(m_entities[hit_map[row][col]].get());
                        plate->setAirTime();
                        hits.emplace_back(id, hit_map[row][col]);
                    }
                }
            }
        }
    }

    return hits;
}

} // namespace iron_dome_game