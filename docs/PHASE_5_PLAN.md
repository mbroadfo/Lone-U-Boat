# Phase 5 Development Plan: Polish & Quality of Life

## Overview

Phase 5 focuses on polish, UI improvements, and essential quality of life features to make the game production-ready.

## Current Status (February 2026)

**Completed:**
- ✅ Phase 1: Turn system (6-phase cycle, AP rolling)
- ✅ Phase 2: All validators (movement, combat, depth, repair, torpedoes)
- ✅ Phase 3: All 7 U-boat actions (Move, Rotate, DepthChange, Repair, DeckGun, LoadTorpedo, FireTorpedo)
- ✅ Phase 4: Merchant AI, Detection AI, Escort AI, B-24 AI (all automated)
- ✅ Victory/Defeat conditions (EXIT MAP button, merchant escape, U-boat destruction)
- ✅ Type hint cleanup (336/336 tests passing, 0 Pylance errors)
- ✅ Combat resolution UI blocking (prevents accidental actions during combat)

**Test Coverage:** 336 tests across 24+ test files, **all passing**

**Mission 1 Status:**
- ✅ Fully playable with automated AI
- ✅ All game-ending conditions implemented and tested
- ✅ Complete turn-based gameplay loop functional
- ✅ Zero type errors, comprehensive test coverage

## Phase 5 Immediate Priorities

### Must Have (Next 2-3 Weeks)

1. **Victory/Defeat Visual Overhaul** ⬜ HIGH PRIORITY
   - Replace full-screen popup with non-intrusive overlay
   - Show final game state (like destroyed entity overlays)
   - Add proper victory overlay (currently missing)
   - Top banner or corner indicator instead of modal dialog
   - Allow player to see final positions before returning to menu

2. **Save/Load System** ⬜
   - Save game state mid-mission
   - Resume from saved games
   - Auto-save on phase transitions
   - Save file management UI

3. **Sound Effects** ⬜
   - Torpedo fire/hit sounds
   - Depth charge explosions
   - Sonar pings
   - Ship destruction
   - Phase transition sounds

4. **Tutorial/Help System** ⬜
   - In-game help overlay
   - Action tooltips
   - Quick reference card
   - First-time player guidance

## Phase 5 Scope

### 5.1 Escort AI (Complete Phase 4)

**Goal:** Automate escort ship movement and attack decisions based on detection level.

#### 5.1.1 Escort Movement AI

**Rules (from RULES.md Phase 4):**
- Each escort rolls dice based on detection level: `2 + DL` dice for Destroyers, `1 + DL` dice for Corvettes
- Each die result determines action: 1-2 = MOVE, 3-4 = TURN, 5-6 = FIRE/DEPTH CHARGE
- Move toward U-boat (pathfinding), turn to face U-boat
- Activation order: Closest escort to U-boat activates first

**Implementation:**
```
core/escort_ai.py:
- EscortAI class (similar to MerchantAI, DetectionAI pattern)
- roll_escort_actions(escort, detection_level) -> List[ActionType]
- get_next_hex_toward_target(escort, u_boat, land_hexes, hex_grid)
- calculate_facing_to_target(from_hex, to_hex)
- execute_escort_phase(ships, u_boat, detection_level, land_hexes, hex_grid)
```

**Testing:**
- test_escort_ai.py (~20 tests)
  - Dice rolling by ship type and DL
  - Movement toward U-boat with pathfinding
  - Turning to face U-boat
  - Activation order (closest first)
  - Multiple escorts coordination
- test_escort_integration.py (~5 tests)
  - Integration with game loop
  - Phase execution
  - Detection level effects

**Estimated Time:** 6-8 hours

#### 5.1.2 Depth Charge Attacks

**Rules (from RULES.md):**
- Only at DL 1-3
- Range 0 only (same hex as U-boat)
- Escort must be facing U-boat
- Attack only if U-boat is submerged (Periscope/Medium/Deep)
- Roll 2d6, consult depth charge table
- Results: Miss, Hull Damage, U-boat Damage Chart roll, Crew KIA

