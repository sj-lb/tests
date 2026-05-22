#pragma once

#include <chrono>
#include <vector>
#include <string>
#include <map>
#include <cstdint>

namespace iron_dome_game
{

/**
 * Game Statistics Tracker - Tests Data Structures and Feature Implementation
 * 
 * TODO: Implement the following:
 * 1. Track various game statistics in real-time
 * 2. Calculate running averages and trends
 * 3. Store hit history with timestamps
 * 4. Provide formatted statistics output
 * 5. Support reset functionality
 * 
 * Statistics to track:
 * - Total score
 * - Total hits
 * - Total shots
 * - Accuracy percentage
 * - Average time to hit
 * - Best streak (consecutive hits)
 * - Hit rate over time
 */

/**
 * Structure to store information about a single hit
 */
struct HitRecord
{
    HitRecord(int score_, float time_to_hit_)
      : score(score_), time_to_hit(time_to_hit_), timestamp(std::chrono::steady_clock::now()) {}

    int score;
    float time_to_hit;
    std::chrono::steady_clock::time_point timestamp;
};

/**
 * Game Statistics Tracker
 * 
 * TODO: Implement statistics tracking and calculation
 */
class GameStatistics
{
public:
    void recordShot() { ++m_total_shots; }
    /**
     * Record a successful hit
     * 
     * TODO: Implement method to record a hit
     * @param score Score earned for this hit
     * @param time_to_hit Time from plate spawn to hit (seconds)
     */
    void recordHit(int score, float time_to_hit);
    
    /**
     * Record a missed shot
     * 
     * TODO: Implement method to record a miss
     */
    void recordMiss() { m_current_streak = 0; }

    
    /**
     * Get total score
     * 
     * TODO: Implement getter
     * @return Total accumulated score
     */
    int getTotalScore() const;
    
    /**
     * Get total number of hits
     * 
     * TODO: Implement getter
     * @return Number of successful hits
     */
    uint16_t getTotalHits() const;
    
    /**
     * Get total number of shots
     * 
     * TODO: Implement getter
     * @return Total shots fired (hits + misses)
     */
    uint16_t getTotalShots() const;
    
    /**
     * Get accuracy percentage
     * 
     * TODO: Implement calculation
     * @return Accuracy as percentage (0-100)
     */
    float getAccuracy() const;
    
    /**
     * Get average time to hit
     * 
     * TODO: Implement calculation
     * @return Average time to hit in seconds, or 0.0 if no hits
     */
    float getAverageTimeToHit() const;
    
    /**
     * Get best streak (consecutive hits)
     * 
     * TODO: Implement calculation
     * Track consecutive hits and return maximum streak
     * @return Longest sequence of consecutive hits
     */
    uint16_t getBestStreak() const;
    
    /**
     * Get formatted statistics string
     * 
     * TODO: Implement formatted output
     * Format should be readable and include key statistics
     * @return Formatted string with statistics
     */
    std::string getFormattedStats() const;
    
    /**
     * Reset all statistics
     * 
     * TODO: Implement reset functionality
     * Clear all tracked data and reset counters
     */
    void reset();

private:
    // TODO: Add member variables to track statistics
    int m_total_score = 0;
    uint16_t m_total_shots = 0;
    uint16_t m_total_hits = 0;
    uint16_t m_current_streak = 0;
    uint16_t m_best_streak = 0;
    
    // TODO: Store hit history
    std::vector<HitRecord> m_hit_history;
};

}

