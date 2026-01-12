# Torpedo System Implementation Plan

## Overview
Implement torpedo loading and firing system, sharing common features with deck gun (damage resolution, detection, interactive UI) while adding unique torpedo mechanics (tube management, path tracing, aspect-based hits, multi-torpedo salvos).

## Shared Features with Deck Gun
- ✅ Allied Ship Damage Chart (ShipDamageResolver)
- ✅ Detection Level changes
- ✅ Interactive resolution pattern with UI buttons
- ✅ Line of sight and range calculations
- ✅ Multi-target sequential resolution
- ✅ Ship sinking and removal logic

## Unique Torpedo Features
- ✅ 5 torpedo tubes (0-3=front, 4=rear)
- ✅ Load action: tube selection UI
- ✅ Fire 1-3 torpedoes in straight line
- ✅ Path tracing to find all ships in line
- ✅ Aspect-based hit tables (side vs front/rear)
- ✅ Continue-on-miss mechanics
- ✅ Torpedo-specific Detection Level rules (Phase D)

---

## Phase A: Load Torpedoes Action ✅ COMPLETE
**Priority:** Can start first (simpler system)

### Requirements
- AP Cost: 1 AP (Surface), 4 AP (Periscope/Submerged)
- Load up to 2 tubes (1 if Weapons Officer KIA)
- Cannot load already-loaded tubes
- Cannot load damaged tubes (future damage system)
- Display tube status: Empty/Loaded/Damaged

### Implementation Tasks
- [ ] Review existing LoadTorpedoAction class
- [ ] Create tube selection UI (checkboxes or buttons for tubes 1-5)
- [ ] Add depth validation (1 AP vs 4 AP)
- [ ] Add Weapons Officer KIA check (load 1 vs 2)
- [ ] Display tube status in UI panel
- [ ] Validate tube state (not already loaded, not damaged)
- [ ] Update UBoat.torpedo_tubes list on successful load

### UI Mockup
```
Load Torpedoes (1 AP at Surface, 4 AP at Periscope)
Select tubes to load (max 2):
[ ] Tube 1 (Front) - Empty
[ ] Tube 2 (Front) - Loaded
[✓] Tube 3 (Front) - Empty
[✓] Tube 4 (Front) - Empty
[ ] Tube 5 (Rear) - Empty

[Confirm Load] [Cancel]
```

---

## Phase B: Path Tracing Enhancement ✅ COMPLETE
**Priority:** Foundation for firing mechanics

### Requirements
- Fire in straight line from u-boat facing direction
- Front tubes fire forward, rear tube backward
- Range 1-9 hexes
- Find ALL ships along path (not just first)
- Calculate aspect for each ship (side vs front/rear)
- Order ships by distance from u-boat

### Implementation Tasks
- ✅ Enhance existing path tracing in FireTorpedoAction
- ✅ Find all ships along torpedo path (not just first)
- ✅ Calculate aspect for each ship:
  - Side aspect: torpedo direction ±45° of ship's broadside
  - Front/Rear aspect: otherwise
- ✅ Return ordered list of (ship, distance, aspect) tuples
- ✅ Handle empty paths (no ships in line)
- ✅ Land hex blocking

### Aspect Calculation Logic
```python
def calculate_aspect(ship_facing: int, torpedo_direction: int) -> str:
    """
    Returns 'side' if torpedo approaches broadside,
    'front_rear' if approaching bow or stern.
    """
    angle_diff = abs((torpedo_direction - ship_facing) % 6)
    if angle_diff in [1, 2, 4, 5]:  # ±60° or ±120° (broadside)
        return 'side'
    else:  # 0° or 180° (bow/stern)
        return 'front_rear'
```

---

## Phase C: Interactive Torpedo Resolution ✅ COMPLETE
**Priority:** Core combat system

### Requirements
- Fire 1-3 torpedoes at once
- Each torpedo rolls separately against each ship
- Torpedo To-Hit Table (aspect + range based)
- Continue missed torpedoes to next ship
- Reuse ShipDamageResolver for damage
- Interactive UI with roll buttons

### Torpedo To-Hit Table
| Range | Side Aspect | Front/Rear Aspect |
|-------|-------------|-------------------|
| 1-2   | 5+          | 6+                |
| 3-4   | 6+          | 7+                |
| 5-6   | 7+          | 8+                |
| 7-8   | 8+          | 9+                |
| 9     | 9+          | 10+               |

### Implementation Tasks
- ✅ Create TorpedoResolutionState (similar to deck_gun_resolution_state)
- ✅ Validate tubes loaded before firing
- ✅ UI for torpedo count selection (1-3)
- ✅ Check tube count for selected number
- ✅ Roll 1d6 per torpedo per ship (sequential)
- ✅ Apply Torpedo To-Hit Table based on aspect/range
- ✅ Track hits and misses for each torpedo
- ✅ Continue missed torpedoes to next ship
- ✅ Reuse ShipDamageResolver for damage rolls
- ✅ Handle ship sinking mid-resolution
- ✅ Display torpedo status and results

