#include <cmath>
#include <algorithm>

#include "score_calculator.hpp"
#include "plate.hpp"
#include "rocket.hpp"
#include "config.hpp"

namespace iron_dome_game
{
static constexpr float BASE_SCORE = 100.0f;

int DistanceBasedStrategy::calculateScore(
    std::unique_ptr<Plate> plate,
    std::unique_ptr<Rocket> rocket,
    float hitTime) const
{
    static const float max_distance = sqrt(
        pow(GRID_COLUMNS / 2, 2)
        + pow(GRID_ROWS - 3, 2));

    float distance = sqrt(
        pow(plate->pos(hitTime).x - rocket->pos0().x, 2)
        + pow(plate->pos(hitTime).y - rocket->pos0().y, 2));

    return BASE_SCORE * distance / max_distance;
}

int SpeedBasedStrategy::calculateScore(
    std::unique_ptr<Plate> plate,
    std::unique_ptr<Rocket>,
    float hitTime) const
{
    return BASE_SCORE * plate->speed(hitTime) / plate->speed(0);
}

// TODO: Implement TimeBasedStrategy::calculateScore()
int TimeBasedStrategy::calculateScore(
    std::unique_ptr<Plate>,
    std::unique_ptr<Rocket>,
    float hitTime) const
{
    return BASE_SCORE / (hitTime + 1.0f);
}

// TODO: Implement ScoreCalculator::setStrategy()
void ScoreCalculator::setStrategy(std::unique_ptr<ScoringStrategy> strategy)
{
    m_strategy = std::move(strategy);
}

// TODO: Implement ScoreCalculator::calculateScore()
int ScoreCalculator::calculateScore(
    std::unique_ptr<Plate> plate,
    std::unique_ptr<Rocket> rocket,
    float hitTime) const
{
    return m_strategy->calculateScore(
        std::move(plate),
        std::move(rocket),
        hitTime);
}

}

