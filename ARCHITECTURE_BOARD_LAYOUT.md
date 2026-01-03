# Lone U-Boat Board/Layout Architecture

**Goal:** Keep all map, hex grid, and status box positioning board-centric, resolution-independent, and single-sourced through the layout engine. Do not introduce new ad-hoc scaling math in screens or rendering.

---

## 1. Layers & Responsibilities

### Config Layer (`config/board_layout_config.py`, mission JSONs)

**Purpose:** Define calibration in map coordinates (not screen coordinates).

**Data Structures:**
- `MapCalibration`: width, height of the mission map at reference size
- `HexGridCalibration`: hex_size, origin_in_map (center of reference hex in map pixels)
- `StatusBoxCalibration`: boxes_in_map[name] = (x, y, w, h) in map pixels

**API:**
```python
load_mission_layout(mission_number) -> MissionLayoutConfig
save_mission_layout(mission_number, MissionLayoutConfig)
```

**Rules:**
- ✅ All coordinates in map-relative pixels
- ❌ No screen-space values here
- ❌ No window size dependencies

---

### Runtime Layout Layer (`core/board_layout.py`)

**Purpose:** Convert calibration data to screen-space positions based on current board area.

**Class:** `BoardLayoutRuntime(screen_size, layout_cfg, ui_cfg)`

**Public API:**
```python
recompute(screen_size: tuple[int, int])
    # Recompute positions when window size changes (full-screen case)

recompute_for_board(board_rect: pygame.Rect)
    # Core layout function: board lives inside board_rect
    # All positioning computed relative to this rect

screen_to_map(pos) -> tuple[float, float]
    # Convert screen coords to map coords (for alignment mode)

map_to_screen(pos) -> tuple[float, float]
    # Convert map coords to screen coords

hit_test_status_box(pos) -> Optional[str]
    # Returns box name for alignment/interactions
```

**Public Data:**
```python
scale: float                                    # Uniform scale from map to screen
board_rects.map_rect: pygame.Rect              # Where map is drawn
hex_size: float                                # Hex radius in screen pixels
hex_origin_screen: tuple[float, float]         # Hex grid origin in screen coords
status_box_rects: dict[str, pygame.Rect]       # Status box positions in screen coords
```

**Responsibilities:**
- ✅ Single source of truth for all screen positions
- ✅ Handles aspect ratio preservation
- ✅ Provides coordinate conversions
- ❌ Does not render anything
- ❌ Does not handle input

---

### Game Logic Layer (`core/game_state.py`)

**Purpose:** Own game entities and coordinate between layout, hex grid, and renderer.

**Owns:**
- Mission config & entities (u-boat, ships, mission hexes, terrain)
- `BoardLayoutRuntime` instance
- `HexGrid` instance
- `GameRenderer` instance

**APIs for Screens:**
```python
update_screen_size(new_size: tuple[int, int])
    # Called when window resizes
    # -> layout.recompute(new_size)
    # -> pushes values to hex_grid and renderer

update_board_region(board_rect: pygame.Rect)
    # Called when screen defines where board should be
    # -> layout.recompute_for_board(board_rect)
    # -> pushes values to hex_grid and renderer
```

**Rules:**
- ✅ Delegates all positioning to `layout`
- ✅ Updates `hex_grid` from `layout` values
- ✅ Updates `renderer` with new layout
- ❌ No manual scale math
- ❌ No hardcoded pixel positions

**Example:**
```python
def update_board_region(self, board_rect: pygame.Rect) -> None:
    self.layout.recompute_for_board(board_rect)
    self.hex_grid.size = self.layout.hex_size
    self.hex_grid.offset_x, self.hex_grid.offset_y = self.layout.hex_origin_screen
    self.renderer.update_layout(self.layout)
```

---

### Screen Layer (`screens/unified_game.py`, others)

**Purpose:** UI chrome, panel layout, and defining board area.

**Responsible For:**
- UI chrome & panel layout (top bar, side panels, event log, controls)
- Defining the board rectangle within the screen
- High-level input (ESC, F11, F2, menu navigation)
- Delegating to game/layout for board-related operations

