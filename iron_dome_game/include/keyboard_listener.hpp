#include <termios.h>

namespace iron_dome_game
{
enum Key {
    KEY_NONE = 0,
    KEY_ESC = 27,
    KEY_UP = 1000,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT
};

class KeyboardListener {
public:
    KeyboardListener();
    ~KeyboardListener();

    int getKey();

private:
    struct termios orig_termios;
};
} // namespace iron_dome_game