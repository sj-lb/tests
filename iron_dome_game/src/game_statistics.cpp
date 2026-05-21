#include "game_statistics.hpp"
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <numeric>

namespace iron_dome_game
{
void GameStatistics::recordHit(int score, float time_to_hit)
{
    m_hit_history.emplace_back(score, time_to_hit);
    m_total_score += score;
    ++m_total_hits;
    ++m_current_streak;
}

void GameStatistics::recordMiss()
{
    if (m_current_streak > m_best_streak)
        m_best_streak = m_current_streak;
    m_current_streak = 0;
}

int GameStatistics::getTotalScore() const
{
    return m_total_score;
}

uint16_t GameStatistics::getTotalHits() const
{
    return m_total_hits;
}

uint16_t GameStatistics::getTotalShots() const
{
    return m_total_shots;
}

float GameStatistics::getAccuracy() const
{
    if (m_total_shots == 0)
        return 0.0f;
    return static_cast<float>(m_total_hits) / m_total_shots * 100.0f;
}

float GameStatistics::getAverageTimeToHit() const

{
    if (m_hit_history.empty())
        return 0.0f;
    float total_time = std::accumulate(
        m_hit_history.begin(),
        m_hit_history.end(),
        0.0f,
        [](float sum, const HitRecord& record)
            { return sum + record.time_to_hit; });
    return total_time / m_hit_history.size();
}

uint16_t GameStatistics::getBestStreak() const
{
    return std::max(m_best_streak, m_current_streak);
}

std::string GameStatistics::getFormattedStats() const
{        
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2);
    oss << "Total Score: " << m_total_score << "\n";
    oss << "Total Shots: " << m_total_shots << "\n";
    oss << "Total Hits: " << m_total_hits << "\n";
    oss << "Accuracy: " << getAccuracy() << "%\n";
    oss << "Average Time to Hit: " << getAverageTimeToHit() << "s\n";
    oss << "Best Streak: " << getBestStreak() << "\n";
    return oss.str();
}

void GameStatistics::reset()
{
    m_total_score = 0;
    m_total_shots = 0;
    m_total_hits = 0;
    m_current_streak = 0;
    m_best_streak = 0;
    m_hit_history.clear();
}

} // namespace iron_dome_game