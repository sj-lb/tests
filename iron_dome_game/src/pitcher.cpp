#include "config.hpp"
#include "pitcher.hpp"

namespace iron_dome_game
{

//============================================================================//

const std::vector<std::string> Pitcher::shape() const
{
    static const std::vector<std::string> shape = {
        "  *",
        "/^|^\\",
        "  |",
        " / \\",
        "/___\\"
    };
    return shape;
}
}