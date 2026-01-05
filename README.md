# Lone U-Boat

A digital implementation of the solitaire board game "Lone U-Boat" where you
command a German submarine during World War II, navigating through dangerous
waters while evading enemy ships and completing mission objectives.

## Overview

Lone U-Boat is a hex-based tactical game where you control a U-boat navigating
through mission-specific maps. The game features:

- **Hex-based movement system** with axial coordinates
- **Depth management** (Surfaced, Periscope, Medium, Deep)
- **Facing and direction** tracking for realistic submarine navigation
- **Detection mechanics** based on depth and enemy proximity
- **Mission-based gameplay** with unique objectives and map layouts
- **Status tracking** for torpedoes, hull damage, crew, and detection

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. Clone or download this repository
2. Create a virtual environment (recommended):

   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install pygame
   ```

## Running the Game

### Play Mode

To start the game:

```powershell
python main.py
```

To play a specific mission:

```powershell
python main.py --mission 1
```

### Game Controls

**Basic Movement:**
- **Q/E**: Rotate U-boat counterclockwise/clockwise
- **W**: Move U-boat forward in current facing direction
- **Z/X**: Change depth (Z = deeper, X = shallower)

**Display Toggles:**
- **G**: Toggle hex grid overlay
- **M**: Toggle map display
- **V**: Toggle terrain overlay
- **S**: Toggle status markers

**Window:**
- **F11**: Toggle fullscreen
- **ESC**: Exit to menu / quit

### Alignment Mode (F2)

Press **F2** during gameplay to enter Alignment Mode for calibrating the hex grid and status box positions. This is useful if elements appear misaligned or when setting up new missions.

**Alignment Controls:**
- **F2**: Toggle alignment mode on/off
- **Tab**: Switch between hex grid and status box adjustment
- **Arrow Keys**: Adjust position (1 map pixel, 10 with Shift)
- **+/-**: Scale hex grid or status boxes (1% normal, 5% with Shift)
- **Click**: Select status box (when in status box mode)
- **P**: Print current calibration to console
- **L**: Save calibration to `missions/mission_N_layout.json`

**Quick Calibration Workflow:**
1. Press **F2** to enter alignment mode
2. Use **Arrow Keys** to adjust hex grid until it aligns with the map
3. Press **Tab** to switch to status boxes mode
4. Use **Arrow Keys** to move all status boxes together (group operation)
5. Use **+/-** to scale all boxes proportionally if needed
6. Press **L** to save your calibration
7. Press **F2** to exit and test

All status boxes move and scale together as a group, maintaining their relative positions. Calibrations are stored in `missions/mission_N_layout.json` and work at any screen resolution.

For detailed documentation, see [ARCHITECTURE_BOARD_LAYOUT.md](ARCHITECTURE_BOARD_LAYOUT.md).

## Project Structure

```text
LoneUBoat/
├── main.py                 # Game entry point
├── editor.py              # Board editor and testing tool
├── extract_maps.py        # Utility to extract map images from PDFs
├── README.md             # This file
├── RULES.md              # Game rules documentation
├── DEVELOPMENT_PLAN.md   # Overall development plan
├── PHASE_2_REFINED.md    # Phase 2 subsystems (COMPLETE)
│
├── tests/                # Test suite (Phase 2: 100% complete)
│   ├── README.md         # Test documentation
│   ├── test_combat_resolver.py
│   ├── test_torpedo_validator.py
│   ├── test_repair_validator.py
│   ├── test_depth_validator.py
│   ├── test_movement_validator.py
│   ├── test_range_los.py
│   └── test_phase2_subsystems.py
│
├── config/
│   ├── __init__.py
│   ├── board_config.py      # Board dimensions, hex layout
│   └── board_layout_config.py  # Status box configurations
│
├── core/                 # Core game engine modules
│   ├── models.py         # Data classes (HexCoord, UBoat, Ship, etc.)
│   ├── hex_grid.py       # Hex geometry and coordinate math
│   ├── assets.py         # Asset loading (images, fonts)
│   ├── conditions.py     # Status box condition factory
│   ├── renderer.py       # All pygame rendering operations
│   ├── game_state.py     # Game logic and state management
│   ├── screen_manager.py # Screen transitions and state
│   │
│   ├── screens/          # Game screens
│   │   ├── base_screen.py
│   │   ├── main_menu.py
│   │   └── unified_game.py
│   │
│   └── # Phase 2 Subsystems (JSON-driven validators)
│       ├── dice.py                 # DiceRoller with seeded random
│       ├── action_cost_lookup.py  # AP costs from JSON
│       ├── range_los.py           # Range calculation & LOS
│       ├── movement_validator.py  # Movement validation
│       ├── depth_validator.py     # Depth change validation
│       ├── repair_validator.py    # Repair validation
│       ├── combat_resolver.py     # Combat resolution
│       └── torpedo_validator.py   # Torpedo loading/firing
│
├── missions/
│   ├── mission_1_config.py        # Mission 1 Python configuration
│   ├── mission_1_layout.json      # Mission 1 hex grid calibration
│   ├── mission_1_briefing.json    # Mission 1 briefing text
│   ├── mission_1_rules.json       # Mission 1 specific rules
│   ├── u_boat_ruleset_default.json  # Default U-boat action rules
│   ├── core_system_rules.json     # Core game system rules
│   └── ...                        # Additional missions
│
├── assets/
│   ├── maps/             # Mission map images
│   │   └── m1.png
│   └── manual/           # Game manual pages (if needed)
│
└── references/           # Original game materials
    └── RULES.txt         # Original rules reference
