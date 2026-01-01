# Lone U-Boat Development Plan

**Project Goal:** Transform the current game infrastructure into a fully playable turn-based submarine warfare game.

**Estimated Timeline:** 12 weeks  
**Last Updated:** January 1, 2026

---

## Overview: What We're Building

We have excellent game infrastructure with:
- ✅ Hex-based game board with map overlay
- ✅ U-Boat positioning, movement, rotation, and depth changes
- ✅ Ship placement and rendering
- ✅ Toggle controls for map, grid, and terrain visualization
- ✅ Clean modular architecture
- ✅ Status box system with markers

We need to add **43 specific components** organized into **5 development phases** to create a complete game.

---

## Progress Tracker

### Phase 1: Foundation (Weeks 1-2) - Game Structure & UI Framework
**Status:** In Progress | **Target Completion:** Week 2

#### 1A: Game Screens
- [x] Create `core/screens/` module structure
- [x] Main menu screen with mission selection
- [x] Mission briefing screen (objectives, rules display)
- [x] Initial setup screen (U-boat depth & facing selection)
- [ ] In-game pause menu
- [x] Screen navigation system
- [x] **Tests:** Menu navigation, mission data loading

#### 1B: Turn Structure
- [ ] Add turn counter to game state
- [x] Implement `GamePhase` enum (6 phases)
- [ ] Create phase display overlay UI
- [ ] Add phase transition system
- [ ] Add "Next Phase" button (manual advancement)
- [ ] Phase announcement system
- [ ] **Tests:** Phase transition logic

#### 1C: Game State Persistence
- [ ] Save game state to file
- [ ] Load game state from file
- [ ] Auto-save functionality
- [ ] **Tests:** Save/load integrity

---

### Phase 2: Player Action System (Weeks 3-4) - U-Boat Phase
**Status:** Not Started | **Target Completion:** Week 4

#### 2A: Action Point System
- [ ] Implement AP rolling (3d6, take highest)
- [ ] Apply captain bonus (+1 AP if alive)
- [ ] Apply engine damage penalty (2d6 if damaged)
- [ ] Display AP counter in UI
- [ ] Action cost calculator based on depth
- [ ] Show available actions with costs
- [ ] **Tests:** AP calculation edge cases

#### 2B: Action Planning System
- [ ] Create `ActionQueue` class
- [ ] Action preview visualization
- [ ] Undo button (remove last action)
- [ ] Commit turn button
- [ ] Action validation before commit
- [ ] Visual feedback for queued actions
- [ ] Turn history/log display
- [ ] **Tests:** Action queue operations, undo/redo

#### 2C: Core Actions Implementation
- [ ] Refactor WASD controls into action system
- [ ] MOVE action with validation (shallow water, ships, land)
- [ ] TURN action (left/right, 60 degrees)
- [ ] CHANGE DEPTH action (once per turn limit)
- [ ] Hull damage depth restrictions
- [ ] Forced dive mechanics
- [ ] **Tests:** Action validation, movement rules

#### 2D: Repair Action
- [ ] Repair action UI (select what to repair)
- [ ] Hull damage cannot be repaired
- [ ] Flak/Deck gun (surface only)
- [ ] Engine repair (any depth if engineer alive)
- [ ] Torpedo tube repair (2 tubes per action)
- [ ] Engineer KIA restrictions
- [ ] **Tests:** Repair validation rules

---

### Phase 3: Combat Systems (Weeks 5-7) - Weapons & Damage
**Status:** Not Started | **Target Completion:** Week 7

#### 3A: Deck Gun System
- [ ] Line of sight calculator
- [ ] Range calculator (1-3 hexes)
- [ ] Targeting UI (click to select target ship)
- [ ] Hit calculation (2d6, range-based)
- [ ] Surface-only restriction
- [ ] Detection level set to 3 on hit
- [ ] **Tests:** LOS edge cases, hit probability

