# Interactive AI Architecture

## Overview

This document describes the **interactive AI system** in Lone U-Boat where the player controls all AI actions and dice rolls for authentic solitaire gameplay. The system uses queue-based execution with action generators to provide step-by-step control over enemy movements and attacks.

## Architecture Summary

The game implements true solitaire gameplay where:
- The player controls all AI dice rolls and actions
- Each AI action is queued and executed one at a time
- Full visibility into what the AI is doing
- Animations trigger for each action
- No automatic batch processing

## Implementation

### Component Hierarchy

```
Game (game_state.py)
├─ current_ai_queue: Optional[AIActionQueue]
│
└─ Queue-Based Execution System
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

**core/game_state.py**
- Single `current_ai_queue: Optional[AIActionQueue]` state
- Phase methods generate action queues:
  - `_execute_merchant_phase()` - generates merchant action queue
  - `_execute_detection_phase()` - generates detection action queue
  - `_execute_escort_phase()` - generates escort action queue
  - `_execute_b24_phase()` - generates B-24 action queue
- UI integration methods:
  - `execute_next_ai_action() -> bool`
  - `get_current_ai_action_preview() -> Optional[Dict]`
  - `has_pending_ai_actions() -> bool`

**core/ai_action_generators.py**
- `generate_merchant_actions(game_state) -> AIActionQueue`
- `generate_detection_actions(game_state) -> AIActionQueue`
- `generate_escort_actions(game_state) -> AIActionQueue`
- `generate_b24_actions(game_state) -> AIActionQueue`
- Uses existing AI logic to determine actions
- Wraps decisions in interactive action classes

**core/actions/ai/ai_action_queue.py**
- Queue manager for player-executed AI actions
- Methods: add, execute_current, next, get_progress
- Tracks execution history for debugging
- Provides UI progress data

### Action Classes

**Merchant Actions**
- `MerchantMoveAction` - Move along path
- `MerchantDamageCheckAction` - Roll damage check (4+ to move)

**Escort Actions**
- `EscortActivationAction` - Roll activation die
- `EscortMoveAction` - Move toward target
- `EscortTurnAction` - Turn toward target
- `EscortFireAction` - Deck gun attack
- `EscortDepthChargeAction` - Depth charge attack

**B-24 Actions**
- `B24MoveAction` - Move forward one hex
- `B24TurnAction` - Turn toward U-boat
- `B24BombAction` - Bombing attack
- `FlakDefenseAction` - U-boat flak defense

**Detection Actions**
- `EscortDetectionAction` - Roll escort detection
- `MerchantVisualAction` - Roll merchant visual sighting

## Phase Execution

### Phase Execution in game_state.py

```python
def _advance_to_next_phase(self):
    """Advance to next phase, executing phase-specific logic."""
    current_phase = self.turn_manager.current_phase
    
    # Execute phase logic when entering
    if current_phase == GamePhase.MERCHANT_PHASE:
        self._execute_merchant_phase()  # Queue-based
    elif current_phase == GamePhase.DETECTION_PHASE:
        self._execute_detection_phase()  # Queue-based
    elif current_phase == GamePhase.ESCORT_PHASE:
        self._execute_escort_phase()  # Queue-based
    elif current_phase == GamePhase.B24_PHASE:
        self._execute_b24_phase()  # Queue-based
```

### Phase Method Pattern

```python
def _execute_merchant_phase(self):
    """Execute merchant phase - generate action queue."""
    # Generate action queue using AI logic
    self.current_ai_queue = generate_merchant_actions(self)
    
    # Handle empty queue (no actions needed)
    if self.current_ai_queue.total_count() == 0:
        self.current_ai_queue = None  # Auto-advance phase
        return
    
    # Queue active - player executes actions
```

## Usage Pattern

### Player Execution Flow

```python
# Phase generates queue
game._advance_to_next_phase()  # Merchant phase queues actions

# UI checks for pending actions
if game.has_pending_ai_actions():
    # Get current action preview
    preview = game.get_current_ai_action_preview()
    display_action_preview(preview)
    
    # Player clicks "Execute Action"
    result = game.execute_next_ai_action()
    display_result(result)
```

### UI Integration

```python
# In UnifiedGameScreen._draw_phase_advance_button()

if self.game.has_pending_ai_actions():
    # Shows "EXECUTE AI ACTION" button (purple tint)
    # Displays action name, details, and progress (X of Y)
    pass
else:
    # Shows "NEXT PHASE" button when no actions pending
    pass
```

## Test Coverage

### Unit Tests (95 passing)
- Merchant AI tests (14 tests)
- Detection AI tests (12 tests)
- Escort AI tests (51 tests)
- B-24 AI tests (18 tests)

### Integration Tests (7 passing)
- `test_interactive_merchant_phase()` - Queue generation
- `test_interactive_detection_phase()` - Detection queue
- `test_interactive_escort_phase()` - Escort queue
- `test_queue_execution_workflow()` - Complete workflow
- `test_has_pending_ai_actions()` - Helper methods

## Benefits

1. **Authentic Solitaire Gameplay** - Player controls all dice rolls and actions
2. **Clean Architecture** - Single execution path, no technical debt
3. **Full Visibility** - Player sees every AI decision and die roll
4. **Animation Support** - Each action triggers visual feedback
5. **Code Reuse** - Action generators use existing AI logic
6. **Type Safety** - All code fully type-hinted, 0 errors

## Performance

- Pauses between actions for player input
- Shows preview/result for each action
- Authentic solitaire experience (player rolls all dice)
- Queue overhead: negligible (~1-5 actions per phase)
- Animations trigger for movement/rotation

---

*Last Updated: February 15, 2026*  
*Status: Production Ready*
