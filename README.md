# Lone U-Boat

A digital implementation of the solitaire board game "Lone U-Boat" where you command a German submarine during World War II, navigating through dangerous waters while evading enemy ships and completing mission objectives.

## Overview

Lone U-Boat is a hex-based tactical game where you control a U-boat navigating through mission-specific maps. The game features:

- **Hex-based movement system** with axial coordinates
- **Depth management** (Surfaced, Periscope, Medium, Deep)  
- **Facing and direction** tracking for realistic submarine navigation
- **Detection mechanics** based on depth and enemy proximity
- **Mission-based gameplay** with unique objectives and map layouts
- **JSON-driven rules engine** with zero hardcoded game rules
- **Action queue system** for planning and executing turns
- **Comprehensive damage system** for ships and U-boats

## Quick Start

```powershell
# Clone and setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pygame

# Play the game
python main.py
```

## Development Status

**Current Phase**: Phase 4 - Enemy AI & Automation (In Progress)  
**Next Phase**: Complete Escort AI and Depth Charges

### Completed Phases

- ✅ **Phase 1**: Turn system with 6-phase cycle and AP rolling
- ✅ **Phase 2**: Validators (LOS, range, movement, torpedoes, repairs, combat, depth)  
- ✅ **Phase 3**: All 7 U-boat actions (Move, Rotate, DepthChange, Repair, DeckGun, LoadTorpedo, FireTorpedo)
- ✅ **Phase 3.6**: Complete damage resolution system
- ✅ **Refactoring**: All game rules moved to JSON (zero redundancy)
- ⚙️ **Phase 4**: Merchant AI (complete), Detection AI (complete), Escort AI (in progress)

**Test Coverage**: 225+ tests across 17 test files, all passing

See [docs/PHASE_1_AUDIT.md](docs/PHASE_1_AUDIT.md) for comprehensive Phase 3 completion audit.

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

**Quick Calibration Workflow:**
1. Press **F2** to enter alignment mode
2. Use **Arrow Keys** to adjust hex grid until it aligns with the map
3. Press **Tab** to switch to status boxes mode
4. Use **Arrow Keys** to move all status boxes together (group operation)
5. Use **+/-** to scale all boxes proportionally if needed
6. Press **L** to save your calibration
7. Press **F2** to exit and test

All status boxes move and scale together as a group, maintaining their relative positions. Calibrations are stored in `missions/mission_N_layout.json` and work at any screen resolution.

For detailed controls, see [docs/ALIGNMENT_MODE_CONTROLS.md](docs/ALIGNMENT_MODE_CONTROLS.md).

## Project Structure

