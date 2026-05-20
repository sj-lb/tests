#include "plate.hpp"

namespace iron_dome_game
{
Plate::Plate(Pos pos_, Velocity v_)
  : trajectory(Trajectory{.initial_state = InitialState{
    .pos = pos_,
    .v = v_}}) {}


//============================================================================//

std::optional<BoundingBox> Plate::boundingBox() 
{
    Pos pos = this->pos();
    return BoundingBox{
        .lower_left = pos,
        .upper_right = pos + Pos{.x = 2, .y = 2}
    };
}

const std::vector<std::string> Plate::shape() const
{
    static const std::vector<std::string> shape = {
        "/^\\",
        "| |",
       "\\_/"
    };
    return shape;
}
}