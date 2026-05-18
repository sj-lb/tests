#pragma once

#include <iostream>
#include <thread>

#include "grid.hpp"
#include "pitcher.hpp"
#include "plate.hpp"

namespace iron_dome_game
{
struct Game
{
    Game();
    ~Game() = default;

    void play();
    void keyboardListener();
    Grid grid;

    void spawnPlate();

    bool isShotFired = false;
    bool gameIsActive = false;

    static constexpr const int GAME_RUN_TIME_SEC = 60;

    // Statistics
    uint16_t platesFired = 0;
    uint16_t platesHit   = 0;
    uint16_t shotsFired  = 0;
};

}