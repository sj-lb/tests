#pragma once

#include "entity.hpp"

namespace iron_dome_game
{
class Plate : public Entity
{
public:
    Plate(Pos pos, Velocity v);

    virtual const std::vector<std::string> shape() const override;
    virtual std::optional<BoundingBox> boundingBox() override;
    virtual Pos pos() override { return trajectory.calculatePosition(); }

    Trajectory trajectory;
};

}