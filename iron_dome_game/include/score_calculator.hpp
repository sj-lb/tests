#pragma once

#include "entity.hpp"
#include "trajectory.hpp"
#include <memory>

namespace iron_dome_game
{

// Forward declarations
struct Plate;
struct Rocket;

/**
 * Base Strategy Interface for scoring calculations
 * 
 * TODO: Create abstract base class for scoring strategies
 * Should have:
 *   - Pure virtual function calculateScore() that takes plate and rocket
 *   - Virtual destructor
 */
class ScoringStrategy
{
public:
    virtual ~ScoringStrategy() = default;
    
    /**
     * Calculate score for hitting a plate with a rocket
     * 
     * TODO: Define pure virtual function
     * @param plate The plate that was hit
     * @param rocket The rocket that hit the plate
     * @param hitTime Time taken to hit (in seconds)
     * @return Calculated score
     */
    virtual int calculateScore(
        std::unique_ptr<Plate> plate,
        std::unique_ptr<Rocket> rocket,
        float hitTime
    ) const = 0;
};

/**
 * Distance-based scoring strategy
 * 
 * TODO: Implement strategy that awards more points for hitting plates farther away
 * Formula: baseScore * (distance / maxDistance)
 * Where:
 *   - baseScore = 100
 *   - distance = distance from cannon to plate at hit time
 *   - maxDistance = GRID_COLUMNS (or reasonable maximum)
 * 
 * Characteristics:
 * - Rewards accuracy at long range
 * - Base score: 100 points
 */
class DistanceBasedStrategy : public ScoringStrategy
{
public:
    DistanceBasedStrategy() = default;
    ~DistanceBasedStrategy() = default;
    
    // TODO: Implement calculateScore()
    // Calculate distance from origin (0, 0) or cannon position to plate position
    // Use formula: distance = sqrt((x2-x1)² + (y2-y1)²)
    // Return: baseScore * (distance / maxDistance)
    int calculateScore(
        std::unique_ptr<Plate> plate,
        std::unique_ptr<Rocket> rocket,
        float hitTime
    ) const override;
};

/**
 * Speed-based scoring strategy
 * 
 * TODO: Implement strategy that awards more points for hitting faster plates
 * Formula: baseScore * (plateSpeed / maxSpeed)
 * Where:
 *   - baseScore = 100
 *   - plateSpeed = magnitude of plate velocity
 *   - maxSpeed = reasonable maximum (e.g., 50)
 * 
 * Characteristics:
 * - Rewards hitting fast-moving targets
 * - Base score: 100 points
 */
class SpeedBasedStrategy : public ScoringStrategy
{
public:
    SpeedBasedStrategy() = default;
    ~SpeedBasedStrategy() = default;
    
    // TODO: Implement calculateScore()
    // Calculate plate speed: speed = sqrt(vx² + vy²)
    // Return: baseScore * (speed / maxSpeed)
    int calculateScore(
        std::unique_ptr<Plate> plate,
        std::unique_ptr<Rocket> rocket,
        float hitTime
    ) const override;
};

/**
 * Time-based scoring strategy
 * 
 * TODO: Implement strategy that awards more points for faster hits
 * Formula: baseScore * (1.0 / (hitTime + 1.0))
 * Where:
 *   - baseScore = 100
 *   - hitTime = time from plate spawn to hit (in seconds)
 * 
 * Characteristics:
 * - Rewards quick reactions
 * - Base score: 100 points
 * - Faster hits = higher multiplier
 */
class TimeBasedStrategy : public ScoringStrategy
{
public:
    TimeBasedStrategy() = default;
    ~TimeBasedStrategy() = default;
    
    // TODO: Implement calculateScore()
    // Use hitTime directly
    // Return: baseScore * (1.0 / (hitTime + 1.0))
    // This gives higher scores for smaller hitTime
    int calculateScore(
        std::unique_ptr<Plate> plate,
        std::unique_ptr<Rocket> rocket,
        float hitTime
    ) const override;
};

/**
 * Score Calculator - Uses Strategy Pattern
 * 
 * TODO: Implement score calculator that uses a scoring strategy
 * Should have:
 *   - Member variable to hold current strategy
 *   - Method to set strategy
 *   - Method to calculate score using current strategy
 *   - Default strategy (can be DistanceBasedStrategy)
 */
class ScoreCalculator
{
public:
    ScoreCalculator() : m_strategy(std::make_unique<DistanceBasedStrategy>()) {}
    ~ScoreCalculator() = default;
    
    /**
     * Set the scoring strategy to use
     * 
     * TODO: Implement method to set strategy
     * @param strategy Unique pointer to scoring strategy
     */
    void setStrategy(std::unique_ptr<ScoringStrategy> strategy);
    
    /**
     * Calculate score using current strategy
     * 
     * TODO: Implement method to calculate score
     * @param plate The plate that was hit
     * @param rocket The rocket that hit the plate
     * @param hitTime Time taken to hit (in seconds)
     * @return Calculated score
     */
    int calculateScore(
        std::unique_ptr<Plate> plate,
        std::unique_ptr<Rocket> rocket,
        float hitTime
    ) const;

private:
    // TODO: Add member variable to store current strategy
    std::unique_ptr<ScoringStrategy> m_strategy;
};

}