**Implementation:**
```
core/actions/depth_charge_action.py:
- DepthChargeAction class
- validate(): check range 0, DL >= 1, facing, depth
- execute(): roll 2d6, apply damage from table
- Use existing damage systems (uboat_damage.py)

core/combat_resolver.py: (extend existing)
- resolve_depth_charge_attack(escort, u_boat, dice_roll)
- depth_charge_damage_table (from JSON)
```

**JSON Configuration:**
```
escort_ai_baseline.json:
- depth_charge_system:
  - range: 0
  - min_detection_level: 1
  - requires_facing: true
  - valid_depths: ["periscope", "medium", "deep"]
  - damage_table: { 2: "miss", 3: "+1_hull", ... 12: "roll_damage_chart" }
```

**Testing:**
- test_depth_charge.py (~12 tests)
  - Validation (range, DL, facing, depth)
  - Damage table rolls (all outcomes)
  - Hull damage application
  - U-boat damage chart integration
  - Crew casualties
- test_depth_charge_integration.py (~3 tests)
  - Escort phase integration
  - Multiple escorts attacking

**Estimated Time:** 5-7 hours

#### 5.1.3 Escort Gunfire

**Rules (from RULES.md):**
- Only if U-boat is Surfaced
- Only at DL 1-3
- Use existing deck gun combat system (range-based 2d6 roll)
- Consult ship damage table for U-boat

**Implementation:**
```
core/escort_ai.py: (extend)
- can_use_gunfire(escort, u_boat, detection_level) -> bool
- execute_gunfire_attack(escort, u_boat) -> ActionResult
- Use existing CombatResolver.resolve_deck_gun_attack()
```

**Testing:**
- test_escort_gunfire.py (~8 tests)
  - Validation (surfaced, DL, range)
  - Combat resolution
  - Damage application
- Reuse existing combat resolver tests

**Estimated Time:** 3-4 hours

### 5.2 B-24 Aircraft Phase (Optional - Mission Dependent)

**Goal:** Automate B-24 aircraft movement and attacks.

**Rules (from RULES.md Phase 5):**
- Move 2 hexes in facing direction
- Remove if exits map
- Turn toward U-boat if DL 2-3
- Attack at range 0-1 if U-boat Surfaced/Periscope
- U-boat Flak gun defense (2d6, destroy on 8+, 7+ if Lookout alive)
- B-24 attack: 1d6 on damage chart

**Implementation:**
```
core/aircraft_ai.py:
- AircraftAI class
- move_aircraft(aircraft, exit_hexes)
- turn_toward_target(aircraft, u_boat, detection_level)
- can_attack(aircraft, u_boat) -> bool
- execute_flak_defense(u_boat) -> bool  # Returns True if B-24 destroyed
- execute_aircraft_attack(aircraft, u_boat) -> ActionResult
- execute_b24_phase(aircraft_list, u_boat, detection_level, exit_hexes)
```

**JSON Configuration:**
```
escort_ai_baseline.json:
- aircraft_system:
  - move_distance: 2
  - turn_detection_threshold: 2
  - attack_range: 1
  - valid_attack_depths: ["surfaced", "periscope"]
  - flak_defense:
    - base_threshold: 8
    - lookout_threshold: 7
  - damage_table: { 1-2: "+2_hull", 3-4: "roll_damage", 5-6: "miss" }
```

**Testing:**
- test_aircraft_ai.py (~15 tests)
  - Movement (2 hexes, exit detection)
  - Turning logic (DL-based, facing)
  - Attack validation (range, depth)
  - Flak defense (thresholds, lookout bonus)
  - Damage application
- test_aircraft_integration.py (~3 tests)
  - B-24 phase execution
  - Multiple aircraft

**Estimated Time:** 6-8 hours

**Note:** This can be deferred if Mission 1 doesn't have B-24s.