```text
LoneUBoat/
├── main.py                 # Game entry point
├── editor.py              # Board editor and testing tool
├── extract_maps.py        # Utility to extract map images from PDFs
├── README.md             # This file
├── RULES.md              # Game rules documentation
├──Architecture Overview

The codebase follows a clean, modular architecture with a **complete separation between code and configuration**. All game rules live in JSON files, with Python code acting as a generic rules engine.

### Code Structure

```text
LoneUBoat/
├── main.py                    # Game entry point
├── README.md                  # This file
├── RULES.md                   # Player-facing game rules reference
│
├── core/                      # Game engine (100% generic, no hardcoded rules)
│   ├── models.py              # Data classes (UBoat, Ship, HexCoord, etc.)
│   ├── hex_grid.py            # Hex geometry calculations
│   ├── dice.py                # Dice roller with seeding
│   ├── assets.py              # Image/font loading
│   ├── renderer.py            # Pygame rendering
│   ├── board_layout.py        # Resolution-independent positioning
│   ├── turn_manager.py        # Phase cycle and AP rolling
│   │
│   ├── screens/               # UI screens
│   │   ├── base_screen.py
│   │   ├── main_menu.py
│   │   └── unified_game.py    # Main gameplay screen
│   │
│   ├── actions/               # Player action system
│   │   ├── base_action.py     # Action interface
│   │   ├── action_queue.py    # Queue with AP tracking
│   │   ├── move_action.py     # Movement
│   │   ├── rotate_action.py   # Rotation
│   │   ├── depth_change_action.py
│   │   ├── repair_action.py
│   │   ├── deck_gun_action.py
│   │   ├── load_torpedo_action.py
│   │   └── fire_torpedo_action.py
│   │
│   ├── damage/                # Damage resolution
│   │   ├── ship_damage.py     # Allied ship damage
│   │   └── uboat_damage.py    # U-boat damage
│   │
│   └── # AI Controllers (load rules from JSON)
│       ├── merchant_ai.py     # Merchant movement
│       ├── detection_ai.py    # Detection phase
│       ├── escort_ai.py       # Escort actions
│       ├── combat_resolver.py # Combat hit tables
│       ├── movement_validator.py
│       ├── depth_validator.py
│       ├── repair_validator.py
│       ├── torpedo_validator.py
│       └── action_costs.py    # AP cost lookups
│
├── config/                    # Board/UI configuration
│   ├── board_config.py        # Screen dimensions, colors
│   └── board_layout_config.py # Status box layouts
│
├── missions/                  # Mission data (JSON-driven)
│   ├── mission_1_config.py    # Mission 1 setup
│   ├── mission_1_layout.json  # Hex grid calibration
│   ├── mission_1_briefing.json
│   ├── mission_1_rules.json   # Mission-specific rules
│   │
│   ├── # Shared Rule Files (loaded by core systems)
│   ├── u_boat_ruleset_default.json  # All U-boat actions & AP rules
│   ├── escort_ai_baseline.json      # Escort behavior & detection
│   ├── damage_tables.json           # All damage resolution tables
│   ├── core_system_rules.json       # Victory conditions, etc.
│   │
│   ├── mission_rules_loader.py      # JSON parser
│   ├── mission_schema.md            # JSON format documentation
│   └── README_METADATA.md           # Mission system guide
│
├── assets/
│   ├── maps/                  # Mission map images
│   └── manual/                # Game manual scans
│
├── tests/                     # Comprehensive test suite (225+ tests)
│   ├── README.md
│   ├── test_*.py              # Unit tests for all systems
│   └── scenarios/             # Integration test scenarios
│       ├── test_deck_gun_scenario.py
│       └── test_torpedo_scenario.py
│
├── utils/                     # Development utilities
│   ├── editor.py              # Legacy board editor (deprecated)
│   └── extract_maps.py        # PDF map extraction
│
├── docs/                      # Development documentation
│   ├── ALIGNMENT_MODE_CONTROLS.md
│   ├── ARCHITECTURE_BOARD_LAYOUT.md
│   ├── PHASE_1_AUDIT.md       # Phase 3 completion audit
│   ├── PHASE_5_PLAN.md        # Future work planning
│   └── REFACTOR_PLAN_RULES_REDUNDANCY.md
│
└── references/                # Original game materials
    └── RULES.txt              # Original rules text
```

### Configuration Flow

**JSON Rules → Python Engine → Gameplay**

```text
missions/u_boat_ruleset_default.json
    ↓
core/action_costs.py (loads AP costs)
core/combat_resolver.py (loads hit tables)
core/turn_manager.py (loads dice rules)
    ↓
