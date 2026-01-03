# Quick Start: Using the New Board Layout System

## For Players

### Normal Gameplay
Everything works as before! The changes are under the hood.

- Start the game normally
- Press **F11** for fullscreen - map/hexes scale automatically
- Resize window - everything adjusts smoothly

### If Something Looks Misaligned

1. Press **F2** to enter Alignment Mode
2. Turn on displays: **G** (grid), **M** (map), **S** (status boxes)
3. See instructions below to fix alignment
4. Press **F2** again to exit and play

## For Developers / Calibrating New Maps

### Quick Calibration Workflow

1. **Start the game** with the mission you want to calibrate
   ```bash
   python main.py
   ```

2. **Enter Alignment Mode**: Press **F2**
   - Event log shows: "ALIGNMENT MODE: Use arrow keys..."
   - Grid and map automatically turn on

3. **Align the Hex Grid** (default mode)
   - Use **Arrow Keys** to move the grid origin
   - Event log shows current position: "Grid origin: (960.0, 303.0)"
   - Move grid until hexes line up with map features

4. **Switch to Status Boxes**: Press **Tab**
   - Event log shows: "Alignment target: status_boxes"
   - All status box outlines appear in cyan

5. **Select a Box**: Click on any status box
   - Selected box highlighted in yellow with corner handles
   - Event log shows: "Selected: torpedo_tube_1"

6. **Adjust Position**: Use **Arrow Keys**
   - Event log shows: "torpedo_tube_1: (1134.3, 162.6)"
   - Repeat for each misaligned box

7. **Print Values** (optional): Press **P**
   - Calibration printed to terminal/console
   - Useful for debugging or manual editing

8. **Save Calibration**: Press **L**
   - Event log confirms: "Calibration saved to mission_1_layout.json"
   - File created in `missions/` directory

9. **Test**: Press **F2** to exit alignment mode
   - Toggle displays to verify alignment
   - Restart game to test persistence

### Keyboard Reference

```
┌────────────────────────────────────────────────┐
│         ALIGNMENT MODE CONTROLS (F2)           │
├────────────┬───────────────────────────────────┤
│ F2         │ Toggle alignment mode on/off      │
│ Tab        │ Switch grid ↔ status box mode     │
│ Arrow Keys │ Adjust position (map pixels)      │
│ Click      │ Select status box                 │
│ P          │ Print calibration to console      │
│ L          │ Save to mission_N_layout.json     │
├────────────┴───────────────────────────────────┤
│         DISPLAY TOGGLES (always active)        │
├────────────┬───────────────────────────────────┤
│ G          │ Toggle hex grid overlay           │
│ M          │ Toggle map display                │
│ S          │ Toggle status boxes               │
│ V          │ Toggle terrain overlay            │
│ F11        │ Toggle fullscreen                 │
│ ESC        │ Exit to menu / quit               │
└────────────┴───────────────────────────────────┘
```

## Understanding the Files

### `missions/mission_N_layout.json`
This is where calibration is stored. Format:

```json
{
  "map_calibration": {
    "width": 678,      // Map width at calibration time
    "height": 900      // Map height at calibration time
  },
  "hex_grid_calibration": {
    "hex_size": 47.328,              // Hex radius
    "origin_in_map": [960, 303]      // Grid origin from map top-left
  },
  "status_box_calibration": {
    "boxes_in_map": {
      "detection_silent": [689.7, 129.3, 42.1, 42.1],  // x, y, width, height
      // ... more boxes
    }
  }
}
```

**Important**: All coordinates are in **map pixels** at the calibration size, NOT screen pixels.

## Tips & Tricks

### Fine-Tuning
- Arrow keys move by 1 map pixel
- For sub-pixel precision, edit JSON directly
- Test at multiple resolutions (windowed, fullscreen, 4K)

### Bulk Adjustments
- If everything is off by same amount, adjust grid origin first
- This shifts all hexes together
- Then fine-tune individual status boxes

### Backup Before Editing
```bash
cp missions/mission_1_layout.json missions/mission_1_layout.json.backup
```

### Reverting Changes
- Delete the JSON file
- Game falls back to legacy config from board_config.py
- Or restore from backup

### Checking Alignment
1. Turn on all displays (G, M, S, V)
2. Look for:
   - Hex corners at terrain boundaries
   - Status boxes centered on their icons
   - Grid spacing matches map features
3. Test at different screen sizes

## Common Issues

### "Layout file not found" error
**Cause**: No mission_N_layout.json for this mission  
**Fix**: Enter alignment mode and press L to create it

### Grid is way off
**Cause**: Wrong calibration or map size changed  
**Fix**: 
1. Check map_calibration width/height matches actual map
2. Re-align from scratch
3. Delete JSON and let game create new from legacy config

### Status boxes disappeared
**Cause**: Either hidden (S key) or coordinates are off-screen  
**Fix**:
1. Press S to toggle status boxes on
2. Enter alignment mode to see outlines
3. Re-position boxes back into view

### Changes don't persist
**Cause**: Not pressing L to save, or file permissions issue  
**Fix**:
1. Always press L after adjustments
2. Check missions/ directory is writable
3. Look for error messages in console

### Alignment breaks after fullscreen
**Cause**: Bug in resize handling (shouldn't happen with new system)  
**Fix**:
1. Report as bug
2. Restart game as workaround
3. Check ScreenManager handles VIDEORESIZE events

## Advanced: Manual JSON Editing

If you need to batch-edit or copy calibrations:

```python
# Example: Shift all status boxes right by 10 pixels
import json

with open('missions/mission_1_layout.json', 'r') as f:
    data = json.load(f)

boxes = data['status_box_calibration']['boxes_in_map']
for name, (x, y, w, h) in boxes.items():
    boxes[name] = [x + 10, y, w, h]  # Shift right by 10

with open('missions/mission_1_layout.json', 'w') as f:
    json.dump(data, f, indent=2)
```

## Help & Support

- **Documentation**: See BOARD_LAYOUT_SYSTEM.md for architecture details
- **Code**: Check comments in board_layout.py for API usage
- **Debugging**: Press P in alignment mode to see current values
- **Issues**: Check console/terminal for error messages

## Summary

New system = **Easier calibration, automatic scaling, no external tools**

Old workflow:
1. Run separate editor.py
2. Adjust values
3. Manually edit board_config.py
4. Restart to test
5. Repeat until perfect

New workflow:
1. Press F2 in game
2. Use arrows to adjust
3. Press L to save
4. Press F2 to test immediately

**Much faster and more intuitive!**
