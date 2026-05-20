#pragma once
#include <stdint.h>
#include <chrono>
#include <math.h>
#include "config.hpp"

namespace iron_dome_game
{
struct Pos
{
    int16_t x;
    int16_t y;
    Pos operator+(const Pos& other) const {return Pos{
        .x = static_cast<int16_t>(x + other.x),
        .y = static_cast<int16_t>(y + other.y)};}
    bool operator==( const Pos& other ) const { return x == other.x && y == other.y; }
};
typedef Pos Velocity;
typedef Pos Acceleration;

struct InitialState
{
    Pos pos;
    Velocity v = {0, 0};
    Acceleration a = {0, GRAVITY};
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
};

struct Trajectory
{
    const InitialState initial_state;

    std::chrono::duration<float> duration() { return  std::chrono::steady_clock::now() - initial_state.t0; }

    Pos calculatePosition(std::chrono::steady_clock::time_point = std::chrono::steady_clock::now())
    {
        auto t = duration().count();
        return Pos{
            .x = static_cast<int16_t>(round(
                initial_state.pos.x
                + initial_state.v.x * t
                + 0.5 * initial_state.a.x * pow(t, 2))),
            .y = static_cast<int16_t>(round(
                initial_state.pos.y
                + initial_state.v.y * t
                + 0.5 * initial_state.a.y * pow(t, 2)))
        };
    }
};
}