#### 3B: Torpedo System
- [ ] Torpedo tube status tracking (5 tubes)
- [ ] LOAD TORPEDOES action
- [ ] Weapons officer KIA penalty (1 tube vs 2)
- [ ] FIRE TORPEDOES action UI
- [ ] Select 1-3 torpedoes to fire
- [ ] Front (4 tubes) vs rear (1 tube) selection
- [ ] Torpedo hit table implementation
- [ ] Side vs Front/Rear targeting
- [ ] Missed torpedoes continue to other ships
- [ ] Detection level changes (+1 if 3 fired, +1 if any hit)
- [ ] **Tests:** Hit calculations, multi-ship targeting

#### 3C: Allied Ship Damage
- [ ] Allied Ship Damage Chart implementation
- [ ] Merchant ship damage (roll 1d6)
- [ ] Corvette damage (roll 1d6, modified)
- [ ] Destroyer damage (roll 1d6, modified)
- [ ] Damaged state tracking
- [ ] Catastrophic hit → immediate sinking
- [ ] Damaged → Sunk (second hit)
- [ ] Remove sunken ships from map
- [ ] Victory condition checking (mission objectives)
- [ ] **Tests:** Damage calculations, ship removal

#### 3D: U-Boat Damage System
- [ ] U-Boat Damage Chart implementation
- [ ] Critical Hit (roll 1d6 sub-table)
- [ ] Hull Damage (cannot be repaired, limit 4)
- [ ] General Damage (roll 1d6 sub-table)
- [ ] Crew KIA (roll 1d6, select crew member)
- [ ] Medic save mechanic (5+ on d6)
- [ ] Torpedo tube damage (random tubes)
- [ ] Engine damage effects
- [ ] Deck/Flak gun damage
- [ ] U-Boat destruction (hull damage 4 or critical)
- [ ] Damage status display
- [ ] Damage animations/notifications
- [ ] **Tests:** All damage types, medic saves, destruction

#### 3E: Detection Level System
- [ ] Detection level tracker (0-3)
- [ ] Display detection level in UI
- [ ] Medium depth check (-1 DL at turn start)
- [ ] Deep depth check (-2 DL at turn start)
- [ ] Combat detection changes
- [ ] Event-based detection changes
- [ ] **Tests:** Detection level calculations

---

### Phase 4: NPC AI & Automation (Weeks 8-10) - Enemy Turns
**Status:** Not Started | **Target Completion:** Week 10

#### 4A: Phase 2 - Merchant Ships
- [ ] Merchant ship movement AI
- [ ] Follow dotted line path
- [ ] Undamaged ships always move
- [ ] Damaged ships (roll 4+ to move)
- [ ] Handle ships exiting map
- [ ] Check mission failure (required ship escaped)
- [ ] Ship cannot enter occupied hex
- [ ] Forced dive if enters U-boat hex
- [ ] Animation for merchant movement
- [ ] **Tests:** Path following, damage penalties

#### 4B: Phase 3 - Detection Phase
- [ ] Find all escorts in LOS within 3 hexes
- [ ] Roll 1d6 for each escort
- [ ] Base detection by depth (Surfaced 1+, Periscope 2+, Medium 4+, Deep 5+)
- [ ] Engine damage modifier (-1 to roll needed)
- [ ] Sonar operator modifier (+1 to roll needed)
- [ ] Increase DL by 1 for each success
- [ ] Skip if DL already at 3
- [ ] **Tests:** Detection rolls, modifiers, LOS/range

#### 4C: Phase 4 - Escorts (Core System)
- [ ] Escort activation order (closest first)
- [ ] Tie-breaking (player choice)
- [ ] Dice calculation (Destroyer 3+DL, Corvette 2+DL)
- [ ] Damaged ship penalty (base dice only)
- [ ] Sort dice results (lowest to highest)
- [ ] Action resolver (process each die)
- [ ] **Tests:** Activation order, dice calculation

#### 4D: Phase 4 - Escort Movement
- [ ] MOVE action (one hex forward in facing direction)
- [ ] Cannot enter land hexes
- [ ] Cannot enter occupied hexes (other ships)
- [ ] Can enter U-boat hex (forced dive check)
- [ ] Blocked detection
- [ ] Movement animation
- [ ] **Tests:** Movement validation, forced dive

