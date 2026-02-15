# Strangler Fig Pattern - Interactive AI Implementation

## Overview

This document describes the **Strangler Fig Pattern** implementation for transitioning from batch AI execution to player-controlled interactive AI actions in Lone U-Boat. The pattern allows both systems to coexist, with controlled migration between them.

## Pattern Description

The Strangler Fig Pattern (Martin Fowler) is an incremental refactoring approach where a new system gradually "wraps around" and replaces an old system. Key principles:

1. **Dual Systems Coexist** - Both old and new implementations remain functional
2. **Feature Flag Routing** - A flag determines which system to use
3. **Gradual Migration** - Systems can be swapped without risk
4. **Zero Breaking Changes** - Existing code continues to work unchanged

## Architecture

### Component Hierarchy

```
Game (game_state.py)
├─ interactive_ai_mode: bool (Feature Flag)
├─ current_ai_queue: Optional[AIActionQueue] (New System State)
│
├─ OLD BATCH SYSTEM (interactive_ai_mode=False, DEFAULT)
│  ├─ MerchantAI.execute_merchant_phase()
│  ├─ DetectionAI.execute_detection_phase()
│  ├─ EscortAI.execute_escort_phase()
│  └─ B24AI.execute_b24_phase()
│
└─ NEW INTERACTIVE SYSTEM (interactive_ai_mode=True)
   ├─ Action Generators (ai_action_generators.py)
   │  ├─ generate_merchant_actions() → AIActionQueue
   │  ├─ generate_detection_actions() → AIActionQueue
   │  ├─ generate_escort_actions() → AIActionQueue
   │  └─ generate_b24_actions() → AIActionQueue
   │
   ├─ Interactive Actions (core/actions/ai/)
   │  ├─ Merchant: MerchantMoveAction, MerchantDamageCheckAction
   │  ├─ Detection: EscortDetectionAction, MerchantVisualAction
   │  ├─ Escort: 6 actions (Activation, Move, Turn, Fire, etc.)
   │  └─ B-24: 4 actions (Move, Turn, Bomb, FlakDefense)
   │
   └─ AIActionQueue (orchestrates player execution)
      ├─ add() / add_multiple()
      ├─ current_action() / execute_current()
      ├─ next() / peek_next()
      └─ get_progress() (for UI)
```

## Implementation Files

### Core Files

**core/game_state.py** (Modified)
- Added `interactive_ai_mode: bool` flag (default False)
- Added `current_ai_queue: Optional[AIActionQueue]` state
- Modified `_advance_to_next_phase()` to route based on flag
- Added 4 new interactive phase methods:
  - `_execute_merchant_phase_interactive()`
  - `_execute_detection_phase_interactive()`
  - `_execute_escort_phase_interactive()`
  - `_execute_b24_phase_interactive()`
- Added UI integration methods:
  - `execute_next_ai_action() -> bool`
  - `get_current_ai_action_preview() -> Optional[Dict]`
  - `has_pending_ai_actions() -> bool`

**core/ai_action_generators.py** (NEW - 240 lines)
- `generate_merchant_actions(game_state) -> AIActionQueue`
- `generate_detection_actions(game_state) -> AIActionQueue`
- `generate_escort_actions(game_state) -> AIActionQueue`
- `generate_b24_actions(game_state) -> AIActionQueue`
- Uses existing AI logic to determine actions
- Wraps decisions in interactive action classes

**core/actions/ai/ai_action_queue.py** (Phase 6 - 282 lines)
- Queue manager for player-executed AI actions
- Methods: add, execute_current, next, get_progress
- Tracks execution history for debugging
- Provides UI progress data

### Action Classes (Phases 1-5)

**Merchant Actions** (Phase 1)
- `MerchantMoveAction` - Move along path
- `MerchantDamageCheckAction` - Roll damage check (4+ to move)

**Escort Actions** (Phase 2)
- `EscortActivationAction` - Roll activation die
- `EscortMoveAction` - Move toward target
- `EscortTurnAction` - Turn toward target
- `EscortFireAction` - Deck gun attack
- `EscortDepthChargeAction` - Depth charge attack
- (Plus die action for deactivation)

**B-24 Actions** (Phase 4)
- `B24MoveAction` - Move forward one hex
- `B24TurnAction` - Turn toward U-boat
- `B24BombAction` - Bombing attack
- `FlakDefenseAction` - U-boat flak defense

**Detection Actions** (Phase 5)
- `EscortDetectionAction` - Roll escort detection
- `MerchantVisualAction` - Roll merchant visual sighting

## Routing Logic

### Phase Execution in game_state.py

```python
def _advance_to_next_phase(self):
    """Advance to next phase, executing phase-specific logic."""
    current_phase = self.turn_manager.current_phase
    
    # Execute phase end logic
    if current_phase == GamePhase.MERCHANT_PHASE:
        if self.interactive_ai_mode:
            self._execute_merchant_phase_interactive()  # NEW
        else:
            self._execute_merchant_phase()  # OLD (batch)
    # ... similar for DETECTION, ESCORT, B24 phases
```

### Interactive Phase Pattern

```python
def _execute_merchant_phase_interactive(self):
    """Execute merchant phase in interactive mode."""
    # Generate action queue using existing AI logic
    self.current_ai_queue = generate_merchant_actions(self)
    
    # Handle empty queue (no actions needed)
    if self.current_ai_queue.total_count() == 0:
        self.current_ai_queue = None  # Auto-advance phase
        return
    
    # Queue remains active - player must execute actions
    # Phase won't advance until queue exhausted
```

## Usage Patterns

### Batch Mode (Default - Old System)

