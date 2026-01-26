# Torpedo Loading Preview State Fix

## Problem
When queueing actions in the same turn, players couldn't queue "Load Torpedoes" after "Fire Torpedoes" because the validation was checking the **current** game state (where tubes are still LOADED) instead of the **preview** state (where tubes would be EMPTY after the fire action executes).

## Example Scenario
1. Player has all torpedo tubes LOADED
2. Player queues "Fire Tubes 1, 2, 3" (costs 2 AP)
3. Player tries to queue "Load Tubes 1, 2" (costs 1 AP)
4. **Before fix**: Validation fails with "Tube 1 is already loaded"
5. **After fix**: Validation succeeds because it sees tubes 1-3 will be EMPTY after fire executes

## Solution
Extended the preview state simulation in [core/actions/action_queue.py](core/actions/action_queue.py) to track torpedo tube states through queued actions.

### Changes Made
**File**: `core/actions/action_queue.py`

**Lines 55-92**: Complete rewrite of `add_action()` validation logic

1. **Import new action types** (lines 55-59):
   ```python
   from .depth_change_action import DepthChangeAction
   from .fire_torpedo_action import FireTorpedoAction
   from .load_torpedo_action import LoadTorpedoAction
   from copy import deepcopy
   from ..models import TubeState
   ```

2. **Create preview u-boat** (line 60):
   ```python
   preview_uboat = deepcopy(game_state.u_boat)
   ```

3. **Simulate queued actions** (lines 62-76):
   - **Depth changes**: Update `simulated_depth`
   - **Fire torpedoes**: Set fired tubes to `TubeState.EMPTY`
   - **Load torpedoes**: Set loaded tubes to `TubeState.LOADED`

4. **Create preview game state** (lines 78-92):
   ```python
   preview_game_state = SimpleNamespace(
       u_boat=preview_uboat,
       ships=getattr(game_state, 'ships', []),
       hex_grid=getattr(game_state, 'hex_grid', None),
       board_layout=getattr(game_state, 'board_layout', None),
       turn_manager=getattr(game_state, 'turn_manager', None)
   )
   ```

5. **Validate against preview** (line 91):
   ```python
   can_perform, reason = action.validate(preview_game_state)
   ```

## Benefits
- **Better UX**: Players can plan complete action sequences (fire → reload) in a single turn
- **No artificial restrictions**: You have 10 AP and both actions cost 3 AP total? You can queue both!
- **Extensible**: The preview system now handles depth, torpedo firing, and torpedo loading
- **Test compatible**: Uses `getattr()` with defaults for backward compatibility

## Testing
All 255 tests pass, including:
- `test_action_system.py`: Action queue functionality
- `test_torpedo_validator.py`: Torpedo fire/load validation
- `test_fire_then_load.py`: Specific test for this fire→load scenario

## How It Works
```
Current State:   tubes=[LOADED, LOADED, LOADED, LOADED, LOADED]
                         ↓
Queue Fire 1,2,3  ← validation sees current state, passes
                         ↓
Preview State:   tubes=[EMPTY, EMPTY, EMPTY, LOADED, LOADED]
                         ↓
Queue Load 1,2    ← validation sees PREVIEW state, passes!
                         ↓
Execute Actions   → Fire executes → Load executes
                         ↓
Final State:     tubes=[LOADED, LOADED, EMPTY, LOADED, LOADED]
```

## Code Quality
- **Defensive programming**: Uses `getattr()` for optional attributes
- **No duplicate code**: Removed redundant depth simulation in cost calculation
- **Clear intent**: Comments explain what each simulation does
- **Type safety**: Proper imports and type handling

## Related Files
- [core/actions/action_queue.py](core/actions/action_queue.py) - Main implementation
- [core/torpedo_validator.py](core/torpedo_validator.py) - Validates tube states
- [core/actions/fire_torpedo_action.py](core/actions/fire_torpedo_action.py) - Fire action
- [core/actions/load_torpedo_action.py](core/actions/load_torpedo_action.py) - Load action
- [test_fire_then_load.py](test_fire_then_load.py) - Validation test

## Previous Similar Fix
This extends the existing depth preview system that was already in place for calculating AP costs based on simulated depth after queued depth changes. The torpedo tube simulation follows the same pattern for consistency.