core/actions/*.py (execute using loaded rules)
    ↓
Player sees results in game
```

**Key Design Principle:** Python code never contains hardcoded game rules. All rules, thresholds, modifiers, and tables exist in JSON files, making the engine generic and missions fully customizable.
## Testing

The project has comprehensive test coverage with 225+ tests across all systems.

### Running Tests

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python tests/test_combat_resolver.py

# Run with coverage report
python -m pytest tests/ --cov=core --cov-report=html
```

### Test Organization

- **Unit Tests**: Test individual components in isolation
  - `test_action_system.py` - Action queue and base classes
  - `test_movement_actions.py` - Move, rotate, depth actions
  - `test_combat_actions.py` - Combat and repair actions
  - `test_damage_resolution.py` - Damage systems
  - `test_*_validator.py` - All validation systems
  - `test_combat_resolver.py` - Combat resolution
  - `test_range_los.py` - Range and LOS calculations

- **Integration Tests**: Test system interactions
  - `test_phase2_subsystems.py` - Phase 2 validator integration
  - `test_detection_integration.py` - Detection phase flow
  - `test_merchant_integration.py` - Merchant AI integration

- **AI Tests**: Test autonomous systems
  - `test_merchant_ai.py` - Merchant ship movement
  - `test_detection_ai.py` - Detection mechanics
  - `test_escort_ai.py` - Escort ship behavior
  - `test_b24_ai.py` - Aircraft mechanics

- **Scenario Tests**: Full gameplay scenarios
  - `tests/scenarios/test_deck_gun_scenario.py` - Deck gun combat flow
  - `tests/scenarios/test_torpedo_scenario.py` - Torpedo attack flow

See [tests/README.md](tests/README.md) for detailed test documentation.

## Development Utilities

### Map Extraction

Extract mission maps from game PDF:

```powershell
python utils/extract_maps.py
```

This converts each page of the mission maps PDF to PNG format in `assets/maps/`.

### Legacy Editor (Deprecated)

The standalone board editor (`utils/editor.py`) is deprecated in favor of the in-game alignment mode (F2). The editor is kept for reference but should not be used for new work.

**Use F2 alignment mode instead:**
- Press F2 during gameplay to enter alignment mode
- All calibration features available in-game
- Live preview and instant feedback
- Saves to the same JSON format

## Adding New Missions

To create a new mission:

1. **Extract the map image:**
   ```powershell
   python utils/extract_maps.py
   ```
   Place the extracted image in `assets/maps/`

2. **Create mission configuration file:**
   ```python
   # missions/mission_2_config.py
   
   MISSION_INFO = {
       'number': 2,
       'name': 'Mission Name',
       'map_image': 'm2.png',
       'description': 'Mission briefing...'
   }
   
   VALID_HEXES = [(0, 0), (1, 0), ...]  # Define valid hexes
   SHALLOW_HEXES = [...]                 # Shallow water hexes
   LAND_HEXES = [...]                    # Land hexes (impassable)
   
   U_BOAT_START = {
       'position': (5, 10),
       'facing': 'N',
       'depth': 'PERISCOPE'
   }
   
   SHIPS_START = [...]                   # Enemy ships
   ```

3. **Align the hex grid:**
   - Run `python main.py --mission 2`
   - Press F2 to enter alignment mode
   - Use arrow keys to align hex grid with map
   - Press L to save calibration to `missions/mission_2_layout.json`

4. **Create mission briefing and rules (optional):**
   - `missions/mission_2_briefing.json` - Story and objectives
   - `missions/mission_2_rules.json` - Mission-specific rule overrides

5. **Test:**
   ```powershell
   python main.py --mission 2
   ```

## Documentation

- **User Documentation:**
  - [README.md](README.md) - This file (getting started, architecture)
  - [RULES.md](RULES.md) - Player-facing game rules
  - [docs/ALIGNMENT_MODE_CONTROLS.md](docs/ALIGNMENT_MODE_CONTROLS.md) - Calibration controls

- **Developer Documentation:**
  - [tests/README.md](tests/README.md) - Test suite documentation
  - [missions/mission_schema.md](missions/mission_schema.md) - JSON format reference
  - [missions/README_METADATA.md](missions/README_METADATA.md) - Mission system guide
  - [docs/ARCHITECTURE_BOARD_LAYOUT.md](docs/ARCHITECTURE_BOARD_LAYOUT.md) - Layout engine design
  - [docs/PHASE_1_AUDIT.md](docs/PHASE_1_AUDIT.md) - Phase 3 completion audit
  - [docs/REFACTOR_PLAN_RULES_REDUNDANCY.md](docs/REFACTOR_PLAN_RULES_REDUNDANCY.md) - JSON refactoring plan

## Technical Details

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
# Type Hints

The codebase uses Python type hints extensively for better code quality and IDE support:

```python
def hex_to_pixel(hex_coord: HexCoord) -> Tuple[float, float]:
    """Convert hex coordinate to pixel position."""
    ...
```

Type checking:
```powershell
pip install mypy
mypy core/
```

### Hex Coordinate System

The game uses **axial coordinates** for hex positioning:
- **q**: Column (left/right)
- **r**: Row (diagonal)

Hex directions are flat-top oriented (N/NE/SE/S/SW/NW).

### Performance

- Rendering capped at 60 FPS
- Hex calculations optimized for flat-top orientation
- Assets loaded once at startup
- JSON rules parsed once per game initialization

## Credits

- **Original Game**: Lone U-Boat board game by Forsage Games
- **Implementation**: Digital adaptation for personal/educational use
- **Engine**: Pygame
- **Language**: Python 3.11+

## License

This is a personal implementation of the board game for educational purposes. All game rules and artwork belong to the original publisher.

---

**Last Updated**: January 13, 2026  
**Version**: 0.4.0 (JSON Rules Engine Complet