### 5.3 End Turn Events Phase (Phase 6)

**Goal:** Implement random events system for mission variety.

**Rules (from RULES.md Phase 6):**
- Roll 2d6 at end of turn
- Consult mission-specific event table
- Events: New ships appear, weather changes, B-24 spawns, etc.

**Implementation:**
```
core/events.py:
- EventSystem class
- load_event_table(mission_rules)
- roll_event(dice_roller) -> Event
- execute_event(event, game_state) -> List[str]  # Return messages
```

**JSON Configuration:**
```
mission_1_rules.json:
- end_turn_events:
  - 2: { type: "new_ship", ship_type: "corvette", position: [x,y], facing: "N" }
  - 3: { type: "weather", effect: "fog", detection_modifier: -1 }
  - ...
  - 12: { type: "reinforcements", ships: [...] }
```

**Testing:**
- test_events.py (~10 tests)
  - Event rolling
  - Ship spawning
  - Weather effects
  - B-24 spawning
- test_events_integration.py (~3 tests)
  - End turn phase execution
  - Event application

**Estimated Time:** 5-6 hours

## Phase 5 Priorities

### Must Have (MVP)
1. ✅ Escort Movement AI (pathfinding toward U-boat)
2. ✅ Depth Charge attacks
3. ✅ Escort Gunfire (reuse existing combat)
4. ⬜ Basic End Turn Events (ship spawning)

