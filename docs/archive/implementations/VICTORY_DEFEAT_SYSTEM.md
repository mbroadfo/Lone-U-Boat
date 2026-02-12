# Victory and Defeat System

**Implementation Date:** January 28, 2026  
**Status:** Complete and Tested (13 tests, 100% passing)

## Overview

Complete implementation of Mission 1 victory and defeat conditions according to RULES.md specifications.

## Victory Condition

**EXIT MAP Button** - Player must meet ALL four requirements:

1. **Position:** U-boat ON exit hex (1, 7)
2. **Facing:** U-boat facing SOUTHWEST (toward (0, 8))
3. **Action Points:** AP > 0 remaining this turn
4. **Objective:** All merchants destroyed

**UI Behavior:**
- Button appears as last action button in action panel
- Green when all conditions met (clickable)
- Gray when conditions not met (shows reason on click)
- Uses preview state (checks after queued actions execute)

**Implementation:**
- `game_state.py`: `can_exit_map()` validates all 4 conditions
- `game_state.py`: `trigger_victory()` ends game with defeat_reason=None
- `unified_game.py`: EXIT MAP button rendering with preview state
- `unified_game.py`: Victory screen overlay displays mission stats

## Defeat Conditions

### 1. U-boat Destroyed (Hull Damage 4/4)

**Trigger:** Hull damage reaches maximum (4 points)

**Detection:** `escort_ai.damage_resolver.check_destruction(u_boat)`

**Implementation:**
- `game_state.py`: `_check_game_over_conditions()` checks hull damage
- Sets `defeat_reason = 'destroyed'`
- Sets `running = False`

**UI:** Defeat screen shows destruction reason and final stats

### 2. Merchant Escapes Map

**Trigger:** Merchant ship reaches exit hex (mission objective failure)

**Detection:** `merchant_ai.check_merchant_exit(ships)` during Merchant Phase

**Implementation:**
- `game_state.py`: `_execute_merchant_phase()` checks for exited merchants
- Removes escaped merchants from ships list
- `_trigger_merchant_escape_defeat()` sets `defeat_reason = 'merchant_escaped'`
- Sets `running = False`

**UI:** Defeat screen shows mission objective failure message

### 3. Crew KIA (NOT a Defeat)

**Important:** Per RULES.md, crew deaths do NOT cause game loss

**Verified:** Test confirms game continues with all crew killed

**Rule Quote:** "You do not lose just because all six of the key crew members... are Killed in Action"

## Defeat Reason Tracking System

**Purpose:** Distinguish between victory and different defeat types for proper UI display

**Flag:** `game.defeat_reason`
- `None` = Victory (EXIT MAP button pressed)
- `'destroyed'` = U-boat hull destroyed
- `'merchant_escaped'` = Mission objective failed

**Usage:**
```python
# Check for victory vs defeat
is_victory = game.defeat_reason is None

# Show appropriate message
if is_victory:
    show_victory_screen()
elif game.defeat_reason == 'destroyed':
    show_defeat_destroyed_screen()
elif game.defeat_reason == 'merchant_escaped':
    show_defeat_mission_failed_screen()
```

## Game Over Flow

1. **Victory or Defeat Triggered**
   - Set `game.running = False`
   - Set `game.defeat_reason` appropriately

2. **Screen Behavior**
   - `unified_game.py`: `update()` detects `game.running == False`
   - Pauses game state updates (freeze)
   - Continues rendering screen with overlay

3. **Overlay Display**
   - `_draw_game_over_overlay()` renders semi-transparent overlay
   - Shows MISSION SUCCESS or MISSION FAILED header
   - Displays reason, stats, and "Press ESC to return to menu"

4. **Exit**
   - ESC key returns to main menu
   - Game instance destroyed

## Code Locations

