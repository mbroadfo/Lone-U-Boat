# Changelog

All notable changes to the Lone U-Boat project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - 2026-02-01

### Fixed
- **Merchant Facing Bug**: Damaged merchants no longer change facing when failing movement roll
  - Merchant ships now return `None` for new_facing when unable to move
  - Only change facing when actually moving to waypoint
  - Test updated to verify no facing change on failed roll
- **Torpedo Penetration System**: Torpedoes now correctly skip destroyed ships and continue to targets in line
  - Torpedoes skip ships sunk earlier in same salvo (checks result tuple is_sunk flag)
  - Torpedoes skip ships destroyed earlier in turn (checks destroyed_this_phase with coordinate comparison)
  - Calculates torpedo firing direction and checks remaining targets for in-line positioning
  - Cancels remaining torpedoes if no ships in line after sinking target
  - Added messages: "Ship sunk - N torpedo(es) continue toward ships in line" or "Ship sunk - no ships in line, canceling N remaining torpedo(es)"
- **B24 Spawn Algorithm**: Rewrote _get_furthest_edge_position() to match RULES.txt specification
  - Now traces lines in all 6 Facing directions from U-boat position
  - Counts valid hexes in each direction until hitting edge
  - Returns last hex in longest line (truly furthest edge on hex-line)
  - Fixes bug where B24 spawned 1 hex away instead of at map edge
- **Movement Through Destroyed Ships**: U-boat can now pass through destroyed ship hexes at any depth
  - Added destroyed_entities parameter to MovementValidator.can_move_to()
  - Checks destroyed_this_phase for ships at target hex with coordinate comparison
  - Allows movement through destroyed ships (visual cleanup handled by caller)

### Changed
- **Result Tuple Format**: Fire torpedo result tuple expanded from 5 to 6 elements
  - Old format: `(torpedo_num, ship, distance, hit, damage_roll)`
  - New format: `(torpedo_num, ship, distance, hit, damage_roll, is_sunk)`
  - Added is_sunk flag from damage_result.is_now_sunk for penetration logic
- **Escort AI**: Added check_forced_ascent() method called after all depth charge and gun attacks
  - Checks if hull damage forces U-boat to ascend beyond current depth capability
  - Destroys U-boat if ship blocks forced ascent in same hex
  - Called in 7 locations after damage resolution
- **Mission 1 Config**: Updated merchant exit hex from (6,10) to (6,9)
  - Corrected waypoint list to match actual map boundaries
  - Updated test expectations to match corrected path

### Technical
- **Code Cleanup**: Fixed 5 Pylance linting errors in unified_game.py
  - Replaced unused tuple unpacking variables with underscores
  - Removed unused Facing import
  - Added type annotation: `List[Tuple[Any, int, str]]` to valid_targets_in_line
- **Coordinate Comparison**: Changed HexCoord equality checks to explicit q/r comparisons
  - Destroyed entity detection now uses: `destroyed_pos.q == ship.position.q and destroyed_pos.r == ship.position.r`
  - More reliable than HexCoord.__eq__ for cross-turn entity tracking

### Validated
- All 336 tests passing
- Epic gameplay validation: "Ship sunk - no ships in line, canceling 1 remaining torpedo(es)"
- B24 spawn distances verified in-game
- Merchant facing confirmed: "rolled 1d6 [3], cannot move" (no facing change)

---

## [Phase 2] - 2026-01-31

### Added
- **Immediate Execution System**: Actions now execute instantly when clicked, replacing queue-based system
- **Multi-Level Undo**: New UNDO button allows reverting actions within the current phase
  - Shows last action name and AP cost
  - Restores full game state including AP
  - Multiple undos available until phase advance
- **State Snapshot System**: Automatic state snapshots before each action for undo functionality
  - Helper functions `create_u_boat_snapshot()` and `restore_u_boat_snapshot()`
  - Deep copy of all mutable state (position, facing, depth, torpedoes, damage)
- **Consistent Phase Advance Button**: NEXT PHASE button now appears consistently at bottom in all modes
  - Regular gameplay
  - Dice roll mode
  - Torpedo selection (load/fire)
  - Deck gun resolution
  - Repair selection
- **Comprehensive Type Annotations**: Added proper type hints throughout codebase
  - Forward references for circular dependencies (TYPE_CHECKING)
  - Optional type hints for nullable parameters
  - Explicit return type annotations
  - Type ignore comments for intentional design patterns