```python
# Creating game uses batch mode by default
game = Game(mission_number=1)  # interactive_ai_mode=False

# Phases execute automatically
game._advance_to_next_phase()  # Merchant AI runs immediately

# No player interaction needed for AI phases
```

### Interactive Mode (New System)

```python
# Enable interactive mode
game = Game(mission_number=1, interactive_ai_mode=True)

# Phase generates queue instead of executing
game._advance_to_next_phase()  # Merchant phase queues actions

# UI checks for pending actions
if game.has_pending_ai_actions():
    # Get current action preview
    preview = game.get_current_ai_action_preview()
    display_action_preview(preview)
    
    # Player clicks "Execute Action"
    result = game.execute_next_ai_action()
    display_result(result)
    
# When queue exhausted, phase can advance
```

### UI Integration (Phase 7.4 - COMPLETE)

```python
# In UnifiedGameScreen._draw_phase_advance_button()
# Now checks for pending actions and shows Execute button

if self.game.has_pending_ai_actions():
    # Shows "EXECUTE AI ACTION" button (purple tint)
    # Displays action name, details, and progress (X of Y)
    # On button click: self.game.execute_next_ai_action()
    pass
else:
    # Shows "NEXT PHASE" button when no actions pending
    pass

# In handle_events() (MOUSEBUTTONDOWN)
if self.execute_ai_action_button_rect and 
   self.execute_ai_action_button_rect.collidepoint(mouse_pos):
    has_more = self.game.execute_next_ai_action()
    if not has_more:
        phase_name = self.game.turn_manager.get_current_phase_name()
        self.add_event(f"{phase_name} AI actions complete")
```

**To Test UI Manually:**
1. Edit `main.py`: Set `interactive_ai_mode=True` in Game() constructor
2. Run game: `python main.py`
3. Complete U-boat phase, advance to AI phase
4. Purple "EXECUTE AI ACTION" button appears
5. Click button to execute each action step-by-step

## Test Coverage

### Unit Tests (445 passing)
- 383 tests from Phases 1-3 (baseline)
- 24 tests for B-24 actions (Phase 4)
- 18 tests for Detection actions (Phase 5)
- 20 tests for AIActionQueue (Phase 6)

### Integration Tests (5 passing)
- `test_interactive_merchant_phase()` - Queue generation
- `test_interactive_detection_phase()` - Detection queue
- `test_interactive_escort_phase()` - Escort queue
- `test_batch_mode_still_works()` - Backward compatibility
- `test_has_pending_ai_actions()` - Helper methods

### Test File: test_interactive_mode.py (171 lines)
Located in repository root for quick access.

## Migration Strategy

### Current State (Phase 7.4 Complete)
✅ Both systems fully functional  
✅ Feature flag controls routing  
✅ All 445 tests passing (batch mode)  
✅ 5 integration tests passing (interactive mode)  
✅ Zero breaking changes  
✅ **UI Integration Complete** - Execute AI Action button functional

### Next Steps

**Phase 7.5: User Enablement** (Not Started)
- Add settings toggle for interactive_ai_mode
- Allow players to choose batch vs interactive
- Add keyboard shortcut to execute AI actions
- Default remains batch mode (safe)

**Phase 8: Deprecate Old System** (Future)
- When interactive mode proven stable
- Remove batch AI execution paths
- Keep AI logic classes for action generators

## Benefits Achieved

1. **Zero Risk Migration** - Old system remains default, fully functional
2. **Solitaire Gameplay** - Player controls all dice rolls (new system)
3. **Incremental Testing** - Each component tested in isolation
4. **Rollback Safety** - Can disable interactive mode anytime
5. **Code Reuse** - Action generators use existing AI logic
6. **Type Safety** - All code fully type-hinted, 0 errors

## Performance Characteristics

### Batch Mode (Old)
- Executes entire phase in one frame
- No user interaction
- Fast but not true to solitaire model

### Interactive Mode (New)
- Pauses between actions for player input
- Shows preview/result for each action
- Slower but authentic solitaire experience
- Queue overhead: negligible (~1-5 actions per phase)

## Known Limitations

1. **Merchant Phase Queues** - May be empty on first turn (no path yet)
2. **Escort Activation** - Queue generates all actions upfront (doesn't dynamically adjust for deactivation)
3. **B-24 Spawning** - Not yet in interactive mode (Phase 7.5)
4. **Manual Mode Toggle** - Must set interactive_ai_mode in code (Phase 7.5 will add UI toggle)

## Future Enhancements

1. **Dynamic Queue Adjustment** - Generate actions based on previous results
2. **Animation Triggers** - Action classes already support `triggers_animation` property
3. **Undo Support** - Queue history enables undo of AI actions
4. **Replay Mode** - Execution history allows replay of turns
5. **AI Difficulty** - Different generators for Easy/Normal/Hard modes

## References

- **Strangler Fig Pattern**: Martin Fowler, <https://martinfowler.com/bliki/StranglerFigApplication.html>
- **Action System Design**: `core/actions/README.md` (if exists)
- **Test Coverage**: `tests/interactive_ai/README.md` (if exists)
- **Phase Documentation**: `docs/archive/phases/PHASE_*.md`

## Version History

- **Phase 6 (2026-02-11)**: AIActionQueue implementation
- **Phase 7.1-7.3 (2026-02-12)**: Strangler fig backend wiring
- **Phase 7.4 (2026-02-12)**: UI integration - Execute AI Action button complete
- **Phase 7.5 (Pending)**: User enablement - settings toggle
- **Phase 8 (Future)**: Old system deprecation

---

*Last Updated: February 12, 2026*  
*Status: Phase 7.4 Complete - UI Fully Functional*
