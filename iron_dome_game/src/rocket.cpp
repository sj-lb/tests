#include "rocket.hpp"

namespace iron_dome_game
{

Rocket::Rocket(Pos pos, float angle, float speed)
  : trajectory(Trajectory{.initial_state = InitialState{
    .pos = pos,
    .v = Pos{
        static_cast<int16_t>(round(speed * cos(toRad(angle)))),
        static_cast<int16_t>(round(speed * sin(toRad(angle))))
    },
    .a = Pos{0, 0}}})
{}

//============================================================================//

const std::vector<std::string> Rocket::shape() const
{
    static const std::vector<std::string> shape = {"*"};
    return shape;
}

std::optional<BoundingBox> Rocket::boundingBox() 
{
    Pos p = pos();
    return BoundingBox{p, p};
}

} // namespace iron_dome_game