### UI Mockup
```
Firing Torpedoes at Allied Ships

Ship: Merchant (Range 4, Side Aspect)
Torpedoes remaining: 3

Torpedo 1: [Roll to Hit (6+)]
Result: Hit! [Roll Damage (1d6)]
Damage: 5 - Catastrophic! Ship sunk.

Torpedo 2: [Roll to Hit (6+)]
Result: Miss! Continues to next ship...

Torpedo 3: [Roll to Hit (6+)]
Result: Miss! Continues to next ship...

Ship: Corvette (Range 6, Side Aspect)
Torpedoes remaining: 2 (missed from previous)
...
```

---

## Phase D: Detection Level Changes ✅ COMPLETE
**Priority:** Game balance

### Requirements
- +1 DL if fire 3 torpedoes
- +1 DL per torpedo hit
- Maximum +2 DL total from one salvo

### Implementation Tasks
- ✅ Track number of torpedoes fired
- ✅ Track number of torpedo hits
- ✅ Calculate DL change: min(2, (1 if fired_3 else 0) + hit_count)
- ✅ Apply DL change after resolution completes
- ✅ Display DL change in UI

### Logic
```python
def calculate_torpedo_detection_change(torpedoes_fired: int, hits: int) -> int:
    """Returns DL change (max +2)."""
    dl_change = 0
    if torpedoes_fired == 3:
        dl_change += 1
    dl_change += hits
    return min(2, dl_change)
```

---

## Phase E: Tube Management & Polish ✅ COMPLETE
**Priority:** Final integration

### Implementation Tasks
- ✅ Mark fired tubes as empty (implemented in FireTorpedoAction.execute)
- ✅ Tube status display in UI (5 torpedo boxes on game board)
- ✅ Test complete workflow: load → fire → reload
- ✅ Handle edge cases (cannot fire empty tubes, cannot load already-loaded tubes)
- ✅ Validation messages in game log

### Summary
Phase E focuses on verifying the complete torpedo tube lifecycle. All core functionality is implemented:
- Tubes are automatically marked empty when fired
- Visual display exists on game board (5 torpedo boxes)
- Complete workflow tested: load → fire → reload cycles
- Edge cases handled by existing validation
- Clear error messages in game log

---

## Testing Strategy

### Test Scenario 1: Basic Single-Ship
- Load tubes 1-3
- Fire 3 torpedoes at merchant (range 3, side aspect)
- Verify hit rolls (6+), damage rolls, DL changes
- Verify tubes marked empty after firing

### Test Scenario 2: Multi-Ship with Continue
- Load tubes 1-3
- Fire 3 torpedoes with 2 ships in line
- Verify missed torpedoes continue to second ship
- Verify separate aspect/range calculations per ship

### Test Scenario 3: Sinking Mid-Resolution
- Fire torpedoes at two ships
- First ship sinks
- Verify resolution continues to second ship
- Verify first ship removed from map

### Test Scenario 4: Detection Level
- Test firing 1, 2, 3 torpedoes
- Test various hit counts
- Verify DL never exceeds +2

---

## Technical Decisions

### Reuse from Deck Gun System
- ✅ ShipDamageResolver class (no changes needed)
- ✅ Interactive resolution pattern (TorpedoResolutionState)
- ✅ CombatResolver.calculate_los_and_range()
- ✅ Ship sinking and removal logic

### New Components
- 🔜 TorpedoPathTracer class (find all ships in line + aspects)
- 🔜 TorpedoHitCalculator class (apply To-Hit Table)
- 🔜 TubeManager helper (validate/update tube state)

### Code Location
- `core/actions/load_torpedo_action.py` - Load action and UI
- `core/actions/fire_torpedo_action.py` - Fire action and path tracing
- `core/screens/unified_game.py` - Interactive resolution UI (2500+ lines)
- `tests/test_torpedo_scenario.py` - Automated test suite

---

## Implementation Order

### Recommended Sequence
1. **Phase A** (Load Torpedoes) - Simpler, establishes tube UI
2. **Phase B** (Path Tracing) - Foundation for firing
3. **Phase C** (Interactive Resolution) - Core combat mechanics
4. **Phase D** (Detection) - Integration with game state
5. **Phase E** (Polish) - Testing and refinement

### Estimated Timeline
- Phase A: 1-2 days
- Phase B: 1-2 days
- Phase C: 3-4 days (most complex)
- Phase D: 1 day
- Phase E: 2-3 days

**Total: ~2-3 weeks** (similar to deck gun implementation)

---

## Success Criteria

- [ ] Can load 1-2 tubes with correct AP cost
- [ ] Can fire 1-3 torpedoes with tube validation
- [ ] Torpedoes trace straight line and find all ships
- [ ] Aspect calculated correctly per ship
- [ ] Hit rolls use correct To-Hit Table values
- [ ] Missed torpedoes continue to next ship
- [ ] Damage uses Allied Ship Damage Chart
- [ ] Ships sink and are removed
- [ ] Detection Level changes correctly
- [ ] Tubes marked empty after firing
- [ ] All tests pass
- [ ] Zero type errors

---

## Notes
- Tube damage system ready for future damage implementation
- Weapons Officer KIA check ready for future crew system
- Consider adding visual torpedo path animation in future
- May want to add torpedo range indicator in UI
