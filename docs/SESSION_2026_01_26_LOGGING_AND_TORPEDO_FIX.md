# Gameplay Improvements: Event Logging & Torpedo Preview State

**Date:** January 26, 2026  
**Tests:** All 255 tests passing

## Summary

Comprehensive improvements to gameplay event logging and a critical bug fix for torpedo action queueing. These changes enhance gameplay clarity and fix a frustrating UX issue where players couldn't queue fire-then-load torpedo actions in the same turn.

---

## 1. Event Logging Improvements (10 Features)

### Standardized Dice Roll Formatting
**Change:** All dice rolls now use bracket notation
- Single die: `[4]` instead of "rolled 4"
- Two dice: `[3,5]` instead of "rolled 3, 5"  
- Three dice: `[2,4,6]` instead of "rolled 2, 4, 6"

**Files Modified:**
- [core/turn_manager.py](core/turn_manager.py#L281-L286) - AP roll formatting
- [core/detection_ai.py](core/detection_ai.py#L248-L281) - Detection roll formatting
- [core/merchant_ai.py](core/merchant_ai.py#L205-L210) - Damaged merchant movement rolls
- [core/damage/uboat_damage.py](core/damage/uboat_damage.py#L477-L623) - Damage chart rolls
- [core/event_system.py](core/event_system.py#L92-L175) - End turn event rolls

### Turn Separators
**Change:** Added visual separators between turns
```
[TURN] ------------------------------------------------------------
[TURN] Turn 3 Beginning
[TURN] ------------------------------------------------------------
```

**File:** [core/game_state.py](core/game_state.py#L581-L584)

### Mission Restart Markers
**Change:** Added clear markers when mission restarts
```
================================================================
[MISSION RESTARTED]
================================================================
```

**File:** [core/screens/unified_game.py](core/screens/unified_game.py#L67-L75)

### Turn/Phase Context Markers
**Change:** Created event logger system with `[T2:ESCORT]` format markers

**File:** [core/event_logger.py](core/event_logger.py) - **NEW FILE**
- Centralized logging with turn/phase context
- Standardized dice formatting functions
- Indentation support for nested events

### Additional Improvements
- Depth charge damage rolls now logged with dice shown
- Detection roll context shows dice type and target
- B-24 attack rolls properly logged
- All critical hit sub-table rolls visible

---

## 2. Torpedo Tube Repair Cost Bug Fix

**Problem:** Torpedo tube repairs cost only 2 AP when submerged with engineer (should be 4 AP).

**Root Cause:** Hardcoded `2` in modulo cost calculations ignored the component's actual `ap_cost` field.

**Fix:** Changed 5 locations in [core/screens/unified_game.py](core/screens/unified_game.py) to use dynamic `base_cost`:
- Line 5305: Get `base_cost` from tube's `ap_cost` field
- Line 5319: Use `base_cost` instead of hardcoded `2`
- Line 5363: Calculate with `base_cost` from tube
- Lines 5450, 5468: Display actual `base_cost` in UI

**Impact:** Repairs now correctly cost 4 AP when submerged with engineer.

---

## 3. Torpedo Loading Preview State Bug Fix ⭐ MAJOR

**Problem:** Players couldn't queue "Load Torpedoes" after "Fire Torpedoes" in the same turn because validation checked **current** state (tubes LOADED) instead of **preview** state (tubes EMPTY after fire executes).

### Example Scenario (Before Fix)
1. Player has all torpedo tubes LOADED
2. Player queues "Fire Tubes 1, 2, 3" (costs 2 AP)
3. Player tries to queue "Load Tubes 1, 2" (costs 1 AP)
4. ❌ **Validation fails:** "Tube 1 is already loaded"

### Solution
Extended preview state simulation in [core/actions/action_queue.py](core/actions/action_queue.py#L55-L92) to track torpedo tube states through queued actions.

**Implementation:**
1. Import FireTorpedoAction, LoadTorpedoAction, deepcopy, TubeState
2. Create `preview_uboat` using deepcopy of game_state.u_boat
3. Simulate ALL queued action effects:
   - Depth changes → update simulated_depth
   - Fire torpedoes → set fired tubes to EMPTY
   - Load torpedoes → set loaded tubes to LOADED
4. Create `preview_game_state` with simulated u_boat
5. Validate new action against preview state

**Files Modified:**
- [core/actions/action_queue.py](core/actions/action_queue.py#L55-L92) - Complete rewrite of validation logic

**Testing:**
- ✅ All 255 tests passing
- ✅ New test script: [test_fire_then_load.py](test_fire_then_load.py)
- ✅ Can now queue Fire → Load in same turn
- ✅ Can now queue Load → Fire → Load sequences

### Benefits
- **Better UX:** Plan complete action sequences in one turn
- **No artificial restrictions:** Have enough AP? Queue both actions!
- **Extensible:** System now handles depth, torpedo firing, and loading
- **Test compatible:** Uses `getattr()` for backward compatibility

---

## 4. Type Hint Fixes

**Problem:** `core/event_logger.py` had missing type hints.

**Fix:** Added proper type hints:
- Line 11: Changed import from `Optional` to `List`
- Line 64: Added `lines: List[str] = []`
- Lines 83-90: Added `results: List[int]` parameters

**File:** [core/event_logger.py](core/event_logger.py#L11-L90)

---

## 5. B-24 Damage Resolver Bug Fix

**Problem:** Tests failed with `.capitalize()` called on None when `ship_type` was None.

**Fix:** Added explicit B-24 attack case in [core/damage/uboat_damage.py](core/damage/uboat_damage.py#L487-L490):
```python
elif attack_type == "b24":
    chart_roll = self.dice.roll_1d6()
    print(f"[DAMAGE] B-24 attack: rolled 1d6 [{chart_roll}]")
```

---

## Test Results

```
================= 255 passed in 5.25s =================

✅ test_action_system.py ......... (8 tests)
✅ test_b24_ai.py ................ (26 tests)
✅ test_combat_actions.py ........ (9 tests)
✅ test_combat_resolver.py ....... (11 tests)
✅ test_damage_resolution.py ..... (11 tests)
✅ test_depth_validator.py ....... (9 tests)
✅ test_detection_ai.py .......... (16 tests)
✅ test_escort_ai.py ............. (41 tests)
✅ test_event_system.py .......... (24 tests)
✅ test_merchant_ai.py ........... (14 tests)
✅ test_repair_system.py ......... (21 tests)
✅ test_torpedo_validator.py ..... (11 tests)
... and 12 more test files
```

---

## Files Changed

**Modified (10 files):**
- `core/actions/action_queue.py` - Preview state simulation
- `core/damage/uboat_damage.py` - B-24 fix + damage roll logging
- `core/detection_ai.py` - Detection roll formatting
- `core/event_system.py` - Event roll formatting
- `core/game_state.py` - Turn separator logging
- `core/merchant_ai.py` - Merchant roll formatting
- `core/screens/unified_game.py` - Repair cost fix + mission restart marker
- `core/turn_manager.py` - AP roll formatting
- `tests/test_event_system.py` - Mock dice for 2d6 tests
- `tests/test_merchant_ai.py` - Bracketed roll assertions

**Created (2 files):**
- `core/event_logger.py` - **NEW:** Centralized event logging system
- `test_fire_then_load.py` - **NEW:** Torpedo preview validation test

**Documentation:**
- `TORPEDO_PREVIEW_FIX.md` - Detailed explanation of preview state fix

---

## Backward Compatibility

✅ All changes maintain backward compatibility:
- Preview state uses `getattr()` with defaults for test mocks
- Event logger is optional - not required by existing code
- Dice formatting changes are cosmetic (output only)
- Cost calculation changes are internal

---

## Future Work

The preview state system is now extensible for future action types:
- Could simulate repairs for component state checking
- Could simulate combat for resource consumption
- Could simulate movement for position-based validation
