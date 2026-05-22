#pragma once

#include "entity.hpp"

namespace iron_dome_game
{

class Dome : public Entity
{
public:
    Dome(Pos pos) : m_pos(pos) {}

    const std::vector<std::string> shape() const override;
    uint16_t width() const override {return 7;}
    Pos pos() override { return m_pos; }

private:
    Pos m_pos;
};

} // namespace iron_dome_game