# Refactor: Immediate Execution System

## Overview
Replace the preview/queue system with immediate action execution. Each action executes instantly, AP is deducted immediately, and only the most recent action can be undone.

## Current System Problems
1. **Preview state complexity**: Every action type needs preview simulation
2. **Selection dialog bugs**: Fire/Load/Repair dialogs check current state instead of preview
3. **Maintenance burden**: New actions require preview logic
4. **Not board-game-like**: Real board games don't have "plan everything then commit"
5. **Bug surface area**: Continual discovery of preview-related bugs

## New System Design

### User Experience Flow
```
Turn starts → Roll AP (e.g., 7 AP)
│
├─ Click "Move Forward" → Executes immediately → Shows "6 AP remaining"
│  └─ Can click "Undo" to refund AP
│
├─ Click "Fire Torpedoes" → Opens dialog → Select tubes → Click "Fire"
│  └─ Executes immediately → Tubes empty → AP deducted → Can undo
│
├─ Click "Load Torpedoes" → Opens dialog → Select tubes → Click "Load"
│  └─ Executes immediately → Tubes loaded → AP deducted → Can undo
│
└─ Click "Next Phase" → Advances to Merchant Phase (no more actions this turn)
```

### Key Features
- **No preview**: Current state is always accurate
- **Immediate feedback**: See results instantly
- **Simple undo**: Only most recent action
- **Clear AP tracking**: Remaining AP shown after each action
- **No blue queue box**: Cleaner UI

---

## Phase 1: Core Architecture Changes ✅ COMPLETE

**Status**: ✅ **COMPLETED** (January 28, 2026)

### 1.1 Create ActionHistory Class ✅
**File**: `core/actions/action_history.py` (NEW)

```python
class ActionHistory:
    """
    Track executed actions for undo functionality.
    Only stores the most recent action.
    """
    def __init__(self):
        self.last_action = None
        self.last_action_state = None  # Game state before action
    
    def record_action(self, action, pre_action_snapshot):
        """Record action execution with state snapshot."""
        pass
    
    def can_undo(self):
        """Check if there's an action to undo."""
        pass
    
    def undo_last_action(self, game_state):
        """Restore game state to before last action."""
        pass
    
    def clear(self):
        """Clear history (when phase advances)."""
        pass
```

**Complexity**: Low (~155 lines implemented)  
**Dependencies**: None  
**Tests**: `tests/test_action_history.py` ✅ 14 tests, all passing

**Implementation Details**:
- Single-level undo with state snapshots
- Deep copy of mutable state for reliable restoration
- Helper functions: `create_u_boat_snapshot()`, `restore_u_boat_snapshot()`
- ✅ Added `action_history` reference (set by GameState)
- ✅ Added `remaining_ap` tracking (immediate execution)
- ✅ Added `clear_action_history()` method for phase transitions
- ✅ Added `execute_action_immediate()` method for AP deduction
- ✅ Set `remaining_ap` in both `roll_action_points_only()` and `start_new_turn()`

**Affected lines**: ~25 lines added  
**Complexity**: Low  
**Tests**: Integration tested via ActionHistory tests

