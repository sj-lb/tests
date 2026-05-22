#include "dome.hpp"

namespace iron_dome_game
{
const std::vector<std::string> Dome::shape() const
{
    static const std::vector<std::string> shape = {
        " __|__",
        "/     \\",
        "|_____|"
    };

    return shape;
}

} // namespace iron_dome_game