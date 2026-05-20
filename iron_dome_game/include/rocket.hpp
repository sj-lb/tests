#pragma once

#include "entity.hpp"

namespace iron_dome_game
{

struct Rocket : public Entity
{
    Rocket(float angle, float speed);
    ~Rocket() = default;

    virtual const std::vector<std::string> shape() const override;
    virtual std::optional<BoundingBox> boundingBox() override;

    // Check if rocket has expired (gone off screen or too old)
    bool isExpired() const;
    
    // Maximum lifetime in seconds
    static constexpr float MAX_LIFETIME = 10.0f;
};

}