### 1.3 Update GameState ✅
**File**: `core/game_stat

**Affected lines**: ~50-100 lines modified  
**Complexity**: Medium  
**Tests**: Update `tests/test_turn_manager.py` (if exists)

### 1.3 Remove ActionQueue Preview Methods
**File**: `core/actions/action_queue.py`
 (DEFERRED TO PHASE 5):
- `get_preview_torpedo_tubes()` (~40 lines)
- `get_preview_damage_state()` (~30 lines)
- `add_action()` preview simulation logic (~80 lines)
- Keep: All existing methods for compatibility during transition

**Complexity**: Low (deletion)  
**Impact**: Will break many tests (expected in Phase 4)
**Note**: Keeping preview methods for now to maintain compatibility during UI refactoring

### Phase 1 Summary

**Completed Work**:
- ✅ New ActionHistory class (155 lines)
- ✅ Comprehensive tests (14 tests, 350 lines)
- ✅ TurnManager integration (25 lines added)
- ✅ GameState integration (30 lines modified)
- ✅ All tests passing (14/14)

**Code Impact**:
- **Added**: 530 lines (ActionHistory + tests)
- **Modified**: 55 lines (TurnManager, GameState)
- **Net change**: +585 lines

**Next Phase**: Phase 2 - UI changes for immediate execution
**Impact**: Breaks many tests (expected)

---

## Phase 2: UI Changes - Action Execution

**Status**: ✅ Phase 2A COMPLETE - Simple actions using immediate execution
            ✅ Phase 2B COMPLETE - Complex actions using immediate execution

### Phase 2A: Simple Actions (COMPLETE ✅)

**Completed**: Simple actions now execute immediately without queueing:
- ✅ Move forward/reverse
- ✅ Rotate left/right  
- ✅ Dive/surface

**Implementation Details**:
- Added `_execute_action_immediate()` method (96 lines)
- Updated button click handler to route simple actions to new method
- Actions validate against current state (no preview needed)
- AP deducted immediately via `turn_manager.execute_action_immediate()`
- State snapshot created before execution for undo
- Action recorded in `action_history` for undo capability
- Complex actions (torpedoes, repair, deck gun) still use queue temporarily

**Code Changes**:
- `unified_game.py`: +96 lines (_execute_action_immediate method)
- `unified_game.py`: Modified button handler to route simple vs complex actions
- `game_state.py`: Re-added action_queue temporarily for complex actions

**Testing**: Game runs successfully, simple actions execute immediately with proper AP deduction

### Phase 2B: Complex Actions (COMPLETE ✅)

**Completed**: All complex actions now execute immediately:
- ✅ Fire torpedoes - executes immediately after tube selection
- ✅ Load torpedoes - executes immediately after tube selection
- ✅ Repair systems - executes immediately after component selection
- ✅ Deck gun - executes immediately when clicked

**Implementation Details**:
- Updated `_handle_fire_torpedo_clicks()` to execute FireTorpedoAction immediately
- Updated `_handle_load_torpedo_clicks()` to execute LoadTorpedoAction immediately
- Updated `_confirm_repair_selection()` to execute RepairAction immediately
- Added deck_gun to `_execute_action_immediate()` method
- Removed all action_queue.add_action() calls from torpedo/repair handlers
- Dialogs still shown for tube/component selection, but execution is immediate on confirm
- All actions use current state (no preview state calculations)

**Code Changes**:
- `unified_game.py`: Modified fire torpedo handler (~60 lines)
- `unified_game.py`: Modified load torpedo handler (~50 lines)
- `unified_game.py`: Modified repair confirmation (~80 lines)
- `unified_game.py`: Added deck_gun to immediate execution (~35 lines)
- `unified_game.py`: Updated button handler to route deck_gun to immediate execution

**Testing**: Game runs successfully, all actions execute immediately with proper AP tracking

**Next**: Phase 2C - Add undo button UI

### Phase 2C: Undo Button (COMPLETE ✅)

**Completed**: Undo button with turn-based restrictions:
- ✅ Undo button shown only when action_history.can_undo() is true
- ✅ Displays last action name and AP refund
- ✅ Click to restore U-boat state and refund AP
- ✅ Action history cleared when dice are rolled (no undoing after dice roll)
- ✅ Undo clears history (can't undo twice - one-level undo only)

**Implementation Details**:
- Added `_undo_last_action()` method to restore snapshot and refund AP
- Undo button rendered in `_draw_game_controls()` below AP display
- Button shows "↶ UNDO: {action_name} (refund {ap} AP)"
- Click handler integrated into mouse event handling
- Action history cleared on dice roll (enforces turn boundary)
- Updated `ActionHistory.undo_last_action()` to return dict with snapshot, ap_refund, and action_name

**Code Changes**:
- `unified_game.py`: +45 lines (undo button rendering and click handling)
- `unified_game.py`: Added `_undo_last_action()` method
- `unified_game.py`: Clear history on dice roll
- `action_history.py`: Modified undo_last_action() to return structured data

**Testing**: Game runs successfully, undo button appears after actions, disappears after dice roll

**Undo Rules**:
- Can undo any action during U-boat phase
- Once dice are rolled for a turn, all undo history is cleared
- After undoing, cannot undo again (one-level undo)
- Undo restores position, facing, depth, torpedo tubes, damage states, hull damage
- AP is refunded immediately

**Next**: Phase 2D - Remove queue display, clean up UI

### Phase 2D: UI Cleanup (COMPLETE ✅)

**Completed**: Removed queue-based UI elements:
- ✅ Removed `_draw_action_queue()` method (~145 lines)
- ✅ Removed blue queue box display
- ✅ Updated button enablement to use CURRENT state instead of preview state
- ✅ Simplified AP display to show remaining/max from turn_manager
- ✅ Removed preview state calculations from button logic
- ✅ No more "queued actions" list display

**Implementation Details**:
- Removed entire `_draw_action_queue()` method that drew queue box with queued actions
- Updated `_draw_game_controls()` to use current U-boat state for all validations
- Button enablement now checks `current_depth`, `current_position`, `u_boat.damage` directly
- AP display shows `turn_manager.remaining_ap` instead of `action_queue.get_remaining_ap()`
- Cost calculations use current depth, not preview depth
- EXIT MAP button uses current position/facing, not preview
- Removed all `_get_preview_state()` calls from button logic
- Removed preview torpedo tubes and preview damage state calculations

**Code Changes**:
- `unified_game.py`: Removed queue display call from right panel rendering
- `unified_game.py`: Commented out `_draw_action_queue()` method
- `unified_game.py`: Updated `_draw_game_controls()` to use current state (~50 lines modified)
- `unified_game.py`: Simplified button logic (no preview calculations)

**Testing**: Game runs successfully, queue box is gone, buttons respond to current state

**Fixes Applied**:
- ✅ Added "NEXT PHASE ►" button to U-boat controls for phase advancement
- ✅ Fixed button click handling order (exit → undo → phase → actions)
- ✅ Added phase_advance_button_rect initialization and click detection

**UI Improvements**:
- Cleaner interface - no confusing "queued actions" display
- Buttons always show current state requirements
- AP remaining prominently displayed
- Undo button shows when available
- **NEXT PHASE button available during U-boat phase to continue game**
- Immediate visual feedback on all actions

**Next**: Phase 2E - Delete old queue code completely

---

### Original Phase 2 Plan

### 2.1 Modify Action Button Handler
**File**: `core/screens/unified_game.py`

**Current**: `_queue_action(action_id)` adds to queue  
**New**: `_execute_action(action_id)` executes immediately

**Changes**:
```python
def _execute_action(self, action_id: str):
    """Execute action immediately and deduct AP."""
    # 1. Create action
    # 2. Validate against CURRENT state (no preview)
    # 3. Execute action
    # 4. Deduct AP
    # 5. Record in action_history
    # 6. Update UI
    # 7. Check if phase should auto-advance
