#include "plate.hpp"

namespace iron_dome_game
{
Plate::Plate(Pos pos_, Velocity v_)
  : m_trajectory(Trajectory{.initial_state = InitialState{
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

float Plate::speed(float t)
{
    auto v = m_trajectory.calculateVelocity(m_trajectory.initial_state.t0 + std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<float>(t)));
    return sqrt(pow(v.x, 2) + pow(v.y, 2));
}

} // namespace iron_dome_game