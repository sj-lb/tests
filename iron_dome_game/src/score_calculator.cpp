#include "score_calculator.hpp"
#include "plate.hpp"
#include "rocket.hpp"
#include "config.hpp"
#include <cmath>
#include <algorithm>

namespace iron_dome_game
{

int DistanceBasedStrategy::calculateScore(
    std::shared_ptr<Plate> plate,
    std::shared_ptr<Rocket> rocket,
    float hitTime) const
{
    
    return 0; 
}

int SpeedBasedStrategy::calculateScore(
    std::shared_ptr<Plate> plate,
    std::shared_ptr<Rocket> rocket,
    float hitTime) const
{
    return 0;
}

// TODO: Implement TimeBasedStrategy::calculateScore()
int TimeBasedStrategy::calculateScore(
    std::shared_ptr<Plate> plate,
    std::shared_ptr<Rocket> rocket,
    float hitTime) const
{
    return 0;
}

// TODO: Implement ScoreCalculator constructor
ScoreCalculator::ScoreCalculator()
{

}

// TODO: Implement ScoreCalculator::setStrategy()
void ScoreCalculator::setStrategy(std::shared_ptr<ScoringStrategy> strategy)
{

}

// TODO: Implement ScoreCalculator::calculateScore()
int ScoreCalculator::calculateScore(
    std::shared_ptr<Plate> plate,
    std::shared_ptr<Rocket> rocket,
    float hitTime) const
{

    
    return 0;
}

}