### Should Have
5. ⬜ Advanced escort coordination (don't stack on same hex)
6. ⬜ B-24 Aircraft (if mission has them)
7. ⬜ Full event system (weather, special events)

### Nice to Have
8. ⬜ Escort evasion (move away if damaged)
9. ⬜ Dynamic difficulty (event frequency adjustment)

## Implementation Order

### Week 1: Escort AI Foundation
**Days 1-2:** Escort Movement AI
- EscortAI class structure
- Dice rolling by DL
- Movement toward U-boat
- Turning logic
- Tests (20 tests)

**Days 3-4:** Depth Charge System
- DepthChargeAction class
- Validation rules
- Damage table implementation
- Integration with damage systems
- Tests (15 tests)

**Day 5:** Escort Gunfire
- Gunfire validation
- Integration with existing combat
- Tests (8 tests)

### Week 2: Aircraft & Events
**Days 6-7:** B-24 Aircraft (Optional)
- AircraftAI class
- Movement and turning
- Attack and flak defense
- Tests (18 tests)

**Days 8-9:** End Turn Events
- EventSystem class
- Mission event tables
- Ship spawning
- Tests (13 tests)

**Day 10:** Integration & Polish
- Full game loop testing
- Performance optimization
- Documentation updates

## Testing Strategy

### Unit Tests
- Each AI system has 10-20 unit tests
- Test all rule combinations
- Test edge cases (DL 0, DL 3, damaged ships)
- MockDice for deterministic results

### Integration Tests
- Each phase has 3-5 integration tests
- Test phase execution in game loop
- Test AI coordination (multiple escorts)
- Test turn progression with events

### Manual Testing
- Play complete turns with all AI active
- Verify visual feedback (ships moving)
- Test edge cases (all escorts destroyed, max DL)
- Performance testing (many ships on map)

## JSON Configuration Updates

### escort_ai_baseline.json
```json
{
  "escort_movement": {
    "destroyer_dice": "2 + detection_level",
    "corvette_dice": "1 + detection_level",
    "action_table": {
      "1-2": "move",
      "3-4": "turn",
      "5-6": "attack"
    },
    "activation_order": "closest_first"
  },
  "depth_charge_system": {
    "range": 0,
    "min_detection_level": 1,
    "requires_facing": true,
    "valid_depths": ["periscope", "medium", "deep"],
    "damage_table": {
      "2": "miss",
      "3-4": "+1_hull",
      "5-6": "roll_damage_chart",
      "7-8": "+1_hull_and_roll",
      "9-10": "roll_damage_chart",
      "11": "+2_hull",
      "12": "roll_damage_chart_and_kia"
    }
  },
  "gunfire_system": {
    "min_detection_level": 1,
    "valid_depths": ["surfaced"],
    "use_deck_gun_table": true
  },
  "aircraft_system": {
    "move_distance": 2,
    "turn_detection_threshold": 2,
    "attack_range": 1,
    "valid_attack_depths": ["surfaced", "periscope"],
    "flak_defense": {
      "base_threshold": 8,
      "lookout_bonus": -1
    },
    "damage_table": {
      "1-2": "+2_hull",
      "3-4": "roll_damage_chart",
      "5-6": "miss"
    }
  }
}
```

## Success Criteria

### Phase 5 Complete When:
1. ✅ All escort ships move intelligently toward U-boat
2. ✅ Escorts attack with depth charges when in range
3. ✅ Escorts use gunfire when U-boat surfaced
4. ✅ B-24 aircraft move and attack (if in mission)
5. ✅ End turn events spawn new threats
6. ✅ All AI actions logged to phase log
7. ✅ All tests passing (100+ new tests)
8. ✅ Zero type errors
9. ✅ Game fully playable without player intervention for enemy forces

### Definition of Done:
- [ ] All AI systems implemented and tested
- [ ] Integration tests verify game loop
- [ ] Documentation updated (README, phase docs)
- [ ] Manual playthrough confirms correct behavior
- [ ] Performance acceptable (< 100ms per AI decision)
- [ ] Code reviewed and committed

## Estimated Total Time

| Component | Time Estimate |
|-----------|--------------|
| Escort Movement AI | 6-8 hours |
| Depth Charge System | 5-7 hours |
| Escort Gunfire | 3-4 hours |
| B-24 Aircraft | 6-8 hours |
| End Turn Events | 5-6 hours |
| Integration & Polish | 4-5 hours |
| **Total** | **29-38 hours** |

With focused 4-hour sessions: **8-10 days**

## Post-Phase 5 Roadmap

### Phase 6: Victory Conditions & Mission Objectives
- Mission completion tracking
- Victory/defeat conditions
- Score calculation
- Mission debriefing

### Phase 7: UI Polish
- Action selection UI
- Combat animation
- Sound effects
- Phase transition animations
- Tutorial system

### Phase 8: Additional Missions
- Mission 2-N implementation
- New map layouts
- Unique mission events
- Difficulty progression

## Dependencies

**Phase 5 depends on:**
- ✅ Phase 3 (all U-boat actions)
- ✅ Phase 4 (Merchant AI, Detection)
- ✅ Combat resolver (deck gun, torpedoes)
- ✅ Damage systems (ship, U-boat)
- ✅ Turn manager (phase cycle)

**Phase 5 enables:**
- Complete AI opponent
- Full game loop automation
- Mission objectives system
- Victory conditions

## Risk Assessment

### Low Risk
- Escort movement (similar to Merchant AI)
- Depth charges (extend existing damage system)
- Escort gunfire (reuse combat resolver)

### Medium Risk
- B-24 aircraft (new movement type, aerial combat)
- Event system (many edge cases, mission variety)

### Mitigation
- Extensive unit testing
- Start with MVP (escorts only)
- Add aircraft/events as Phase 5.1, 5.2
- Manual testing after each component

## Next Steps

1. **Immediate:** Start with Escort Movement AI
   - Create `core/escort_ai.py`
   - Implement dice rolling and action determination
   - Pathfinding toward U-boat
   - Tests (20 tests)

2. **Week 1 Goal:** Complete Escort AI with depth charges
   - Fully functional escort opposition
   - ~35 new tests
   - Game dramatically more challenging

3. **Week 2 Goal:** Add aircraft and events
   - Complete automation
   - ~30 more tests
   - Game fully playable

---

**Status:** Ready to begin Phase 5 implementation
**Last Updated:** January 13, 2026
