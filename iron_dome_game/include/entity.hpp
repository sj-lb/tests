#pragma once
#include <vector>
#include <string>
#include <optional>

#include "config.hpp"
#include "trajectory.hpp"
namespace iron_dome_game
{
struct BoundingBox
{
    Pos lower_left;
    Pos upper_right;
};

class Entity
{
public:
    virtual ~Entity() = 0;
    virtual Pos pos() = 0;

    virtual std::optional<BoundingBox> boundingBox() { return std::nullopt; }
    virtual const std::vector<std::string> shape() const = 0;
};
}