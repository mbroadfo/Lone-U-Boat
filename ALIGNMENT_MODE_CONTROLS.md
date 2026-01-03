# Alignment Mode Controls Reference

## Overview

Press **F2** to toggle alignment mode on/off while in-game. This embedded editor replaces the old `editor.py` with better integration.

---

## ✅ Current Controls (In-Game F2 Mode)

### Alignment Mode Toggle
| Key | Action |
|-----|--------|
| **F2** | Toggle alignment mode on/off |

### Target Selection
| Key | Action |
|-----|--------|
| **Tab** | Switch between hex grid and status boxes |
| **Mouse Click** | Select individual status box (when in status box mode) |

### Position Adjustment (Arrow Keys)
| Key | Action |
|-----|--------|
| **Arrow Keys** | Move selected element 1 pixel at a time |
| **Shift + Arrow** | Move selected element 10 pixels at a time (fast) |

### Size Adjustment (+/- Keys)
| Key | Action |
|-----|--------|
| **+ or =** | Increase size by 0.1 |
| **- or _** | Decrease size by 0.1 |
| **Shift + +** | Increase size by 0.5 (fast) |
| **Shift + -** | Decrease size by 0.5 (fast) |

**Note:** When on hex grid target, this scales hex size. When on status boxes with a box selected, this scales that specific box.

### Save/Load
| Key | Action |
|-----|--------|
| **P** | Print current calibration to console |
| **L** | Save calibration to `missions/mission_X_layout.json` |

### Display Toggles (Work in alignment mode)
| Key | Action |
|-----|--------|
| **G** | Toggle hex grid overlay on/off |
| **M** | Toggle map image on/off |
| **V** | Toggle terrain overlay on/off |
| **S** | Toggle status markers on/off |

### U-Boat Movement (For testing positions)
| Key | Action |
|-----|--------|
| **Q** | Rotate U-boat left |
| **E** | Rotate U-boat right |
| **W** | Move U-boat forward |
| **Z** | Increase depth (go deeper) |
| **X** | Decrease depth (go shallower) |

### Window Controls
| Key | Action |
|-----|--------|
| **F11** | Toggle fullscreen |
| **ESC** | Exit to main menu |

---

## ❌ Missing from Old Editor (Not Yet Implemented)

These features from `editor.py` are **not yet** in F2 alignment mode:

### Not Implemented
| Key | Old Editor Feature | Status |
|-----|-------------------|--------|
| **T** | Toggle torpedo loading (for marker testing) | ❌ Not implemented |
| **P** (alternate) | Print mission hexes layout | ❌ Different - now prints calibration |
| **O** | Print calibration values | ✅ Now done with **P** key |
| **Shift+Click** | Add hex to mission layout | ❌ Not implemented |
| **Ctrl+Click** | Remove hex from mission layout | ❌ Not implemented |
| **Alt+Drag** | Detect status box coordinates | ❌ Not implemented |
| **Click+Drag** (grid) | Move hex grid by dragging | ❌ Not implemented |

### Why These Were Removed

1. **Torpedo testing (T)** - Can be tested in actual gameplay instead
2. **Print mission hexes (P)** - Mission hex layouts are static in config, rarely change
3. **Add/Remove hexes** - Mission layouts are static, defined in mission configs
4. **Detect box coordinates** - No longer needed; positions stored in JSON and adjusted with arrow keys
5. **Drag to move** - Arrow keys with Shift are more precise and consistent

---

## 🎯 Typical Alignment Workflow

### Initial Calibration
1. Start mission
2. Press **F2** - enter alignment mode
3. Press **G** - ensure hex grid is visible
4. Press **S** - ensure status markers are visible

### Align Hex Grid
1. Ensure **Tab** target is on "grid" (check debug overlay)
2. Use **+ / -** to scale hex size to match map hexes
   - Use **Shift + / -** for faster scaling
3. Use **Arrow Keys** to position the grid
   - Use **Shift + Arrow** to move faster
4. Fine-tune with regular arrow keys

### Align Status Boxes
1. Press **Tab** to switch to status boxes
2. **Click** on a status box to select it
3. Use **Arrow Keys** to position it precisely
4. Use **+ / -** to scale if needed
5. Repeat for each box that needs adjustment

### Save Your Work
1. Press **P** - verify calibration in console
2. Press **L** - save to `missions/mission_X_layout.json`
3. Press **F2** - exit alignment mode and continue playing

---

## 📊 Debug Overlay (Visible in Alignment Mode)

Shows in top-right corner:
- Current screen size
- Scale factor
- Hex size (in pixels)
- Hex grid origin (screen coordinates)
- Map rect position
- Selected status box info (if any)
  - Box name
  - Position (x, y)
  - Size (width × height)

---

## 💡 Pro Tips

### Precision Alignment
- Use **Shift+Arrow** to get close quickly
- Switch to regular **Arrow Keys** for pixel-perfect positioning
- Watch the event log (right panel) for coordinate feedback

### Testing Alignment
- Press **G/M/S** to toggle layers and verify alignment
- Move U-boat (**Q/E/W**) to test hex positions
- Check all status boxes by clicking each one

### Multi-Resolution Testing
1. Align at your preferred resolution
2. Press **F11** to test fullscreen
3. Resize window (drag edges) to test scaling
4. Alignment should maintain across all sizes

### Saving Strategy
- Press **P** frequently to check progress
- Press **L** only when satisfied with alignment
- JSON file is overwritten each save
- Keep backups if experimenting heavily

---

## 🔧 Technical Notes

### Coordinate System
- All calibration stored in **map-relative coordinates**
- Layout engine converts to screen coordinates at runtime
- This makes calibration resolution-independent

### File Location
Calibration saved to: `missions/mission_X_layout.json`

### Backward Compatibility
If no layout JSON exists, game falls back to legacy `board_config.py` constants and creates default JSON on first save.

---

## 🆚 Old Editor vs New F2 Mode

| Feature | Old `editor.py` | New F2 Mode |
|---------|----------------|-------------|
| Launch | Separate command | In-game (F2) |
| Live Preview | ❌ No | ✅ Yes |
| Integration | Separate app | Embedded |
| Controls | Complex | Streamlined |
| Hex Layout Editing | ✅ Yes | ❌ No (static) |
| Status Box Scaling | Via multipliers | ✅ Direct size control |
| Coordinate Detection | Drag rectangle | ✅ Click + arrow keys |
| Save Feedback | Console only | ✅ Event log + console |

---

*For architecture details, see `ARCHITECTURE_BOARD_LAYOUT.md`*
