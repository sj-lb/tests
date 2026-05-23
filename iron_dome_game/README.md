
# Iron Dome — Terminal Defense Game 🚀🛡️

## 1. Project Overview
- Iron Dome is a compact, terminal-based arcade game that simulates a simple anti-rocket defense scenario. Players aim and fire interceptors (rockets) to destroy incoming plates before they land.
- Core mechanics: spawn-and-intercept gameplay with real-time keyboard input, a scoring system, and a timed game loop.

## 2. Getting Started
### Build Instructions
Production build:
```bash
make
```

Debug build:
```bash
make debug
```

If you prefer a direct compilation (single-step):
```bash
g++ -std=c++17 -Wall -Wextra -I./include src/*.cpp -lpthread -o iron_dome_game
```

### Running the Game
Execute the compiled binary from the project directory:
```bash
./iron_dome_game
```

## 3. How to Play
- **Objective:** Shoot down falling plates before they hit the ground. Earn points for successful interceptions.
- **Controls:**
	- Press `Enter` — Fire a rocket (interceptor).
	- Arrow `Up` / `Down` — Increase / decrease rocket speed.
	- Arrow `Left` / `Right` — Adjust rocket firing angle.
	- `Esc` — Exit the game immediately.
- **Winning / Losing:**
	- The game runs for a fixed duration (60 seconds). Final score is shown at the end.
	- Missed plates are tracked as misses; score is based on hit accuracy and plate airtime.

## 4. Changelog

- **Migrated from `std::shared_ptr` to `std::unique_ptr`**
    - *Dev Note: `Entity`s should be owned by one system at a time (grid / scoring)*
- **Advanced Input System:** Replaced blocking `getchar()` input with `KeyboardListener` class using termios for real-time, non-blocking keyboard input
- **Player-Controlled Rocket Mechanics:** Added support for arrow keys (up/down for speed, left/right for angle adjustments), allowing players to adjust launch parameters in real-time; new `spawnRocket()` method creates rockets with player-set parameters
  - *Dev Note: added mutex since now both threads interface with the `Grid`*
- **Entity System Refactoring:** 
    - Removed the redundant `EntityType` enum
        - *Dev Note: instance class can be inferred using `dynamic_cast`*
    - replaced `drawOnGrid()` with `shape()` method returning ASCII art vectors
        - *Dev Note: the `Entity` shouldn't care about the `Grid` that holds it, or how it is rendered there; it should only export its own shape*
    - Changed entity storage container from `std::list` to `std::map` for indexed lookup
- **Collision Detection Enhancement:** Changed `checkHits()` return type from simple count to vector of rocket/plate ID pairs; enables proper multi-collision handling and score attribution.
- **Grid Rendering Refactor:**
    - Converted from static 2D char array to dynamic `std::vector<std::string>`
        - *Dev Note: could have made the grid a single string and worked with offsets, but I felt this configutation is more maintainable, and working with strings is still a significant performance improvement over modifying each "pixel" independently*
    - added grid template system
	    - *Dev Note: keeping a template of the base grid state with its static entities is way more efficient than drawing everything anew with each refresh, and it also means we don't actually need to track static entities anymore*
- **Game Statistics Implementation according to `TODO` documentation**
- **Configuration Modernization:** Converted `#define` macros to `constexpr` values in `config.hpp` for better type safety.
- **Build System & Makefile:** Added `Makefile` with production (`-O2`) and debug (`-g -O0`) build targets