```

## Development Status

### ✅ Phase 1: Complete

- Turn-based gameplay system
- Action point management
- Game loop and state transitions

### ✅ Phase 2: Complete (100% - 23/23 hours)

All subsystems implemented with comprehensive tests:
- 2.1 DiceRoller (seeded random for testing)
- 2.2 Range & Line-of-Sight calculation
- 2.3 ActionCostLookup (JSON-driven AP costs)
- 2.4 MovementValidator (hex grid navigation)
- 2.5 DepthValidator (ballast tank damage rules)
- 2.6 RepairValidator (crew status & critical damage)
- 2.7 CombatResolver (deck gun & torpedoes)
- 2.8 TorpedoValidator (loading & firing rules)

### 🚧 Phase 3: Next - Action Implementation

Integrate validators into actual gameplay actions

## Testing

All Phase 2 subsystems have comprehensive test coverage. Run tests from the project root:

```powershell
# Run individual test files
python tests/test_combat_resolver.py
python tests/test_torpedo_validator.py
# ... etc

# Or run all tests
python -m pytest tests/
```

See [tests/README.md](tests/README.md) for detailed test documentation.

## Architecture

The codebase follows a clean modular architecture:

### Core Modules

- **`core/models.py`**: Pure data classes
  - `HexCoord`: Axial coordinate system (q, r)
  - `Facing`: Six directions (N, NE, SE, S, SW, NW)
  - `Depth`: Four depth levels (Surfaced, Periscope, Medium, Deep)
  - `UBoat`: Submarine state (position, facing, depth, crew, torpedoes)
  - `Ship`: Enemy ship state (position, facing, type)

- **`core/hex_grid.py`**: Hex geometry calculations
  - Pixel-to-hex and hex-to-pixel conversions
  - Hex corner calculations for rendering
  - Validation and boundary checking

- **`core/assets.py`**: Asset management
  - Loads and scales all images (U-boat, ships, markers)
  - Manages fonts
  - Handles missing asset gracefully

- **`core/conditions.py`**: Status box logic
  - Factory pattern for creating condition checkers
  - Lambda generation for dynamic status evaluation

- **`core/renderer.py`**: All rendering operations
  - Map and hex grid rendering
  - U-boat and ship rendering
  - Status box markers
  - Text overlays and debug info

- **`core/game_state.py`**: Game logic
  - Event handling
  - Update loop (ready for NPC AI)
  - State management

### Configuration

- **`config/board_config.py`**: Shared board configuration
  - Screen dimensions
  - Hex size and spacing
  - Status box positions and conditions
  - Color definitions

- **`missions/mission_X_config.py`**: Mission-specific data
  - Valid hex coordinates
  - Terrain (shallow water, land)
  - Starting positions
  - Mission objectives
  - Enemy ships (position, type, behavior rules)

## Adding New Missions

To create a new mission:

1. **Extract the map image** from the game PDF:

   ```powershell
   python extract_maps.py
   ```

   Place the extracted image in `assets/maps/`

2. **Create mission configuration** file:

   ```python
   # missions/mission_2_config.py
   
   MISSION_INFO = {
       'number': 2,
       'name': 'Mission Name',
       'map_image': 'm2.png',
       'description': 'Mission briefing...'
   }
   
   # Define valid hexes (use editor to determine coordinates)
   VALID_HEXES = [
       (0, 0), (1, 0), (2, 0),  # Row 0
       # ... more hexes
   ]
   
   SHALLOW_HEXES = [
       # Shallow water hexes
   ]
   
   LAND_HEXES = [
       # Land hexes (impassable)
   ]
   
   U_BOAT_START = {
       'position': (5, 10),
       'facing': 'N',
       'depth': 'PERISCOPE'
   }
   
   ENEMY_SHIPS = [
       {
           'type': 'DESTROYER',
           'position': (10, 15),
           'facing': 'S'
       },
       # ... more ships
   ]
   ```

3. **Use the editor** to align the hex grid:

   ```powershell
   python editor.py --mission 2 --edit
   ```

   - Drag the grid to align with the map
   - Use arrow keys for fine adjustment
   - Press **O** to print the final offset values
   - Update `board_config.py` with mission-specific offset if needed

4. **Test in game mode**:

   ```powershell
   python main.py --mission 2
   ```

## Development Status

### Completed ✅

- Hex grid rendering and coordinate system
- Map image overlay and alignment
- U-boat rendering with facing indicators
- Depth tracking and visualization
- Status box system with conditional markers
- Mission configuration system
- Board editor with alignment tools
- Clean modular architecture
- Type annotations throughout codebase

### In Progress 🚧

- Game rules implementation
- Player action validation
- NPC ship AI and behavior
- Detection system
- Combat resolution

### Planned 📋

- Turn-based game loop
- Mission objectives tracking
- Win/loss conditions
- Sound effects
- Multiple mission support
- Save/load game state

## Game Mechanics

### Hex Coordinate System

The game uses **axial coordinates** for hex positioning:
- **q**: Column (left/right)
- **r**: Row (diagonal)

Hex directions are flat-top oriented:
- **N** (North): up
- **NE** (Northeast): up-right
- **SE** (Southeast): down-right
- **S** (South): down
- **SW** (Southwest): down-left
- **NW** (Northwest): up-left

### Depth Levels

1. **Surfaced**: Maximum speed, highly visible, vulnerable
2. **Periscope**: Balanced visibility and stealth
3. **Medium**: Reduced visibility, slower
4. **Deep**: Safest, slowest, limited operations

### Status Tracking

The game tracks multiple status indicators:
- **Torpedo tubes**: 5 tubes (4 bow, 1 stern)
- **Hull damage**: 3 hit points
- **Detection level**: 0-3 (Silent, Aware, Traced, Locked)
- **Crew status**: Captain, Engineer, Sonar Operator, Weapons Officer,
  Lookout, Medic
- **Action points**: Available actions per turn

## Contributing

This is a personal project implementing the Lone U-Boat board game.
The game rules and original design belong to the original publisher.

## Technical Notes

### Type Hints

The codebase uses Python type hints extensively:

```python
def hex_to_pixel(hex_coord: HexCoord) -> Tuple[float, float]:
    """Convert hex coordinate to pixel position."""
    ...
```

Type checking can be performed with:

```powershell
pip install mypy
mypy .
```

### Performance

- Rendering is capped at 60 FPS
- Hex calculations are optimized for flat-top orientation
- Assets are loaded once at startup

### Debugging

Enable debug mode in the editor to see:
- Hex coordinates on hover
- Grid alignment info
- Status box positions
- Collision boundaries

## Credits

- **Original Game**: Lone U-Boat board game
- **Implementation**: Digital adaptation for personal use
- **Engine**: Pygame
- **Language**: Python 3.13

## License

This is a personal implementation of the board game for educational purposes.
All game rules and artwork belong to the original publisher.

---

**Last Updated**: January 1, 2026  
**Version**: 0.1.0 (Refactored Architecture)