**Pattern:**
```python
def render(self):
    # 1. Calculate panel dimensions
    screen_width = self.screen.get_width()
    screen_height = self.screen.get_height()
    left_width = self.config.LEFT_PANEL_WIDTH
    right_width = self.config.RIGHT_PANEL_WIDTH
    top_height = self.config.TOP_BAR_HEIGHT
    
    board_width = screen_width - left_width - right_width
    board_height = screen_height - top_height
    
    # 2. Define board area
    board_rect = pygame.Rect(left_width, top_height, board_width, board_height)
    
    # 3. Update layout for this board region
    self.game.update_board_region(board_rect)
    
    # 4. Simple render calls (no scaling logic)
    self.game.renderer.render_map(self.game.map_image)
    self.game.renderer.render_hex_grid(self.game.mission_hexes)
    # ... etc
```

**Rules:**
- ✅ Defines "where the board is"
- ✅ Calls `game.update_board_region(board_rect)`
- ❌ Never scales map, hexes, or status boxes directly
- ❌ No calibration math
- ❌ No `adjustment_x/y` calculations

---

### Rendering Layer (`core/renderer.py`)

**Purpose:** Draw everything using positions from `layout`.

**Draws Using:**
- `layout.board_rects.map_rect` - where to draw map
- `layout.hex_origin_screen` / `hex_grid` - where hexes go
- `layout.status_box_rects` - where status boxes go

**Key Methods:**
```python
render_map(map_image)
    # Uses layout.board_rects.map_rect
    # Smoothscales image to fit rect

render_hex_grid(mission_hexes)
    # Uses hex_grid (which was updated from layout)

render_status_markers(status_boxes, show_all)
    # Uses layout.status_box_rects[name]

render_ship(ship), render_u_boat(u_boat)
    # Uses hex_grid.hex_to_pixel()

render_alignment_highlights(target, selected_box)
    # Visual feedback for alignment mode

render_debug_overlay(layout, selected_box)
    # Shows layout info in alignment mode
```

**Rules:**
- ✅ Uses screen-space positions from `layout`
- ✅ "Dumb" rendering - just draws at given positions
- ❌ No scale/offset parameters (except legacy compatibility)
- ❌ No positioning calculations

**If New Element Needs Positioning:**
1. Add it to `MissionLayoutConfig` + `BoardLayoutRuntime`, OR
2. Derive its screen position from existing layout data

---

## 2. Alignment Mode (Embedded Editor)

**Activation:** Press F2 on `UnifiedGameScreen`

**Purpose:** Adjust hex grid and status box positions interactively.

### Controls

| Key | Action |
|-----|--------|
| F2 | Toggle alignment mode on/off |
| Tab | Switch between grid and status boxes |
| Arrow Keys | Adjust selected element position |
| Shift+Arrow | Adjust faster (10x) |
| Click | Select status box |
| P | Print calibration to console |
| L | Save calibration to JSON |

### Data Flow

```
Arrow Key Press
    ↓
Adjust layout_cfg.hex_grid_calib.origin_in_map
   OR
Adjust layout_cfg.status_calib.boxes_in_map[name]
    ↓
layout.recompute_for_board(board_rect)
    ↓
Update hex_grid + renderer
    ↓
Visual feedback (yellow highlights)
    ↓
Press L to save
    ↓
save_mission_layout(mission_number, layout_cfg)
```

### Rules

- ✅ `BoardLayoutRuntime` is the only source of truth
- ✅ Arrow keys adjust calibration data in map coordinates
- ✅ Immediately recompute to see changes
- ✅ Save with L key to persist
- ❌ No separate `editor.py` logic (deprecated)

---

## 3. Rules of Thumb for Future Changes

### If You Catch Yourself Writing `x * scale + offset`...

**STOP.** Instead:
1. Put that concept into calibration data (`MissionLayoutConfig`)
2. Add computation to `BoardLayoutRuntime`
3. Use the computed value from `layout`

### If a Screen Needs to Move or Resize the Board...

Compute a new `board_rect` and call:
```python
game.update_board_region(board_rect)
```

### If Something Needs to Respond to Window Resize...

