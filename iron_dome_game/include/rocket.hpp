#pragma once

#include "entity.hpp"

namespace iron_dome_game
{

struct Rocket : public Entity
{
    Rocket(float angle, float speed);
    ~Rocket() = default;

    EntityType type() override { return EntityType::ROCKET; }

    void drawOnGrid(Grid &grid) override;

    bool isStatic() override { return false; }

    // Check if rocket has expired (gone off screen or too old)
    bool isExpired() const;
    
    // Maximum lifetime in seconds
    static constexpr float MAX_LIFETIME = 10.0f;
};

}

