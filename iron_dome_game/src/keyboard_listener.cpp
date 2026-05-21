#include <unistd.h>
#include <thread>

#include "keyboard_listener.hpp"

namespace iron_dome_game
{
KeyboardListener::KeyboardListener() {
    tcgetattr(STDIN_FILENO, &orig_termios);
    
    struct termios raw = orig_termios;
    // ICANON turns off line buffering (Enter key requirement)
    // ECHO turns off displaying the typed characters on screen
    raw.c_lflag &= ~(ICANON | ECHO);
    
    // Set read() to be non-blocking
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    
    tcsetattr(STDIN_FILENO, TCSANOW, &raw);
}

KeyboardListener::~KeyboardListener() {
    tcsetattr(STDIN_FILENO, TCSANOW, &orig_termios);
}

//============================================================================//

int KeyboardListener::getKey() {
    char c;

    if (read(STDIN_FILENO, &c, 1) <= 0)
        return KEY_NONE;

    if (c == KEY_ESC) {
        char seq[2];
        std::this_thread::sleep_for(std::chrono::milliseconds(10));

        if (read(STDIN_FILENO, &seq[0], 1) == 0 || read(STDIN_FILENO, &seq[1], 1) == 0)
            return KEY_ESC;

        if (seq[0] == '[') {
            switch (seq[1]) {
            case 'A':
                return KEY_UP;
            case 'B':
                return KEY_DOWN;
            case 'C':
                return KEY_RIGHT;
            case 'D':
                return KEY_LEFT;
            }
        }
        return KEY_ESC;
    }

    return c;
}
} // namespace iron_dome_game