### Core Game State
- [core/game_state.py](../core/game_state.py#L51): `defeat_reason` flag initialization
- [core/game_state.py](../core/game_state.py#L619-L657): `can_exit_map()` with preview state
- [core/game_state.py](../core/game_state.py#L699-L709): `trigger_victory()` method
- [core/game_state.py](../core/game_state.py#L685-L697): `_check_game_over_conditions()` for U-boat destruction
- [core/game_state.py](../core/game_state.py#L383-L417): Merchant escape defeat handling

### UI Implementation
- [core/screens/unified_game.py](../core/screens/unified_game.py#L147): Exit button rect initialization
- [core/screens/unified_game.py](../core/screens/unified_game.py#L3353-L3387): EXIT MAP button rendering
- [core/screens/unified_game.py](../core/screens/unified_game.py#L480-L500): Exit button click handler
- [core/screens/unified_game.py](../core/screens/unified_game.py#L773-L778): Update pause on game over
- [core/screens/unified_game.py](../core/screens/unified_game.py#L838-L905): Game over overlay rendering

### Mission Configuration
- [missions/mission_1_config.py](../missions/mission_1_config.py#L115-L116): Exit hex and facing constants

## Test Coverage

**File:** [tests/test_victory_loss_conditions.py](../tests/test_victory_loss_conditions.py)

**13 Tests (100% Passing):**

### Loss Conditions (3 tests)
- ✅ U-boat destroyed at hull 4/4
- ✅ Merchant escapes to exit hex
- ✅ Crew KIA does NOT cause loss (correct behavior)

### Victory Conditions (6 tests)
- ✅ All conditions met → victory
- ✅ Wrong position → cannot exit
- ✅ Wrong facing → cannot exit
- ✅ No AP → cannot exit
- ✅ Merchants alive → cannot exit
- ✅ Preview state works correctly

### Defeat Reason Tracking (4 tests)
- ✅ Starts as None
- ✅ Set to 'destroyed' on U-boat destruction
- ✅ Set to 'merchant_escaped' on merchant escape
- ✅ Remains None on victory

## Rules Verification

All conditions verified against [RULES.md](../RULES.md):

1. ✅ **Loss: U-boat Destroyed** (RULES.md line 56)
   > "You lose immediately if your U-Boat is destroyed"

2. ✅ **Loss: Merchant Escapes** (RULES.md line 571)
   > "If a Ship Moves off the Map... you lose the game if the Objectives required you to destroy it"

3. ✅ **Victory: Complete Objectives**
   > Mission 1 briefing: "Destroy the Merchant Ship before it exits the map, then exit the map in the direction of the red arrow"

4. ✅ **NOT a Loss: Crew KIA** (RULES.md line 56)
   > "You do not lose just because all six of the key crew members... are Killed in Action"

## Future Missions

The system is designed for extensibility:

**Per-Mission Configuration:**
```python
# missions/mission_N_config.py
U_BOAT_EXIT_HEX = (x, y)
U_BOAT_EXIT_FACING = 'DIRECTION'
```

**Multiple Exit Points:**
- Current system checks single exit hex/facing
- Can be extended to list of valid exit configurations

**Variable Objectives:**
- Merchant count check can be replaced with custom objective validation
- `can_exit_map()` can call mission-specific objective checker

## Known Limitations

1. **Single Exit Point:** Mission 1 has one exit hex/facing
2. **Binary Merchant Check:** All-or-nothing merchant destruction
3. **No Time Limit:** No turn-based failure condition (yet)

## Maintenance Notes

**If Adding New Defeat Conditions:**
1. Add new defeat_reason string (e.g., 'out_of_time')
2. Set flag when condition triggered
3. Update `_draw_game_over_overlay()` to handle new reason
4. Add tests to `test_victory_loss_conditions.py`

**If Changing Victory Conditions:**
1. Update `can_exit_map()` logic
2. Update mission config constants
3. Update tests for new requirements
4. Update mission briefing text

## Performance Notes

- Victory/defeat checks run once per phase, not every frame
- Preview state calculations cached during UI render
- Game over overlay only drawn when `running == False`
- No performance impact on normal gameplay
