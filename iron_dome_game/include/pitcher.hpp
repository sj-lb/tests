#pragma once

#include "entity.hpp"

namespace iron_dome_game
{
class Pitcher : public Entity
{
public:
    Pitcher(Pos pos) : m_pos(pos) {}

    virtual const std::vector<std::string> shape() const override;
    virtual Pos pos() override { return m_pos; }

private:
    const Pos m_pos;
};

} // namespace iron_dome_game