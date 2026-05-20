#include <iostream>
#include "grid.hpp"
#include "entity.hpp"

namespace iron_dome_game
{

Grid::Grid(size_t rows, size_t columns) : m_grid(rows, std::string(columns, ' '))
{
    std::fill(m_grid[0].begin(), m_grid[0].end(), '_');
    for (int i = 1; i < rows; ++i)
        m_grid[i] += '\n';
}

//============================================================================//

void Grid::draw() 
{
    for (int i = rows() - 1; i >= 0; --i)
        std::cout << m_grid[i];
    std::cout << std::endl;
}

void Grid::refresh() 
{
    std::fill(m_grid[0].begin(), m_grid[0].end(), '_');
    for (int i = 1; i < rows(); ++i)
        std::fill(m_grid[i].begin(), m_grid[i].end() - 1, ' ');

    for (const auto& entity : m_entities)
        draw(entity);
}

void Grid::draw(const std::unique_ptr<Entity>& entity) 
{
    auto shape = entity->shape();
    for (int i = 0; i < shape.size(); ++i)
    {
        auto row = entity->pos().y + shape.size() - 1 - i;
        auto col = entity->pos().x;

        if (row >= 0 && row < rows() && col >= 0 && col < columns())
        {
            uint16_t len = std::min(
                static_cast<uint16_t>(shape[i].size()),
                static_cast<uint16_t>(columns() - col));
            m_grid[row].replace(col, len, shape[i].substr(0, len));
        }
    }
}

//============================================================================//

uint16_t Grid::checkHits() 
{
    uint16_t hits = 0;
    // TODO
    return hits;
}

//============================================================================//

bool Grid::intersects(const std::unique_ptr<Entity>& first, const std::unique_ptr<Entity>& second) 
{
    return true;
    // TODO
}

}