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
        switch (keyboard_listener.getKey()) {
        case '\n':
            isShotFired = true;
            spawnRocket();
            break;
        case KEY_ESC:
            gameIsActive = false;
            break;
        case KEY_UP:
            m_rocket_speed += m_rocket_speed < 100.0f ? 5.0f : 0.0f;
            break;
        case KEY_DOWN:
            m_rocket_speed -= m_rocket_speed > 5.0f ? 5.0f : 0.0f;
            break;
        case KEY_RIGHT:
            m_rocket_angle -= m_rocket_angle > 15.0f ? 5.0f : 0.0f;
            break;
        case KEY_LEFT:
            m_rocket_angle += m_rocket_angle < 165.0f ? 5.0f : 0.0f;
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
    std::thread keyboard_thread(&Game::keyboardThread, this);

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

        auto hits = grid.checkHits();
        for (const auto& [id1, id2] : hits)
        {
            if (id2.has_value())
            {
                ++plates_hit;

                // Move both entities out of the grid exactly once.
                auto e1 = grid.getEntity(id1);
                auto e2 = grid.getEntity(id2.value());

                Plate*  plate_ptr  = dynamic_cast<Plate*>(e1.get());
                Rocket* rocket_ptr = nullptr;
                if (plate_ptr)
                {
                    rocket_ptr = dynamic_cast<Rocket*>(e2.get());
                }
                else
                {
                    plate_ptr  = dynamic_cast<Plate*>(e2.get());
                    rocket_ptr = dynamic_cast<Rocket*>(e1.get());
                }

                std::unique_ptr<Plate>  plate;
                std::unique_ptr<Rocket> rocket;
                if (plate_ptr)  plate  = std::make_unique<Plate>(*plate_ptr);
                if (rocket_ptr) rocket = std::make_unique<Rocket>(*rocket_ptr);

                grid.removeEntity(id2.value());
            }
            else
            {
                auto e1 = grid.getEntity(id1);
                if (dynamic_cast<Rocket*>(e1.get()) != nullptr)
                    stats.recordMiss();
            }
            grid.removeEntity(id1);
        }

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

    keyboard_thread.join();
    std::cout << "GAME OVER\n" << stats.getFormattedStats() << std::endl;
}

//============================================================================//

void Game::spawnPlate() 
{
    static const double ANGLE = toRad(120.0);
    int firePower = std::rand() % 15 + 30;

    grid.addEntity(std::make_unique<Plate>(
        Pos{static_cast<int16_t>(grid.columns() - 10), 5},
        Velocity{ 
        .x = static_cast<int16_t>(std::cos(ANGLE) * firePower),
        .y = static_cast<int16_t>(std::sin(ANGLE) * firePower)
    }));
}

void Game::spawnRocket() 
{
    grid.addEntity(std::make_unique<Rocket>(
        Pos{static_cast<int16_t>(grid.columns() / 2), 3},
        m_rocket_angle,
        m_rocket_speed));
    stats.recordShot();
}

} // namespace iron_dome_game