# Test Run Analysis - Issues Found

## Issue 1: Depth Change Restriction NOT Enforced ❌

**Rule**: "Once per turn, one level only" (mission_1_briefing.json line 33)

**What Happened**: Turn 8 shows `Depth(2AP), Depth(2AP) [4AP used] ->SURFACED`
- U-boat went from PERISCOPE → MEDIUM → SURFACED in a single turn
- This violates the "once per turn" rule

**Root Cause**: 
- `TurnManager` has `depth_changed_this_turn` flag
- `DepthChangeAction.validate()` was passing hardcoded `False` instead of checking the flag
- ActionCatalog generates ALL depth changes without filtering for this restriction

**Fix Applied**: 
- Updated DepthChangeAction to check `game_state.turn_manager.depth_changed_this_turn`
- Updated execute() to set the flag when depth changes

---

## Issue 2: Missing Actions Not Available ⚠️

**Available Actions**: Move, Rotate, Depth, Repair, DeckGun, LoadTorpedo, FireTorpedo

**What's Actually Generated**:
- ✅ Move - Working
- ✅ Rotate - Working  
- ✅ Depth - Working (but was allowing multiple per turn)
- ✅ Repair - Generated (but no damage to repair)
- ✅ DeckGun - Generated (but ships out of range)
- ✅ LoadTorpedo - Generated (but tubes already loaded)
- ✅ FireTorpedo - Generated (but randomly not selected)

**Conclusion**: All action types ARE being generated correctly. The AI just isn't selecting certain actions because:
- Combat actions only work when ships are in range
- Repair only works when there's damage
- Load torpedoes only works when tubes are empty

---

## Issue 3: Merchant Exit Analysis 📍

**Merchant Path**: (1,4) → (6,9) over 10 turns
**Exit Hex**: (6,10) per mission_1_config.py line 97

**Distance from Exit**: 
- Final position: (6,9)
- Exit position: (6,10)
- Distance: **1 hex away from exit**

**Conclusion**: Merchant DID NOT exit, but was 1 turn away from exiting.

---

## Issue 4: End Turn Events Broken ❌

**Rolls vs Expected Events**:

| Turn | Roll | Expected Event | Actual | Status |
|------|------|----------------|--------|--------|
| 1 | 5 | B-24 spawn if DL=2-3 | "No event" | ✅ Correct (DL=0) |
| 2 | 4 | B-24 spawn if DL=2-3 | "No event" | ✅ Correct (DL=0) |
| 3 | 6 | Extra Detection if DL≠3 | "No event" | ❌ WRONG |
| 4 | 8 | Hull pressure if Deep | "No event" | ✅ Correct (Periscope) |
| 5 | 8 | Hull pressure if Deep | "No event" | ✅ Correct (Periscope) |
| 6 | 5 | B-24 spawn if DL=2-3 | "No event" | ✅ Correct (DL=0) |
| 7 | 5 | B-24 spawn if DL=2-3 | "No event" | ✅ Correct (DL=0) |
| 8 | 8 | Hull pressure if Deep | "No event" | ✅ Correct (Surfaced) |
| 9 | 8 | Hull pressure if Deep | "No event" | ✅ Correct (Surfaced) |
| 10 | 9 | Silent running -1 DL | "No event" | ❌ WRONG |

**Bugs Found**:
- **Turn 3 (Roll 6)**: Should trigger extra Detection phase (event says "If DL is not already at 3, perform Phase 3 again now")
- **Turn 10 (Roll 9)**: Should reduce DL by 1 if not surfaced and engine not damaged (U-boat was PERISCOPE depth with no engine damage)

**Conclusion**: End Turn Events system has bugs - not all events are being triggered correctly.

---

## Issue 5: Action Counter Broken ❌

**Statistics Show**: "Total actions taken: 0"

**Reality**: 
- Turn 1: 3 moves = 3 actions
- Turn 2: 2 moves = 2 actions  
- Turn 3: 1 rotate + 1 depth = 2 actions
- Turn 4: 2 moves = 2 actions
- Turn 5: 1 move + 1 rotate + 1 move = 3 actions
- Turn 6: 3 moves = 3 actions
- Turn 7: 2 moves + 1 rotate = 3 actions
- Turn 8: 2 depth = 2 actions (should only be 1 after fix!)
- Turn 9: 1 rotate + 1 rotate = 2 actions
- Turn 10: 1 depth + 1 rotate + 1 move = 3 actions

**Actual Total**: ~25 actions (will be ~24 after depth fix)

**Where to Fix**: Need to find where action counting happens and ensure it increments when actions are committed.

---

## Summary

### Critical Bugs Fixed:
1. ✅ **Depth change "once per turn"** - Now enforced via turn_manager flag

### Critical Bugs Remaining:
1. ❌ **End Turn Events** - Events on rolls 6 and 9+ not triggering
2. ❌ **Action Counter** - Shows 0 when ~25 actions occurred

### Not Bugs (Working as Designed):
1. ✅ Detection never triggered - Ships too far apart (random AI issue, not code bug)
2. ✅ No combat - Ships out of range (random AI issue, not code bug)
3. ✅ All action types generated - Combat/repair just not relevant in this scenario
4. ✅ Merchant near exit - Will exit on turn 11

### Test Quality Assessment:
- **Random AI** creates boring scenarios with no ship interaction
- Need either: smarter AI, smaller map, or forced engagement scenarios
- Current test validates action generation but not combat systems
