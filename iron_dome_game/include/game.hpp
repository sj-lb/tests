#pragma once

#include <iostream>
#include <thread>

#include "keyboard_listener.hpp"
#include "grid.hpp"

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
private:
    Grid grid;
    KeyboardListener keyboardListener;

    bool isShotFired = false;
    bool gameIsActive = false;

    static constexpr const int GAME_RUN_TIME_SEC = 60;

    // Statistics
    uint16_t platesFired = 0;
    uint16_t platesHit   = 0;
    uint16_t shotsFired  = 0;
};

}