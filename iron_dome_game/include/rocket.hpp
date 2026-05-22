#pragma once

#include "entity.hpp"

namespace iron_dome_game
{

class Rocket : public Entity
{
public:
    Rocket(Pos pos,float angle, float speed);
    ~Rocket() = default;

    const std::vector<std::string> shape() const override;
    std::optional<BoundingBox> boundingBox() override;
    Pos pos() override { return trajectory.calculatePosition(); }
    uint16_t width() const override { return 1; }

    Pos pos0() { return trajectory.initial_state.pos; }
private:
    Trajectory trajectory;
};

} // namespace iron_dome_game
