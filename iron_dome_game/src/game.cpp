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

void Game::keyboardThread() 
{
    while (is_running)
    {
        switch (keyboard_listener.getKey()) {
        case '\n':
            spawnRocket();
            break;
        case KEY_ESC:
            is_running = false;
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
    }
}

//============================================================================//

void Game::play() 
{
    is_running = true;

    // std::cout << "PLAYING" << std::endl;
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
    std::thread keyboard_thread(&Game::keyboardThread, this);

    std::chrono::steady_clock::time_point last_refresh = std::chrono::steady_clock::now();

    while (is_running)
    {
        if (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - last_refresh).count() > 100)
        {
            system("clear");
            grid.refresh();
            grid.draw();
            
            last_refresh = std::chrono::steady_clock::now();
        }

        if (grid.clearExpiredAndCheckMisses())
            stats.recordMiss();

        auto hits = grid.checkHits();
        for (const auto& [rocket_id, plate_id] : hits)
        {
            auto rocket_ptr = dynamic_cast<Rocket*>(grid.getEntity(rocket_id).get());
            auto plate_ptr = dynamic_cast<Plate*>(grid.getEntity(plate_id).get());
            std::unique_ptr<Plate> plate = std::make_unique<Plate>(*plate_ptr);
            std::unique_ptr<Rocket> rocket = std::make_unique<Rocket>(*rocket_ptr);

            stats.recordHit(
                score_calculator.calculateScore(
                    std::move(plate),
                    std::move(rocket),
                    plate->airTime()),
                plate->airTime());

            grid.removeEntity(rocket_id);
            grid.removeEntity(plate_id);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(10));

        auto game_time = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - t0).count();
        if (game_time > GAME_RUN_TIME_SEC)
            is_running = false;
        else if (game_time / 2 > plates_fired)
            spawnPlate();
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

    ++plates_fired;
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