1. Handle `VIDEORESIZE` in `ScreenManager`
2. Call `update_screen_size()` on current screen/game:
```python
if event.type == pygame.VIDEORESIZE:
    self.screen = pygame.display.get_surface()
    if self.current_screen:
        self.current_screen.update_screen(self.screen)
```

### When Adding New Missions...

1. Create `missions/mission_N_layout.json` by copying existing one
2. Start the mission
3. Press F2 for alignment mode
4. Use arrow keys to adjust positions
5. Press L to save

**DO NOT:**
- ❌ Add mission-specific constants to `board_config.py`
- ❌ Write custom scaling logic in screens
- ❌ Hardcode pixel positions anywhere

---

## 4. Current Architecture State

### ✅ Implemented & Working

- [x] Board-centric layout engine (`BoardLayoutRuntime`)
- [x] Single source of truth for positions
- [x] Resolution-independent scaling
- [x] JSON-based calibration storage
- [x] Window resize support (`VIDEORESIZE`)
- [x] Embedded alignment mode (F2)
- [x] Debug overlay showing layout info
- [x] Simplified screen rendering (no scaling logic)
- [x] `Game.update_board_region()` API
- [x] Coordinate conversion utilities

### ⚠️ Legacy/Cleanup Needed

**Low Priority (works but inconsistent):**

1. **`render_ship()` / `render_u_boat()` scale parameters**
   - Currently: Still have unused `scale` parameter for compatibility
   - Should: Remove scale parameter (positions come from layout)
   - Impact: Minimal - just cleanup

2. **Status box data duplication**
   - Currently: `cfg.STATUS_BOXES` has rects (ignored) + marker types
   - Should: Mark rects as deprecated in comments
   - Impact: None - already using `layout.status_box_rects`

3. **`editor.py` still exists**
   - Currently: Marked deprecated with warning
   - Should: Delete once F2 alignment proven stable
   - Impact: None - F2 mode replaces it

4. **`update_board_region()` called every frame**
   - Currently: Called in `_draw_game_board()` each frame
   - Should: Only call when board rect changes
   - Impact: Tiny performance improvement
   - Note: Not a problem, just inefficient

### ❌ Deprecated (Don't Use)

- ~~`board_config.py`: `CALIBRATION_MAP_POSITION`~~
- ~~`board_config.py`: `GLOBAL_BOARD_OFFSET`~~
- ~~`board_config.py`: `HEX_SCALE_MULTIPLIER`~~
- ~~`board_config.py`: `STATUS_BOX_SCALE_MULTIPLIER`~~
- ~~`editor.py` (use F2 alignment mode instead)~~

---

## 5. Testing Checklist

When making changes, verify:

- [ ] Game starts and map renders correctly
- [ ] Status boxes align with map graphics
- [ ] Hex grid aligns with map hexes
- [ ] F11 fullscreen maintains alignment
- [ ] Window resize updates layout correctly
- [ ] F2 alignment mode activates
- [ ] Arrow keys adjust positions
- [ ] P prints calibration
- [ ] L saves calibration to JSON
- [ ] Debug overlay shows correct info
- [ ] Different resolutions maintain alignment
- [ ] Multiple missions work (test at least 2)

---

## 6. Quick Reference

### Adding a New Visual Element

**Example:** Adding a compass rose overlay

```python
# 1. Add to calibration (if mission-specific)
@dataclass
class CompassCalibration:
    position_in_map: Tuple[float, float]  # Map-relative position
    size: float                           # Size at calibration

# Add to MissionLayoutConfig
compass_calib: CompassCalibration

# 2. Add to BoardLayoutRuntime
def recompute_for_board(self, board_rect):
    # ... existing code ...
    
    # Compute compass screen position
    self.compass_screen_pos = (
        map_x + self.cfg.compass_calib.position_in_map[0] * self.scale,
        map_y + self.cfg.compass_calib.position_in_map[1] * self.scale
    )
    self.compass_size = self.cfg.compass_calib.size * self.scale

# 3. Add to renderer
def render_compass(self):
    if not self.layout:
        return
    pos = self.layout.compass_screen_pos
    size = self.layout.compass_size
    # ... draw compass at pos with size ...
```