```

**Affected methods**:
- `_queue_action()` → `_execute_action()`
- Remove all preview state checks
- Use current `u_boat.torpedo_tubes` directly
- Use current `u_boat.deck_gun_damaged` directly

**Complexity**: High (~200 lines modified)  
**Files touched**: 
- `unified_game.py::_execute_action`
- `unified_game.py::_draw_game_controls` (button logic)

### 2.2 Update Selection Dialogs
**Files**: `core/screens/unified_game.py`

**Fire Torpedoes Dialog**:
- **Current**: Checks `u_boat.torpedo_tubes[i]` (already correct!)
- **Change**: Remove any preview state references
- Lines: ~4000-4200

**Load Torpedoes Dialog**:
- **Current**: Checks `u_boat.torpedo_tubes[i]` (already correct!)
- **Change**: Remove any preview state references
- Lines: ~3850-4100

**Repair Selection Dialog**:
- **Current**: Checks `u_boat.engine_damaged` etc.
- **Change**: Remove any preview state references
- Lines: ~5200-5400

**Complexity**: Low (mostly removal)

### 2.3 Remove Queue Display Box
**File**: `core/screens/unified_game.py`

**Remove**:
- `_draw_action_queue()` method (~100 lines)
- Blue queue box rendering
- "Queued actions" display

**Add**:
- Display "AP Remaining: X" prominently
- Display last action (if any) with undo button

**Complexity**: Medium (~150 lines removed, 50 lines added)

### 2.4 Add Undo Button
**File**: `core/screens/unified_game.py`

**New UI element**:
```
┌─────────────────────────┐
│ AP Remaining: 5         │
│ Last: Move Forward (1 AP)│
│ [UNDO LAST ACTION]      │
└─────────────────────────┘
```

**Handler**:
```python
def _undo_last_action(self):
    """Undo the most recent action."""
    if self.game.action_history.can_undo():
        self.game.action_history.undo_last_action(self.game)
        self.add_event("✓ Undone: [action name]")
