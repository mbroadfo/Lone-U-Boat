# Board-Centric Layout Refactoring

## Summary

This refactoring completes the transition to a fully board-centric layout system. The layout engine now handles all positioning and scaling relative to a board rectangle, eliminating the "dual brain" problem where both `UnifiedGameScreen` and the layout engine were trying to do layout calculations.

## Key Changes

### 1. Board-Centric Layout Engine

**`BoardLayoutRuntime.recompute_for_board(board_rect)`**
- Core layout algorithm now takes a board rectangle instead of screen size
- All calculations are relative to the board area
- `recompute(screen_size)` is now a thin wrapper that creates a full-screen board rect

**Benefits:**
- Layout engine is independent of screen panels/UI
- Screens define "where the board is" and layout handles "what goes in it"
- Cleaner separation of concerns

### 2. Game.update_board_region() Method

**New API:**
```python
def update_board_region(self, board_rect: pygame.Rect) -> None:
    """Update layout for a specific board region."""
    self.layout.recompute_for_board(board_rect)
    self.hex_grid.size = self.layout.hex_size
    self.hex_grid.offset_x, self.hex_grid.offset_y = self.layout.hex_origin_screen
    self.renderer.update_layout(self.layout)
```

**Usage:**
- Screens call this before rendering the board
- Passes in the board area (after calculating panel sizes)
- Layout engine handles all positioning automatically

### 3. Simplified UnifiedGameScreen._draw_game_board()

**Before (~100 lines):**
- Complex calibration adjustment calculations
- Manual scaling of map, hexes, and status boxes
- Storing/restoring original values
- Fighting with the layout engine

**After (~50 lines):**
```python
def _draw_game_board(self, x, y, width, height):
    board_rect = pygame.Rect(x, y, width, height)
    self.game.update_board_region(board_rect)  # Layout engine handles everything
    
    # Simple render calls - no scaling logic
    self.game.renderer.render_map(self.game.map_image)
    self.game.renderer.render_hex_grid(self.game.mission_hexes)
    # ... etc
```

**Result:**
- Screen just defines the frame and calls renderer
- No manual scaling calculations
- Single source of truth (layout engine)

### 4. Cleaned Up Renderer

**Removed:**
- Legacy `global_offset_x/y` attributes (when layout is present)
- Scale parameters from `render_ship()` and `render_u_boat()`
- Legacy fallback branches in `render_status_markers()`

**Added:**
- `render_debug_overlay()` - shows layout info in alignment mode

**Simplified:**
- `render_status_markers()` always uses layout engine
- `render_ship()` and `render_u_boat()` no longer take scale parameter
- All scaling handled by layout engine

### 5. Deprecated Legacy Code

**board_config.py:**
- Removed `HEX_SCALE_MULTIPLIER`
- Removed `STATUS_BOX_SCALE_MULTIPLIER`
- Removed `CALIBRATION_MAP_POSITION`
- Removed `GLOBAL_BOARD_OFFSET`
- Added deprecation notice

**editor.py:**
- Added large deprecation warning at top
- Directs users to in-game alignment mode (F2)

### 6. Debug Overlay

**New feature in alignment mode:**
- Shows current screen size, scale factor
- Shows hex origin and map rect position
- Shows selected status box details
- Appears as semi-transparent panel in top-right

## Testing Checklist

- [ ] Game starts and map renders correctly
- [ ] Status boxes align with map graphics
- [ ] Hex grid aligns with map hexes
- [ ] F11 fullscreen works, alignment maintained
- [ ] Window resize updates layout correctly
- [ ] F2 alignment mode works
- [ ] Arrow keys adjust positions
- [ ] P prints calibration to console
- [ ] L saves calibration to JSON
- [ ] Debug overlay shows correct info
- [ ] Different resolutions maintain alignment

## Architecture Benefits

### Before
```
UnifiedGameScreen
├─ Calculates calibration adjustments
├─ Manually scales everything
├─ Stores/restores original values
└─ Fights with layout engine

BoardLayoutRuntime
├─ Tries to compute positions
└─ Gets overridden by screen
```

### After
```
UnifiedGameScreen
├─ Defines board area (x, y, width, height)
└─ Calls game.update_board_region(board_rect)

BoardLayoutRuntime (single source of truth)
├─ Fits map into board area
├─ Scales hex grid
├─ Positions status boxes
└─ Provides absolute screen coordinates

Renderer
└─ Draws at computed positions (no scaling logic)
```

## Migration Notes

### For Other Screens
If you add new screens that show the game board:

1. Calculate your panel layout
2. Define board_rect = pygame.Rect(x, y, width, height)
3. Call game.update_board_region(board_rect)
4. Call renderer methods (no scaling needed)

### For Calibration
- All calibration now in `missions/mission_X_layout.json`
- Use in-game alignment mode (F2) to adjust
- No need to touch `board_config.py`

### For New Missions
1. Create `missions/mission_X_layout.json` (copy from mission 1)
2. Adjust using in-game alignment mode
3. Save with L key

## Performance

- Minimal impact: `recompute_for_board()` only called on resize or alignment mode changes
- No per-frame recalculations
- Simpler code paths = faster execution

## Compatibility

- Backwards compatible: game loads legacy config if layout JSON missing
- Existing mission_1_layout.json works unchanged
- Old calibration constants preserved (but marked deprecated)

## Future Enhancements

- [ ] Panel-aware layout (left/right panels in board area calculation)
- [ ] Multiple board modes (full-screen vs multi-panel)
- [ ] Layout presets (compact, wide, tall)
- [ ] Per-resolution calibration overrides
