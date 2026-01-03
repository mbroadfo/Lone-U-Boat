# Board Layout System - Architecture Documentation

## Overview

The board layout system provides resolution-independent positioning for the game map, hex grid, and status boxes. It eliminates hard-coded pixel offsets and manual scaling calculations, replacing them with a single calibration-based layout engine.

## Key Concepts

### 1. **Calibration Space vs Screen Space**

- **Calibration Space**: All positions are stored relative to the map image at a known reference size (e.g., 678×900 pixels)
- **Screen Space**: Runtime positions in the actual window, computed by scaling calibration data

This separation allows the same calibration to work at any screen resolution.

### 2. **Three-Layer Architecture**

```
┌──────────────────────────────────────┐
│  Config Layer (board_layout_config)  │  ← Calibration data (JSON)
├──────────────────────────────────────┤
│  Runtime Layer (board_layout)        │  ← Compute screen positions
├──────────────────────────────────────┤
│  Rendering Layer (renderer)          │  ← Draw at computed positions
└──────────────────────────────────────┘
```

## Components

### `config/board_layout_config.py`

Defines the calibration data structure:

- **MapCalibration**: Map image size at calibration time
- **HexGridCalibration**: Hex size and origin position (in map pixels)
- **StatusBoxCalibration**: Status box rectangles (in map pixels)
- **MissionLayoutConfig**: Bundles all calibration data

Functions:
- `load_mission_layout(mission_number)` - Load from JSON
- `save_mission_layout(mission_number, config)` - Save to JSON

### `core/board_layout.py`

Runtime layout engine:

- **BoardLayoutRuntime**: Computes screen positions from calibration data
  - `recompute(screen_size)` - Recalculate for new window size
  - `screen_to_map(pos)` - Convert screen coords to map coords
  - `map_to_screen(pos)` - Convert map coords to screen coords
  - `hit_test_status_box(pos)` - Find status box at screen position

Properties:
- `scale` - Uniform scale factor from calibration to screen
- `board_rects` - Map rectangle in screen space
- `hex_size` - Hex radius in screen space
- `hex_origin_screen` - Hex grid origin in screen space
- `status_box_rects` - Status box rectangles in screen space

### `missions/mission_N_layout.json`

Per-mission calibration files:

```json
{
  "map_calibration": {
    "width": 678,
    "height": 900
  },
  "hex_grid_calibration": {
    "hex_size": 47.328,
    "origin_in_map": [960, 303]
  },
  "status_box_calibration": {
    "boxes_in_map": {
      "detection_silent": [689.704, 129.348, 42.108, 42.108],
      ...
    }
  }
}
```

## Integration Points

### Game Initialization

```python
# In Game.__init__()
layout_cfg = load_mission_layout(mission_number)
self.layout = BoardLayoutRuntime(
    screen_size=(width, height),
    layout_cfg=layout_cfg,
    ui_cfg=cfg.UI
)

# Configure hex grid from layout
self.hex_grid = HexGrid(
    size=self.layout.hex_size,
    offset_x=self.layout.hex_origin_screen[0],
    offset_y=self.layout.hex_origin_screen[1]
)

# Pass layout to renderer
self.renderer = GameRenderer(..., layout=self.layout)
```

### Window Resize Handling

```python
# In ScreenManager when VIDEORESIZE event occurs
self.current_screen.update_screen(new_screen)

# In UnifiedGameScreen.update_screen()
new_size = (screen.get_width(), screen.get_height())
self.game.update_screen_size(new_size)

# In Game.update_screen_size()
self.layout.recompute(new_size)
self.hex_grid.size = self.layout.hex_size
self.hex_grid.offset_x, self.hex_grid.offset_y = self.layout.hex_origin_screen
self.renderer.update_layout(self.layout)
```

### Rendering

```python
# In GameRenderer
def render_map(self, map_image):
    rect = self.layout.board_rects.map_rect
    scaled = pygame.transform.smoothscale(map_image, (rect.width, rect.height))
    self.screen.blit(scaled, rect.topleft)

def render_status_markers(self, status_boxes, show_all):
    for name, box_data in status_boxes.items():
        rect = self.layout.status_box_rects[name]  # Already in screen space
        # ... draw marker at rect
```