### Handling Input on Board Elements

```python
# In screen's handle_events:
def handle_events(self, event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = event.pos
        
        # Use layout for hit testing
        clicked_hex = self.game.hex_grid.pixel_to_hex(*mouse_pos)
        clicked_box = self.game.layout.hit_test_status_box(mouse_pos)
        
        # Handle click...
```

---

## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        ScreenManager                         │
│  - Handles VIDEORESIZE events                               │
│  - Propagates to current screen                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     UnifiedGameScreen                        │
│  - Calculates panel layout                                  │
│  - Defines board_rect                                       │
│  - Calls game.update_board_region(board_rect)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                          Game                                │
│  - Owns: layout, hex_grid, renderer, entities               │
│  - update_board_region(board_rect)                          │
│    └─> layout.recompute_for_board(board_rect)              │
│    └─> hex_grid.size = layout.hex_size                     │
│    └─> renderer.update_layout(layout)                      │
└─────────────┬───────────────────────┬───────────────────────┘
              │                       │
              ▼                       ▼
┌─────────────────────────┐ ┌─────────────────────────────────┐
│  BoardLayoutRuntime     │ │     GameRenderer                │
│  - Single source of     │ │  - render_map()                 │
│    truth for positions  │ │  - render_hex_grid()            │
│  - Converts calibration │ │  - render_status_markers()      │
│    to screen coords     │ │  - render_ship()                │
│  - Handles scaling      │ │  - render_u_boat()              │
│                         │ │  - Uses positions from layout   │
└─────────────────────────┘ └─────────────────────────────────┘
              ▲
              │
┌─────────────────────────┐
│  MissionLayoutConfig    │
│  (JSON)                 │
│  - Map calibration      │
│  - Hex grid calibration │
│  - Status box positions │
│  (all in map coords)    │
└─────────────────────────┘
```

---

## 8. Common Pitfalls to Avoid

### ❌ DON'T: Add scaling logic to screens
```python
# BAD - screen doing layout math
def _draw_game_board(self):
    scale = board_height / map_height
    hex_size = base_hex_size * scale * multiplier
    # ... more math ...
```

### ✅ DO: Let layout handle it
```python
# GOOD - screen just defines frame
def _draw_game_board(self, x, y, width, height):
    board_rect = pygame.Rect(x, y, width, height)
    self.game.update_board_region(board_rect)
    # Layout handles all the math
```

### ❌ DON'T: Hardcode positions
```python
# BAD - magic numbers
status_box_x = 475 + offset_x
```

### ✅ DO: Use layout rects
```python
# GOOD - position from layout
rect = self.layout.status_box_rects['detection_silent']
```

### ❌ DON'T: Store screen positions in config
```python
# BAD - screen-dependent
HEX_ORIGIN_SCREEN = (960, 303)  # What resolution?
```

### ✅ DO: Store map-relative calibration
```python
# GOOD - resolution-independent
"origin_in_map": [480.5, 220.0]  # Map pixels
```

---

## 9. Future Enhancements

### Possible Improvements (Not Required)

1. **Panel-aware layout modes**
   - Different layouts for single-panel vs multi-panel views
   - Layout presets: "compact", "wide", "tall"

2. **Per-resolution calibration overrides**
   - Fine-tune specific resolutions if needed
   - Fallback to base calibration + scaling

3. **Animated board transitions**
   - Smooth zoom when entering/exiting fullscreen
   - Pan animations for board region changes

4. **Multiple board views**
   - Minimap
   - Tactical zoom
   - Both using same layout engine

---

## 10. For AI Assistants (Claude, Copilot, etc.)

When modifying code in this project:

1. **Always use the layout engine** for positioning board elements
2. **Never add manual scaling** in screens or rendering code
3. **Store calibration in map coordinates** in mission JSON files
4. **Use `game.update_board_region()`** when board area changes
5. **Refer to this document** when unsure about architecture

**If a change seems to violate these principles, stop and ask the user.**

---

*Last Updated: January 3, 2026*
*Architecture Version: 2.0 (Board-Centric)*
