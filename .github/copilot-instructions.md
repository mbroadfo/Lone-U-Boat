# LoneUBoat — GitHub Copilot Project Instructions

## What This Project Is
A solitaire hex-grid U-boat game built in Python with pygame. The player controls a WWII U-boat against AI-driven escorts and merchants across turn-based phases. All game logic is sound and tested. Current work is a UX overhaul.

## Tech Stack
- Python 3.13, pygame 2.6
- No external game frameworks — all rendering is custom pygame draw calls
- Screen: 1600×900, three-panel layout (left panel | game board | right panel)

## Three-Panel Layout — CRITICAL RULES

```
┌──────────────────┬──────────────────────┬─────────────────┐
│  LEFT PANEL      │   GAME BOARD         │  RIGHT PANEL    │
│  750px           │   600px              │  250px          │
│  _draw_left_     │   _draw_game_board() │  _draw_right_   │
│  panel()         │   DO NOT TOUCH       │  panel()        │
└──────────────────┴──────────────────────┴─────────────────┘
```

**The game board (center 600px) is FROZEN.** The hex grid sizing, offsets, and calibration constants in `config/board_config.py` took significant effort to align with the mission map images. Do not modify:
- `HEX_GRID` dict (size, cols, rows, offset_x, offset_y)
- `CALIBRATION_MAP_POSITION`
- `GLOBAL_BOARD_OFFSET`
- Any STATUS_BOXES rect values

You MAY adjust: `LEFT_PANEL_WIDTH`, `RIGHT_PANEL_WIDTH`, font sizes, panel rendering logic.

## Key Files
| File | Purpose |
|------|---------|
| `core/screens/unified_game.py` | Main game screen (~6900 lines) — all rendering |
| `core/screens/base_screen.py` | Base class, fonts |
| `config/board_config.py` | Layout constants, colors, hex grid config |
| `core/game_state.py` | Game logic |
| `core/models.py` | GamePhase enum, Depth, Facing, HexCoord, Ship |
| `missions/mission_X_layout.json` | Per-mission map calibration |

## Turn Phase Order
1. **U-Boat Phase** — player rolls AP dice, spends AP on actions
2. **Merchant Phase** — merchants move (AI)
3. **Detection Phase** — escorts/merchant check for U-boat
4. **Escort Phase** — escorts roll die table, move and attack
5. **B24 Aircraft Phase** — bomber AI
6. **End Turn Events** — random event table (2d6)

## AP System
- Roll 3d6, take highest + 1 (captain bonus) = Action Points
- Each action costs AP (move=1, rotate=1, dive/surface=1-2, torpedo=variable)
- AP displayed as D6 pip faces, live decrement as AP spent

## UX Redesign — Active Work (Strangler Fig Pattern)
A full UX overhaul is in progress using the strangler fig pattern. A `NEW_UI` feature flag in `config/board_config.py` gates new vs old rendering. Build new components alongside old ones — do not delete old code until the new version is validated.

### What Is Being Built
1. **Dice tray** (right panel top) — large animated D6 pip faces, player-colored, context-sensitive per phase
2. **Civ VI-style context button** (right panel bottom) — large, label changes by state
3. **Phase rules accordion** (left panel) — collapsible per-phase rules, auto-expands on phase change
4. **Play-by-play log** (left panel, below accordion) — scrollable, bold phase headers

### Player Die Colors (RGB)
- U-boat: `(150, 160, 175)` — steel gray
- Escort: `(220, 80, 60)` — red/orange
- Merchant: `(180, 150, 90)` — tan/brown
- Gun/torpedo resolution: `(220, 200, 60)` — yellow

### Dice Tray Context Per Phase
- U-boat phase: remaining AP as D6 faces, maxed-first split (e.g. 7 AP = [6][1])
- Detection phase: escort detection dice
- Merchant phase: merchant dice (if applicable)
- Escort phase: escort combat dice

### Strangler Fig Pattern
```python
# In config/board_config.py — add:
NEW_UI = False  # Flip per-component as validated

# In unified_game.py rendering methods:
if NEW_UI:
    self._draw_dice_tray_new()
else:
    self._draw_dice_section_old()
```

## Abandoned Code Worth Reusing
In `_draw_left_panel()` around lines 1479–1554: commented-out phase accordion sections with `self.expanded_phases` dict already wired up. Resurrect rather than rewrite.

## Coding Conventions
- Methods follow `_draw_<component>()` naming
- Button rects stored as `self.<name>_button_rect` for click detection
- Events logged via `self.add_event(message)` — auto-scrolls log
- Colors defined as RGB tuples, semi-transparent surfaces use RGBA