## Alignment Mode (Editor)

Press **F2** in-game to toggle alignment mode for calibrating layouts.

### Controls

| Key | Action |
|-----|--------|
| F2 | Toggle alignment mode on/off |
| Tab | Switch between grid and status box alignment |
| Arrow Keys | Adjust selected element position |
| Click | Select status box (when in status box mode) |
| P | Print current calibration to console |
| L | Save calibration to `mission_N_layout.json` |

### Workflow

1. Start game and press **F2** to enter alignment mode
2. Turn on grid (G) and map (M) displays
3. Use arrow keys to adjust hex grid origin until hexes align with map
4. Press **Tab** to switch to status box mode
5. Click a status box to select it
6. Use arrow keys to adjust its position
7. Press **P** to print calibration (verify values)
8. Press **L** to save to JSON file
9. Press **F2** to exit alignment mode and test

### Visual Feedback

- **Selected status box**: Yellow border with corner handles
- **Unselected boxes** (in status mode): Cyan outlines
- **Event log**: Shows current values as you adjust

## Migration from Legacy System

### Before (board_config.py)

```python
# Hard-coded calibration constants
GLOBAL_BOARD_OFFSET = {'offset_x': 227, 'offset_y': -66}
HEX_GRID = {'size': 32, 'offset_x': 733, 'offset_y': -33}
STATUS_BOXES = {
    'detection_silent': {'rect': (475, 89, 29, 29), ...},
    ...
}

# Manual scaling in renderer
adjusted_rect = pygame.Rect(
    int(rect[0] * scale) + self.global_offset_x,
    int(rect[1] * scale) + self.global_offset_y,
    ...
)
```

### After (new system)

```python
# Load calibration from JSON
layout_cfg = load_mission_layout(1)
layout = BoardLayoutRuntime(screen_size, layout_cfg, ui_cfg)

# Positions computed automatically
hex_size = layout.hex_size
hex_origin = layout.hex_origin_screen
status_rect = layout.status_box_rects['detection_silent']
```

### Key Differences

| Aspect | Legacy | New System |
|--------|--------|------------|
| **Calibration Storage** | Hard-coded in Python | JSON files per mission |
| **Coordinate System** | Mixed screen/calibration | Pure map-relative |
| **Scaling** | Manual multiplication | Automatic via layout engine |
| **Resize Support** | Fixed layout | Dynamic recompute |
| **Editor Integration** | Separate editor.py | Built into game (F2) |
| **Status Box Positions** | Screen pixels + offset | Map pixels, scaled at runtime |

## Benefits

1. **Resolution Independence**: Works at any screen size, from windowed to 4K fullscreen
2. **Single Source of Truth**: Layout engine computes all positions consistently
3. **Easy Calibration**: Adjust values in alignment mode, see changes immediately
4. **Persistent Layouts**: Save calibration once, use forever
5. **Clean Code**: No manual offset calculations scattered through renderers
6. **Editor Built-In**: No separate editor tool, align while playing

## Troubleshooting

### Hexes don't align with map

1. Press F2 to enter alignment mode
2. Use arrow keys to adjust grid origin
3. Press L to save when aligned
4. Restart game to verify

### Status boxes in wrong positions

1. Press F2 → Tab to switch to status box mode
2. Click the misaligned box to select it
3. Use arrow keys to adjust position
4. Press L to save
5. Test by toggling status boxes (S key)

### Layout broken after window resize

Check that:
- `ScreenManager` handles `VIDEORESIZE` events
- `update_screen()` calls propagate to game
- `layout.recompute()` is called with new size

### Legacy calibration not loading

If `mission_N_layout.json` doesn't exist, the game falls back to legacy config. Create initial layout by:
1. Running game
2. Entering alignment mode (F2)
3. Saving with L key

This generates the JSON file from current legacy values.

## Future Enhancements

- [ ] Support for multiple map tiles/zoom levels
- [ ] Undo/redo in alignment mode
- [ ] Batch calibration tools
- [ ] Visual alignment guides (crosshairs, grids)
- [ ] Copy calibration between missions
- [ ] Export/import calibration presets