#### 4E: Phase 4 - Escort Turning
- [ ] Anchor hex targeting (DL 0-1)
- [ ] U-boat targeting (DL 2-3)
- [ ] Calculate smallest angle turn direction
- [ ] Facing target: only turn if blocked
- [ ] Facing away from target: turn randomly
- [ ] Same hex as target: only turn if blocked (random)
- [ ] Random turn implementation (d6: odd=left, even=right)
- [ ] **Tests:** Direction calculations, special cases

#### 4F: Phase 4 - Escort Attacks
- [ ] DEPTH CHARGE action
- [ ] Range check (0-1 hexes)
- [ ] Depth check (not surfaced)
- [ ] Corvette: roll 1d6 on U-Boat Damage Chart
- [ ] Destroyer: roll 2d6, take lowest
- [ ] FIRE action (gun)
- [ ] Surfaced check
- [ ] LOS check within 3 hexes
- [ ] Set DL to 3
- [ ] Roll as Critical Hit (1 on damage chart)
- [ ] Attack animations
- [ ] **Tests:** Attack conditions, damage application

#### 4G: Phase 5 - B24 Aircraft
- [ ] B24 placement (end of turn events)
- [ ] MOVE 2 hexes in facing direction
- [ ] Can enter any hex type (including land)
- [ ] Remove if exits map
- [ ] TURN toward U-boat (DL 2-3 only)
- [ ] Facing U-boat: never turn
- [ ] Facing away: turn randomly
- [ ] Same hex: only turn if facing off-map
- [ ] ATTACK check (surfaced/periscope, range 0-1)
- [ ] Flak gun defense (surfaced, undamaged gun)
- [ ] Roll 2d6: 8+ destroys (7+ if lookout alive)
- [ ] B24 attack (roll 1d6): 1=Critical, 2-3=Damage, 4-6=No damage
- [ ] Maximum 2 B24s on map
- [ ] **Tests:** Movement, turning, flak defense, attacks

---

### Phase 5: Game Rules & Polish (Weeks 11-12) - Complete Game
**Status:** Not Started | **Target Completion:** Week 12

#### 5A: Phase 6 - End Turn Events
- [ ] Roll 2d6, add together
- [ ] Event table per mission
- [ ] Place B24 (DL 2-3, trace longest hex line)
- [ ] Escort detection (repeat Phase 3)
- [ ] Radio interception (surfaced/periscope, DL 0→1)
- [ ] U-boat runs silently (not surfaced, engine OK, -1 DL)
- [ ] Hull pressure (Deep, +1 hull damage, ascend to medium)
- [ ] Event log display
- [ ] Event animations
- [ ] **Tests:** Each event type, conditions

#### 5B: Advanced Mechanics
- [ ] Forced dive implementation
- [ ] -2 AP penalty next turn
- [ ] Forced dive in shallow water = destruction
- [ ] Shallow water restrictions (periscope/surface only)
- [ ] Hull damage depth restrictions
- [ ] Immediate ascension on hull damage
- [ ] Destruction if cannot ascend (ship blocking)
- [ ] Ship collision prevention
- [ ] **Tests:** Edge cases, destruction scenarios

#### 5C: Victory & Defeat
- [ ] Mission objectives tracker
- [ ] Victory condition checking (each phase)
- [ ] Defeat conditions (U-boat destroyed)
- [ ] Defeat conditions (objective failure)
- [ ] Game over screen
- [ ] Victory statistics display
- [ ] Defeat reason display
- [ ] Replay option
- [ ] Return to main menu
- [ ] **Tests:** All victory/defeat scenarios

#### 5D: UI Polish & Features
- [ ] Turn announcement display
- [ ] Action feedback animations
- [ ] Sound effects (optional)
- [ ] Keyboard shortcuts reference
- [ ] Help/rules screen
- [ ] Tutorial mission (optional)
- [ ] Mission statistics tracking
- [ ] **Tests:** UI/UX validation

---

## Code Architecture

