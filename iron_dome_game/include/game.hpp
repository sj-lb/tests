#pragma once

#include <iostream>
#include <thread>

#include "keyboard_listener.hpp"
#include "grid.hpp"
#include "score_calculator.hpp"
#include "config.hpp"
#include "game_statistics.hpp"

namespace iron_dome_game
{
class Game
{
public:
    Game();
    ~Game() = default;

    void play();
    void keyboardThread();
    
    void spawnPlate();
    void spawnRocket();
private:
    Grid grid;
    KeyboardListener keyboard_listener;
    GameStatistics stats;
    ScoreCalculator score_calculator;

    bool gameIsActive = false;

    static constexpr int GAME_RUN_TIME_SEC = 60;

    // Statistics
    uint16_t platesFired = 0;

    float m_rocket_angle = 90.0f;
    float m_rocket_speed = 30.0f;
};

}