### Changed
- **UI Flow**: Removed commit step - actions execute immediately
- **Button Labels**: "COMMIT" renamed to "NEXT PHASE" for clarity
- **Control Panel Layout**: Simplified layout without queue preview box
- **Action Feedback**: Immediate visual feedback when actions execute
- **AP Display**: Shows remaining AP in real-time (no preview calculation needed)

### Removed
- **Action Queue System**: Removed queue-based preview and commit workflow
- **Continue Button**: Removed old Continue button from queue system
- **Queue Preview Box**: Removed blue preview box showing queued actions
- **Preview State Calculations**: No longer needed with immediate execution
- **Debug Logging**: Removed 14+ DEBUG print statements added during development
- **Dead Code**: Removed duplicate _draw_game_controls method and old queue system keyboard handlers
- **Unused Variables**: Cleaned up unused variables to eliminate type checker warnings

### Fixed
- **Invisible Button Bug**: Fixed Continue button overlapping with action buttons causing torpedo firing to end phase
- **Button Click Detection**: Fixed NEXT PHASE button rect variable (`phase_advance_button_rect` instead of `action_continue_button_rect`)
- **Special Mode Button**: Fixed NEXT PHASE button not appearing during torpedo selection, dice rolls, and other special modes
- **Type Hints**: Resolved all type checker errors and warnings
  - Added Optional type hints to RepairAction parameters
  - Fixed torpedo_button_rects dictionary type annotation
  - Added TYPE_CHECKING imports for forward references
  - Removed unused TubeState import
  - Fixed unbound snapshot variable in repair code
  - Added type: ignore comments for intentional protected method access
  - Added return type annotations for list-returning methods
- **Test Assertions**: Fixed test expectations to match new undo return structure

### Testing
- All 336 tests passing across 24 test files
- Integration tested with full Mission 1 playthrough (4 turns, victory achieved)
- Validated undo functionality with multiple action types
- Confirmed all action dialogs work with immediate execution
- Zero type checker errors or warnings

### Performance
- Reduced `unified_game.py` from 5,897 to 5,738 lines (-159 lines)
- State snapshots use deepcopy for safety
- Memory efficient: snapshots cleared on phase advance

### Code Quality
- **Type Safety**: Complete type annotation coverage with no errors
- **Clean Code**: Removed all dead code from old queue system
- **Consistent Naming**: Prefixed intentionally unused variables with underscore

### Documentation
- Added `docs/PHASE_2_COMPLETION.md` - Detailed implementation report
- Updated `README.md` with Phase 2 completion status
- Added type hints to action history module docstrings
- Updated `CHANGELOG.md` with comprehensive Phase 2 changes

---

## [Phase 4] - 2026-01-24

### Fixed
- **Torpedo Hit Mechanics**: Fixed hardcoded torpedo hit targets that didn't match game rules
  - Range 1-2 side aspect now correctly requires 3+ (was 5+)
  - Range 1-2 front/rear now correctly requires 4+ (was 6+)
  - All other ranges corrected to match JSON rules
  - Added regression test

### Added
- **Torpedo Reload System**: Fixed TubeState enum handling
- **AP Confirmation Dialog**: Double-click required when committing with unspent AP
- **Event Log Display**: AI phase messages now appear in event panel
- **Context-Sensitive Buttons**: Button text changes based on game state
- **Phase Advance Button**: Visible button for non-U-Boat phases

---

## [Phase 3.6] - 2026-01-17

### Added
- **Torpedo Tube States**: Three distinct states (LOADED, EMPTY, DAMAGED)
- **Damage System**: Complete damage resolution for U-boats and ships
- **Repair System**: Repair actions for damaged components
- **Victory/Defeat Conditions**: EXIT MAP button and loss conditions

---

## [Phase 1-3] - 2025-2026

### Added
- Turn system with 6-phase cycle
- AP rolling and management
- All validators (LOS, range, movement, torpedoes, repairs, combat, depth)
- All 7 U-boat actions
- Enemy AI (Merchants, Detection, Escorts, B-24)
- JSON-driven rules engine
- Hex-based movement system
- Depth management
- Mission-based gameplay

---

*For detailed implementation notes on each phase, see the `docs/` directory.*
