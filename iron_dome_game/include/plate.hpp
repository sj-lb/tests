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
    virtual Pos pos() override { return m_trajectory.calculatePosition(); }

    Pos pos(float t) { return m_trajectory.calculatePosition(m_trajectory.initial_state.t0 + std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<float>(t))); }
    float speed(float t);
    void setAirTime() { m_air_time = m_trajectory.duration().count(); }
    float airTime() const { return m_air_time; }
private:
    Trajectory m_trajectory;
    float m_air_time = 0.0f;
};

} // namespace iron_dome_game