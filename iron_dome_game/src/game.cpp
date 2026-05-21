#include <iostream>
#include <random>
#include <memory>
#include <math.h>
#include <termios.h>

#include "game.hpp"
#include "pitcher.hpp"
#include "plate.hpp"
#include "rocket.hpp"
#include "dome.hpp"

namespace iron_dome_game
{

Game::Game() 
{
    grid.addEntity(std::make_unique<iron_dome_game::Pitcher>(
        Pos{static_cast<int16_t>(grid.columns() - 7), 0}));
    grid.addEntity(std::make_unique<iron_dome_game::Dome>(
        Pos{static_cast<int16_t>(grid.columns() / 2 - 3), 0}));
}

//============================================================================//

void Game::keyboardThread() 
{
    while (gameIsActive)
    {
        switch (keyboardListener.getKey()) {
        case '\n':
            // spawnRocket();
            isShotFired = true;
            break;
        case KEY_ESC:
            gameIsActive = false;
            break;
        default:
            break;
        }
        // std::cout << "Fired" << std::endl;
    }
}

//============================================================================//

void Game::play() 
{
    gameIsActive = true;

    // std::cout << "PLAYING" << std::endl;
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
    std::thread keyboardThread(&Game::keyboardThread, this);

    std::chrono::steady_clock::time_point lastTimeRefreshed = std::chrono::steady_clock::now();

    while (gameIsActive)
    {
        if (isShotFired)
        {
            isShotFired = false;
            ++shotsFired;
        }

        if (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - lastTimeRefreshed).count() > 100)
        {
            system("clear");
            grid.refresh();
            grid.draw();
            
            lastTimeRefreshed = std::chrono::steady_clock::now();
        }

        platesHit += grid.checkHits();

        std::this_thread::sleep_for(std::chrono::milliseconds(10));

        auto gameTime = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - t0).count();
        if (gameTime > GAME_RUN_TIME_SEC)
        {
            gameIsActive = false;
        }
        else if (gameTime / 2 > platesFired)
        {
            spawnPlate();
            ++platesFired;
        }
    }

    std::cout << "Game over. Total hits: " << platesHit << ". Total shots fired: " << shotsFired << std::endl;
    std::cout << "Accuracy " << (float)platesHit /  shotsFired * 100 << "%" << std::endl;
    keyboardThread.join();
}

//============================================================================//

void Game::spawnPlate() 
{
    static const double ANGLE = degToRad(120.0);
    int firePower = std::rand() % 15 + 30;

    grid.addEntity(std::make_unique<Plate>(
        Pos{static_cast<int16_t>(grid.columns() - 10), 5},
        Velocity{ 
        .x = static_cast<int16_t>(std::cos(ANGLE) * firePower),
        .y = static_cast<int16_t>(std::sin(ANGLE) * firePower)
    }));
}

}