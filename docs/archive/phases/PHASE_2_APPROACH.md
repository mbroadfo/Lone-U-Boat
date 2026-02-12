# Phase 2 Implementation Plan - Immediate Execution UI

## Context
Phase 1 established ActionHistory. Phase 2 converts the UI from queue/commit to immediate execution.

## Challenges Identified
- **unified_game.py** is 5,897 lines - very large file
- Multiple action types with different flows (simple moves, interactive torpedoes, dialogs)
- Existing preview state system deeply integrated
- Need to maintain game functionality during transition

## Recommended Approach: Incremental Implementation

Rather than a complete rewrite, Phase 2 should be broken into smaller, testable sub-phases:

### Phase 2A: Minimal Immediate Execution (2-3 hours)
**Goal**: Get basic immediate execution working for simple actions

1. Create `_execute_action_immediate()` method alongside `_queue_action()`
2. Convert simple actions only: move, rotate, dive, surface
3. Keep existing queue for complex actions temporarily
4. Test that simple actions work

**Benefit**: Partially working system, can test immediately

### Phase 2B: Action Dialogs (2-3 hours)
**Goal**: Update interactive action selection

1. Update Fire Torpedo dialog to execute immediately after selection
2. Update Load Torpedo dialog to execute immediately after selection
3. Update Repair dialog to execute immediately after selection
4. Remove preview state checks from dialogs

**Benefit**: All action types work with immediate execution

### Phase 2C: Undo Button (1-2 hours)
**Goal**: Add undo capability to UI

1. Add undo button to game controls
2. Wire up to `action_history.undo_last_action()`
3. Show last action info
4. Disable button when can't undo

**Benefit**: User can fix mistakes

### Phase 2D: UI Cleanup (2-3 hours)
**Goal**: Remove queue-specific UI elements

1. Remove blue queue display box
2. Update AP display to show remaining
3. Change "COMMIT" to "NEXT PHASE"
4. Remove queue-related keyboard shortcuts
5. Update button enablement logic

**Benefit**: Clean, simple UI

### Phase 2E: Remove Old Queue Code (1-2 hours)
**Goal**: Clean up deprecated code

1. Remove `_queue_action()` method
2. Remove preview state helpers
3. Remove queue execution animation
4. Update all callers

**Benefit**: Simplified codebase

## Total Estimated Time: 8-15 hours across 5 sub-phases

## Alternative: Full Rewrite Approach
- Estimate: 20-30 hours
- Risk: Higher chance of breaking things
- Difficulty: Harder to test incrementally

## Recommendation
**Start with Phase 2A** - Get immediate execution working for simple actions first.
This allows us to:
1. Verify the approach works
2. Get user feedback early
3. Catch integration issues sooner
4. Have a working system at each step

## Next Action
Shall we:
A) Start Phase 2A (simple actions immediate execution)
B) Do full Phase 2 rewrite
C) Reconsider the approach

**Recommended**: Option A (incremental)