### New Module Structure
```
core/
├── actions.py              # Action system, ActionQueue
├── combat.py               # Combat calculations, damage
├── detection.py            # Detection mechanics
├── phase_manager.py        # Turn phase management
├── victory_conditions.py   # Win/loss checking
├── ai/
│   ├── __init__.py
│   ├── merchant.py         # Merchant ship AI
│   ├── escort.py           # Escort ship AI
│   └── aircraft.py         # B24 AI
├── screens/
│   ├── __init__.py
│   ├── menu.py             # Main menu
│   ├── briefing.py         # Mission briefing
│   ├── setup.py            # Initial U-boat setup
│   └── game_over.py        # End game screen
└── events.py               # End of turn events

tests/
├── test_models.py
├── test_hex_grid.py
├── test_actions.py
├── test_combat.py
├── test_detection.py
├── test_ai_movement.py
├── test_ai_escort.py
├── test_events.py
├── test_missions.py
└── test_integration.py
```

---

## Testing Strategy

### Unit Tests (Build alongside each feature)
- [ ] Set up pytest framework
- [ ] Models and coordinate tests
- [ ] Hex grid geometry tests
- [ ] Action validation tests
- [ ] Combat calculation tests
- [ ] Detection roll tests
- [ ] AI behavior tests
- [ ] Event trigger tests

### Integration Tests
- [ ] Complete turn sequences
- [ ] Multi-turn scenarios
- [ ] Combat interactions
- [ ] Victory/defeat scenarios
- [ ] Edge cases (forced dive, hull damage, etc.)

### Manual Testing
- [ ] Full mission 1 playthrough
- [ ] UI/UX validation
- [ ] Performance testing
- [ ] Save/load testing
- [ ] All missions playable

---

## Development Principles

### ✅ Do's
- Test as you go (TDD preferred)
- Keep modules small and focused
- Use feature flags for new systems
- Git commit after each working feature
- Update README with new features
- Document complex algorithms
- Playtest early and often

### ❌ Don'ts
- Don't break existing visualization code
- Don't build everything then test
- Don't skip validation logic
- Don't hardcode mission-specific data
- Don't forget edge cases
- Don't skip documentation

---

## Current Status

**Phase:** Phase 1A Complete - Game Screens Implemented  
**Next Task:** Phase 1B - Turn Structure (phase display overlay, phase transitions)  
**Blockers:** None

**Recent Completions:**
- ✅ Main menu with mission selection
- ✅ Mission briefing screen with text loading
- ✅ Setup screen for depth/facing selection
- ✅ Screen navigation and transitions
- ✅ GamePhase enum added to models
- ✅ ScreenManager for handling screen flow
- ✅ Updated main.py to use menu system

---

## Quick Reference: Game Rules Summary

### Turn Sequence (6 Phases)
1. **U-Boat Phase** - Player rolls AP, performs actions
2. **Merchant Ships Phase** - NPCs move along paths
3. **Detection Phase** - Escorts attempt detection
4. **Escorts Phase** - Escorts activate, move, attack
5. **Allied B24 Phase** - Aircraft move and attack
6. **End of Turn Events Phase** - Random events

### U-Boat Actions (7 types)
- MOVE (1-3 AP based on depth)
- TURN (1-3 AP based on depth)
- CHANGE DEPTH (1-2 AP, once per turn)
- REPAIR (2-4 AP)
- FIRE DECK GUN (2 AP, surface only)
- LOAD TORPEDOES (1-4 AP)
- FIRE TORPEDOES (2 AP)

### Detection Levels
- **0 - Silent:** Enemy unaware
- **1 - Aware:** Enemy knows you're present
- **2 - Traced:** Enemy knows approximate location
- **3 - Locked:** Enemy knows exact location

### Victory/Defeat
- **Victory:** Complete mission objectives
- **Defeat:** U-boat destroyed OR objective failure

---

## Notes & Decisions

### Design Decisions
- Action preview system prevents "undo after commit" exploits
- Manual phase advancement initially (can add auto-advance later)
- Visual feedback for all NPC actions (transparency/fairness)
- Save game after each committed turn

### Technical Decisions
- Use pygame for all rendering (consistent with current code)
- State machine pattern for game phases
- Event system for game state changes
- JSON for save files

### Future Enhancements (Post-MVP)
- Campaign mode (play all 10 missions)
- Difficulty settings
- Achievements/scoring system
- Sound effects and music
- Mission editor mode
- Online leaderboards
- Additional missions

---

## Questions & Issues

_Track questions and decisions here as they arise_

---

**Last Updated:** January 1, 2026  
**Version:** 1.0
