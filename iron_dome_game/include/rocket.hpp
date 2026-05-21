#pragma once

#include "entity.hpp"

namespace iron_dome_game
{

class Rocket : public Entity
{
public:
    Rocket(Pos pos,float angle, float speed);
    ~Rocket() = default;

    virtual const std::vector<std::string> shape() const override;
    virtual std::optional<BoundingBox> boundingBox() override;

    virtual Pos pos() override { return trajectory.calculatePosition(); };
private:
    Trajectory trajectory;
};

} // namespace iron_dome_game