```

**Complexity**: Low (~80 lines)

### 2.5 Change Commit Button to "Next Phase"
**File**: `core/screens/unified_game.py`

**Current**: "COMMIT" button executes queue  
**New**: "NEXT PHASE" button advances phase

**Changes**:
- Button label: "COMMIT" → "NEXT PHASE" (or "→ MERCHANT PHASE")
- Handler: Execute `advance_phase()` instead of `commit_actions()`
- Clear `action_history` on phase advance
- No confirmation needed (actions already executed)

**Complexity**: Low (~30 lines modified)

---

## Phase 3: Button Enablement Simplification

### 3.1 Simplify Button Logic
**File**: `core/screens/unified_game.py` (`_draw_game_controls`)

**Current**: Uses preview states  
**New**: Uses current states only

**Changes**:
```python
# OLD (lines 3288-3298)
preview_torpedo_tubes = self.game.action_queue.get_preview_torpedo_tubes(u_boat)
preview_damage = self.game.action_queue.get_preview_damage_state(u_boat)
loaded_tubes = sum(1 for tube in preview_torpedo_tubes if tube == TubeState.LOADED)
empty_tubes = sum(1 for tube in preview_torpedo_tubes if tube == TubeState.EMPTY)

# NEW
loaded_tubes = sum(1 for tube in u_boat.torpedo_tubes if tube == TubeState.LOADED)
empty_tubes = sum(1 for tube in u_boat.torpedo_tubes if tube == TubeState.EMPTY)
deck_gun_enabled = not u_boat.deck_gun_damaged and preview_depth == Depth.SURFACED
```

**Complexity**: Low (~50 lines simplified)  
**Benefit**: **Eliminates entire class of preview bugs**

### 3.2 Simplify On-Map Button Logic
**File**: `core/screens/unified_game.py` (`_draw_on_map_action_buttons`)

**Current**: Uses preview torpedo tubes  
**New**: Uses current torpedo tubes directly

**Lines**: 2660-2680  
**Complexity**: Low (~20 lines simplified)

---

## Phase 4: Test Updates

### 4.1 Remove Preview Tests
**File**: `tests/test_action_stacking.py`

**Remove** (~300 lines):
- All `test_preview_*` tests
- All "UI PREVIEW STATE TESTS" section
- All "COMPREHENSIVE PREVIEW STATE TESTS" section

**Keep** (~200 lines):
- Basic action validation tests
- Action execution tests
- AP cost tests
- Action stacking validation (can still do multiple actions per turn)

**Complexity**: Low (mostly deletion)

### 4.2 Add Action History Tests
**File**: `tests/test_action_history.py` (NEW)

**Tests**:
- `test_record_action`: Records action with state snapshot
- `test_undo_single_action`: Undoes last action, restores state
- `test_undo_refunds_ap`: Undoing refunds action points
- `test_cannot_undo_twice`: Can only undo most recent action
- `test_clear_history`: Clearing prevents undo

**Complexity**: Low (~150 lines new tests)

### 4.3 Add Immediate Execution Tests
**File**: `tests/test_immediate_execution.py` (NEW)

**Tests**:
- `test_fire_then_load_same_turn`: Execute fire, then load
- `test_load_then_fire_same_turn`: Execute load, then fire
- `test_repair_then_use_same_turn`: Execute repair, then use
- `test_undo_fire_restores_tubes`: Undo fire action restores tubes
- `test_undo_load_refunds_ap`: Undo load refunds AP
- `test_multiple_actions_different_types`: Fire → Move → Load sequence

**Complexity**: Medium (~300 lines new tests)

### 4.4 Update Existing Tests
**Files**: Various test files

**Changes**:
- Remove `action_queue` references
- Change "queue and commit" to "execute directly"
- Update AP tracking (remaining vs. max)

**Estimated affected tests**: 50-100 tests  
**Complexity**: High (tedious but straightforward)

---

## Phase 5: Cleanup & Polish

### 5.1 Remove Unused Code
**Files**: Various

**Remove**:
- `action_queue.py` unused methods
- Preview state simulation code
- Queue validation logic
- Preview-related helper functions

**Estimated lines removed**: 500+ lines  
**Complexity**: Low (deletion)

### 5.2 Update Documentation
**Files**: 
- `docs/ARCHITECTURE_BOARD_LAYOUT.md`
- `docs/SESSION_*.md` files
- `README.md`

**Changes**:
- Remove queue/preview references
- Add action history documentation
- Update gameplay flow diagrams

**Complexity**: Low

### 5.3 Performance Testing
**Tests**: Manual gameplay testing

**Verify**:
- Actions execute smoothly
- Undo works reliably
- AP tracking accurate
- No lag between actions
- Phase transitions smooth

---

## Implementation Order (Recommended)

### Week 1: Core Changes
1. **Day 1-2**: Phase 1 (ActionHistory, TurnManager changes)
2. **Day 3**: Phase 2.1 (Action execution logic)
3. **Day 4**: Phase 2.2-2.3 (Selection dialogs, remove queue box)
4. **Day 5**: Phase 2.4-2.5 (Undo button, Next Phase button)

### Week 2: UI & Tests
1. **Day 1**: Phase 3 (Button enablement simplification)
2. **Day 2-3**: Phase 4.1-4.2 (Remove preview tests, add new tests)
3. **Day 4-5**: Phase 4.3-4.4 (Execution tests, update existing tests)

### Week 3: Polish
1. **Day 1-2**: Phase 5.1-5.2 (Cleanup, documentation)
2. **Day 3-5**: Phase 5.3 (Testing, bug fixes)

---

## Risk Assessment

### High Risk Areas
1. **State restoration for undo**: Need deep copy of game state
2. **Interactive actions** (torpedoes): Undo after rolling dice?
3. **Test breakage**: Many tests will need updates

### Mitigation Strategies
1. **Snapshot only critical state**: U-boat, AP, tube states
2. **Undo before resolution**: Can't undo after dice rolled
3. **Incremental testing**: Fix tests after each phase

---

## Benefits Summary

### Code Quality
- **-500 lines**: Remove preview simulation complexity
- **-300 lines**: Remove preview tests
- **+200 lines**: Simple undo logic
- **Net**: -600 lines of complex code

### Maintainability
- ✅ No preview state to maintain
- ✅ No selection dialog preview bugs
- ✅ Future actions don't need preview logic
- ✅ Simpler UI logic

### User Experience
- ✅ More authentic board game feel
- ✅ Immediate feedback
- ✅ Cleaner UI (no blue queue box)
- ✅ Clear AP tracking
- ✅ Simple undo for mistakes

### Performance
- ✅ No preview calculation overhead
- ✅ Faster UI rendering
- ✅ Less memory usage

---

## Decision Points

### What Happens When AP Runs Out?
**Option A**: "Next Phase" button appears automatically  
**Option B**: Buttons gray out, manual "Next Phase" click  
**Recommendation**: Option A (smoother flow)

### Undo Limitations
**Question**: Can you undo after dice are rolled?  
**Recommendation**: No - once dice rolled (torpedoes, deck gun), can't undo  
**Rationale**: Prevents save-scumming, maintains board game feel

### AP Display
**Question**: Where to show remaining AP?  
**Recommendation**: Top-right corner, large and prominent  
**Format**: "AP: 5 / 7" or just "5 AP"

---

## Success Criteria

### Functionality
- ✅ All actions execute immediately
- ✅ Undo restores last action correctly
- ✅ AP tracking accurate
- ✅ No preview state bugs
- ✅ Phase transitions work

### Code Quality
- ✅ All tests pass
- ✅ Zero preview-related code
- ✅ Simpler codebase
- ✅ Better maintainability

### User Experience
- ✅ Smooth gameplay
- ✅ Clear feedback
- ✅ No confusing behavior
- ✅ Authentic board game feel

---

## Notes

### Compatibility Considerations
- Game saves may need migration (remove queue data)
- No breaking changes to mission files
- Action classes remain unchanged (just execute differently)

### Future Enhancements
- Multiple undo levels? (Not for v1)
- Redo functionality? (Not for v1)
- Action animation? (Nice to have)

---

## Approval Required

Before starting implementation:
- [ ] Review plan with team/user
- [ ] Confirm scope (all phases or subset?)
- [ ] Agree on timeline
- [ ] Identify blockers

**Status**: DRAFT - Awaiting approval
