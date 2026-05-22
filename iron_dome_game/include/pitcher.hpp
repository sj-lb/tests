#pragma once

#include "entity.hpp"

namespace iron_dome_game
{
class Pitcher : public Entity
{
public:
    Pitcher(Pos pos) : m_pos(pos) {}

    const std::vector<std::string> shape() const override;
    Pos pos() override { return m_pos; }
    uint16_t width() const override { return 5;}

private:
    const Pos m_pos;
};

} // namespace iron_dome_game