#include "game_statistics.hpp"
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <numeric>

namespace iron_dome_game
{

HitRecord::HitRecord(int score, float timeToHit)
    : score(score), timeToHit(timeToHit)
{

}

GameStatistics::GameStatistics()
{
}

void GameStatistics::recordHit(int score, float timeToHit)
{

}

void GameStatistics::recordMiss()
{
}

int GameStatistics::getTotalScore() const
{
    return 0;
}

uint16_t GameStatistics::getTotalHits() const
{
    return 0;
}

uint16_t GameStatistics::getTotalShots() const
{
    return 0;
}

float GameStatistics::getAccuracy() const
{

    return 0.0f;
}

float GameStatistics::getAverageTimeToHit() const

{
    
    return 0.0f;
}

uint16_t GameStatistics::getBestStreak() const
{
    return 0;
}

std::string GameStatistics::getFormattedStats() const
{        
    return "";
}

void GameStatistics::reset()
{

}

void GameStatistics::updateStreak(bool isHit)
{
}

}


