# Lone U-Boat - Gameplay Development Plan

**Created**: January 4, 2026  
**Status**: Planning Phase  
**Goal**: Transform the visual prototype into a fully playable turn-based tactical submarine game

---

## Table of Contents

1. [Overview](#overview)
2. [Current State Analysis](#current-state-analysis)
3. [Development Phases](#development-phases)
4. [Phase 1: Core Turn System & UI](#phase-1-core-turn-system--ui)
5. [Phase 2: Action Subsystems](#phase-2-action-subsystems)
6. [Phase 3: U-Boat Actions](#phase-3-u-boat-actions)
7. [Phase 4: AI & Enemy Phases](#phase-4-ai--enemy-phases)
8. [Phase 5: Combat & Damage](#phase-5-combat--damage)
9. [Phase 6: Victory Conditions & Polish](#phase-6-victory-conditions--polish)
10. [Technical Architecture](#technical-architecture)

---

## Overview

This plan transforms Lone U-Boat from a visual prototype into a fully playable game by implementing:

- **Turn-based gameplay** with 6 distinct phases per turn
- **Action Point (AP) system** with depth-based action costs
- **Validation subsystems** (LOS, range, terrain, movement)
- **AI behaviors** for merchants and escorts based on JSON rules
- **Combat resolution** (deck gun, torpedoes, depth charges)
- **Detection mechanics** influencing AI behavior
- **Victory/defeat conditions** with mission objectives

### Design Principles

1. **Player Control**: Player advances through phases at their own pace (not auto-advancing)
2. **Clear Feedback**: Always show current phase, available AP, valid actions
3. **Undo-Friendly**: Where possible, allow action review before committing
4. **JSON-Driven**: Use existing mission rule files to drive mechanics
5. **Incremental**: Each phase builds on previous work, always playable

---

## Current State Analysis

### ✅ **What We Have**

**Foundation:**
- Clean modular architecture (models, hex_grid, renderer, game_state)
- Hex coordinate system with axial math
- Asset management and rendering pipeline
- Resolution-independent board layout system

**Data Structures:**
- `UBoat` class with position, facing, depth, damage, crew, torpedoes
- `Ship` class with position, facing, type, damage
- `HexCoord`, `Facing`, `Depth` enums
- `GamePhase` enum (defined but not used)

**Visual Systems:**
- Map rendering with hex grid overlay
- U-boat and ship rendering with facing indicators
- Status box system with conditional markers
- Depth visualization

**Mission System:**
- JSON rule files with layered inheritance:
  - `core_system_rules.json` (immutable mechanics)
  - `u_boat_ruleset_default.json` (standard capabilities)
  - `escort_ai_baseline.json` (AI behaviors)
  - `mission_X_rules.json` (mission-specific)
- `MissionRules` loader class
- Mission configuration files with terrain, starting positions

**Basic Controls:**
- Movement (W), rotation (Q/E), depth (Z/X)
- Display toggles (G, M, V, S)

### ❌ **What's Missing**

**Core Gameplay:**
- No turn structure or phase management
- No AP rolling/tracking/spending
- No action validation
- No AI behaviors
- No combat resolution
- No detection level effects
- No victory/defeat conditions

**Subsystems:**
- Line of Sight (LOS) calculation
- Range calculation
- Movement validation
- Terrain restrictions
- Hit resolution (dice rolling)
- Damage application

**UI/UX:**
- No phase indicator
- No AP counter
- No action menu/buttons
- No action cost preview
- No turn log/history
- No confirmation dialogs

---

## Development Phases

The work is broken into 6 phases, each deliverable and playable:

| Phase | Focus | Deliverable | Estimated Effort |
|-------|-------|-------------|------------------|
| **1** | Turn System & UI | Working turn loop with phase advancement | 2-3 days |
| **2** | Action Subsystems | LOS, range, movement validation | 2-3 days |
| **3** | U-Boat Actions | All 7 player actions functional | 3-4 days |
| **4** | AI & Enemy Phases | Merchants, escorts, aircraft movement | 3-4 days |
| **5** | Combat & Damage | Attack resolution, damage charts | 2-3 days |
| **6** | Victory & Polish | Objectives, end conditions, refinement | 2-3 days |

**Total Estimated Time**: 14-20 days of focused development

---

## Phase 1: Core Turn System & UI

**Goal**: Establish the turn-based structure with player-controlled phase advancement

### 1.1 Turn State Management

**New Module**: `core/turn_manager.py`

```python
class TurnManager:
    """Manages game turns and phase transitions."""
    
    def __init__(self, mission_rules: MissionRules):
        self.turn_number: int = 1
        self.current_phase: GamePhase = GamePhase.UBOAT_PHASE
        self.mission_rules = mission_rules
    
    def advance_phase(self) -> GamePhase:
        """Move to next phase, handle turn wrap."""
        
    def start_turn(self):
        """Initialize new turn (roll AP, apply depth DL modifiers)."""
        
    def end_turn(self):
        """Clean up turn state, increment turn counter."""
        
    def can_advance_phase(self) -> tuple[bool, str]:
        """Check if current phase can advance (return reason if not)."""
```

**Integration**: Add `TurnManager` to `Game` class in `game_state.py`

### 1.2 Action Point System

**Extend**: `core/turn_manager.py`

```python
class ActionPointTracker:
    """Tracks and validates AP spending."""
    
    def __init__(self, initial_ap: int):
        self.total_ap: int = initial_ap
        self.spent_ap: int = 0
        self.action_history: List[tuple[str, int]] = []
    
    def can_afford(self, action: str, cost: int) -> bool:
        """Check if enough AP remains."""
        
    def spend(self, action: str, cost: int) -> bool:
        """Spend AP on action, return success."""
        
    def remaining(self) -> int:
        """Get remaining AP."""
        
    def reset(self, new_ap: int):
        """Reset for new turn."""
```

**AP Rolling Logic**:
- Read from `u_boat_ruleset_default.json` → `u_boat_ap_rules`
- Roll 3d6 (or 2d6 if engine damaged)
- Take highest die
- Add +1 if captain alive
- Apply forced dive penalty if applicable

### 1.3 Phase UI Overlay

**Extend**: `core/renderer.py`

Add methods for rendering turn info:

```python
def render_turn_info(self, turn_num: int, phase: GamePhase, ap: int):
    """Render turn number, current phase, and AP in top-right corner."""
    
def render_phase_transition(self, next_phase: GamePhase):
    """Show brief transition animation/message."""
    
def render_action_history(self, history: List[tuple[str, int]]):
    """Show log of actions taken this turn."""
```

**Layout**:

```text
┌─────────────────────────────────────┐
│ Turn 3 │ U-Boat Phase │ AP: 5/7     │  ← Top bar
├─────────────────────────────────────┤
│                                     │
│     [Game board]                    │
│                                     │
│                                     │
├─────────────────────────────────────┤
│ [Space] Next Phase                  │  ← Bottom hint
│ Actions: MOVE(1) TURN(1) FIRE(2)    │
└─────────────────────────────────────┘
```

### 1.4 Phase Advancement Controls

**Extend**: `core/game_state.py` → `handle_events()`

Add phase control keys:
- **SPACE**: Advance to next phase
- **ENTER**: Confirm action and advance (where applicable)
- **BACKSPACE**: Undo last action (if possible)
- **TAB**: Show action menu (future)

### 1.5 Phase-Specific Behavior

**Phases to Implement**:

1. **U-Boat Phase** (Player active)
   - Show AP counter
   - Allow actions until AP depleted or player advances
   - Track action history

2. **Merchant Phase** (Auto-execute, require advancement)
   - Show "Merchant Ships Moving..." message
   - Execute merchant movement (initially just message)
   - Player presses SPACE to continue

3. **Detection Phase** (Auto-execute)
   - Calculate detection level changes
   - Show DL change notification
   - Auto-advance or wait for player

4. **Escort Phase** (Auto-execute)
   - Show "Escorts Acting..." message
   - Execute escort behaviors (initially just message)
   - Player presses SPACE to continue

5. **B24 Phase** (Conditional)
   - Only if aircraft present
   - Auto-skip if none

6. **End Turn Phase** (Auto-execute)
   - Clean up markers
   - Check victory/defeat conditions (stub for now)
   - Roll new AP
   - Start next turn

### Deliverables

- [ ] `TurnManager` class managing phase flow
- [ ] `ActionPointTracker` class with rolling logic
- [ ] Turn info UI overlay (turn #, phase, AP)
- [ ] SPACE key advances phases
- [ ] Phase-specific messages display
- [ ] Action history log (text-based)
- [ ] All 6 phases cycle correctly (even if some are stubs)

**Testing**: Play through 3 complete turns, verify phase cycling and AP rolling

---

## Phase 2: Action Subsystems

**Goal**: Build reusable validation systems for actions

### 2.1 Line of Sight (LOS) System

**New Module**: `core/los.py`

```python
class LineOfSight:
    """Calculate line of sight between hexes."""
    
    @staticmethod
    def has_los(
        from_hex: HexCoord,
        to_hex: HexCoord,
        land_hexes: Set[HexCoord]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if LOS exists between two hexes.
        
        Returns:
            (has_los, blocking_reason)
            
        Rules:
        - Adjacent hexes: always true
        - Range 2: trace through 1 or 2 hexes, Land blocks
        - Range 3: trace through exactly 2 hexes, Land blocks
        - Units never block LOS
        """
        
    @staticmethod
    def get_intervening_hexes(
        from_hex: HexCoord,
        to_hex: HexCoord
    ) -> List[HexCoord]:
        """Get hexes between from_hex and to_hex."""
```

**Implementation Details**:
- Use axial coordinate geometry
- For range 2: check if direct line or edge case
- For range 3: always exactly 2 intervening hexes
- Reference RULES.md diagrams for edge cases

### 2.2 Range Calculation

**Extend**: `core/hex_grid.py`

```python
class HexGrid:
    """Add range calculation methods."""
    
    @staticmethod
    def hex_distance(a: HexCoord, b: HexCoord) -> int:
        """Calculate hex distance (axial cube conversion)."""
        return (abs(a.q - b.q) 
                + abs(a.q + a.r - b.q - b.r)
                + abs(a.r - b.r)) // 2
    
    @staticmethod
    def hexes_in_range(
        center: HexCoord,
        range: int,
        valid_hexes: Optional[Set[HexCoord]] = None
    ) -> List[HexCoord]:
        """Get all hexes within range of center."""
```

### 2.3 Movement Validator

**New Module**: `core/movement.py`

```python
class MovementValidator:
    """Validate movement actions."""
    
    def __init__(
        self,
        valid_hexes: Set[HexCoord],
        land_hexes: Set[HexCoord],
        shallow_hexes: Set[HexCoord]
    ):
        self.valid_hexes = valid_hexes
        self.land_hexes = land_hexes
        self.shallow_hexes = shallow_hexes
    
    def can_move_to(
        self,
        target: HexCoord,
        u_boat: UBoat,
        ships: List[Ship]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if U-boat can move to target hex.
        
        Rules:
        - Cannot enter Land hexes
        - Cannot enter Shallow unless Surfaced or Periscope
        - Cannot enter Ship hex unless Medium or Deep
        - Must be valid hex on map
        """
        
    def can_pass_through(
        self,
        hex: HexCoord,
        depth: Depth,
        ships: List[Ship]
    ) -> tuple[bool, Optional[str]]:
        """Check if U-boat at depth can occupy hex."""
```

### 2.4 Depth Validator

**New Module**: `core/depth.py`

```python
class DepthValidator:
    """Validate depth changes."""
    
    @staticmethod
    def can_change_depth(
        u_boat: UBoat,
        new_depth: Depth,
        current_hex: HexCoord,
        shallow_hexes: Set[HexCoord],
        ships: List[Ship]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if depth change is valid.
        
        Rules:
        - Can only change by 1 level
        - Cannot go below Periscope in shallow water
        - Cannot go above Medium if ship on hex
        - Hull damage restricts max depth
        - Once per turn restriction (tracked elsewhere)
        """
        
    @staticmethod
    def max_depth_for_damage(hull_damage: int) -> Depth:
        """Get maximum allowed depth based on hull damage."""
        # 0 damage: DEEP
        # 1 damage: MEDIUM
        # 2 damage: PERISCOPE
        # 3 damage: SURFACED
```

### 2.5 Action Cost Calculator

**New Module**: `core/action_costs.py`

```python
class ActionCostCalculator:
    """Calculate action costs from JSON rules."""
    
    def __init__(self, mission_rules: MissionRules):
        self.rules = mission_rules
        self.action_costs = self._load_action_costs()
    
    def get_cost(self, action: str, depth: Depth) -> Optional[int]:
        """Get AP cost for action at given depth."""
        
    def get_all_costs(self, depth: Depth) -> Dict[str, int]:
        """Get all action costs at given depth."""
        
    def _load_action_costs(self) -> Dict[str, Dict[str, int]]:
        """Parse u_boat_action_costs from JSON rules."""
```

### 2.6 Visual Feedback for Validation

**Extend**: `core/renderer.py`

```python
def render_valid_movement_hexes(
    self,
    u_boat: UBoat,
    validator: MovementValidator
):
    """Highlight hexes U-boat can move to in green."""
    
def render_invalid_hex_feedback(
    self,
    hex: HexCoord,
    reason: str
):
    """Show red X or message on invalid hex."""
    
def render_range_indicator(
    self,
    center: HexCoord,
    range: int,
    color: tuple
):
    """Draw range circle/hexes around center."""
```

### Deliverables

- [ ] `LineOfSight` class with LOS calculation
- [ ] `HexGrid.hex_distance()` for range
- [ ] `MovementValidator` enforcing terrain/depth rules
- [ ] `DepthValidator` enforcing depth change rules
- [ ] `ActionCostCalculator` reading from JSON
- [ ] Visual feedback for valid/invalid moves
- [ ] Unit tests for LOS edge cases
- [ ] Unit tests for range calculation

**Testing**: Verify LOS at ranges 1-3 with Land blocking, movement restrictions at each depth

---

## Phase 3: U-Boat Actions

**Goal**: Implement all 7 player actions with full validation

### 3.1 Action Architecture

**New Module**: `core/actions.py`

```python
class Action(ABC):
    """Base class for all U-boat actions."""
    
    @abstractmethod
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        """Check if action is currently valid."""
        
    @abstractmethod
    def get_cost(self, game_state) -> int:
        """Get AP cost for this action."""
        
    @abstractmethod
    def execute(self, game_state) -> bool:
        """Perform the action, return success."""
        
    @abstractmethod
    def get_name(self) -> str:
        """Get action display name."""
```

### 3.2 Movement Action

```python
class MoveAction(Action):
    """Move U-boat forward one hex."""
    
    def __init__(self, validator: MovementValidator):
        self.validator = validator
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Check target hex using facing
        # Use MovementValidator
        # Check AP sufficient
        
    def get_cost(self, game_state) -> int:
        # Surf=1, Peri=2, Med=3, Deep=3
        
    def execute(self, game_state) -> bool:
        # Move U-boat to new position
        # Deduct AP
        # Log action
```

### 3.3 Turn Action

```python
class TurnAction(Action):
    """Rotate U-boat 60° left or right."""
    
    def __init__(self, direction: int):  # -1 left, +1 right
        self.direction = direction
    
    def get_cost(self, game_state) -> int:
        # Surf=1, Peri=1, Med=2, Deep=3
```

### 3.4 Change Depth Action

```python
class ChangeDepthAction(Action):
    """Change depth by one level."""
    
    def __init__(self, direction: int, validator: DepthValidator):
        self.direction = direction  # -1 shallower, +1 deeper
        self.validator = validator
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Check once-per-turn restriction
        # Use DepthValidator
        # Check hull damage restrictions
        
    def get_cost(self, game_state) -> int:
        # Going deeper: Surf=2, Peri=2, Med=2
        # Going shallower: Peri=1, Med=1, Deep=1
```

### 3.5 Fire Deck Gun Action

```python
class FireDeckGunAction(Action):
    """Fire deck gun at surface target."""
    
    def __init__(self, target_hex: HexCoord, los: LineOfSight):
        self.target_hex = target_hex
        self.los = los
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Must be Surfaced
        # Deck gun not damaged
        # Target in range 1-3
        # LOS to target
        # Target must have ship
        
    def execute(self, game_state) -> bool:
        # Roll 2d6: 7+ at R1-2, 8+ at R3
        # On hit: set DL to 3
        # Roll Allied Ship Damage Chart (Phase 5)
```

### 3.6 Load Torpedoes Action

```python
class LoadTorpedoesAction(Action):
    """Load torpedo tubes."""
    
    def __init__(self, tube_indices: List[int]):
        self.tube_indices = tube_indices
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Must be Surfaced or Periscope
        # Tubes not already loaded
        # Tubes not damaged
        # Count: 2 tubes (1 if Weapons Officer KIA)
        
    def get_cost(self, game_state) -> int:
        # Surf=1, Peri=4
```

### 3.7 Fire Torpedoes Action

```python
class FireTorpedoesAction(Action):
    """Fire 1-3 torpedoes."""
    
    def __init__(
        self,
        tube_indices: List[int],
        target_hex: HexCoord,
        los: LineOfSight
    ):
        self.tube_indices = tube_indices  # 1-3 tubes
        self.target_hex = target_hex
        self.los = los
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Must be Surfaced or Periscope
        # Tubes must be loaded
        # Either front 4 OR rear 1 (not both)
        # Range 1-9 (no limit)
        # Target must have ship
        
    def execute(self, game_state) -> bool:
        # If 3 torps: +1 DL
        # Roll to hit for each torp (range-based table)
        # Any hit: +1 DL
        # Apply damage (Phase 5)
```

### 3.8 Repair Action

```python
class RepairAction(Action):
    """Repair damage or fix torpedo tubes."""
    
    def __init__(self, repair_target: str):
        self.repair_target = repair_target  # 'engine', 'deck_gun', 'tubes', etc.
    
    def can_execute(self, game_state) -> tuple[bool, Optional[str]]:
        # Check depth (Surf=2AP, Submerged=4AP+Engineer)
        # Cannot repair hull damage
        # Flak/Deck gun: Surfaced only
        
    def execute(self, game_state) -> bool:
        # Remove damage marker or fix tubes
```

### 3.9 Action Menu UI

**Extend**: `core/renderer.py`

```python
def render_action_menu(
    self,
    actions: List[Action],
    ap_remaining: int
):
    """Render available actions with costs and hotkeys."""
```

**Layout**:

```text
┌──────────────────────────────┐
│ Available Actions (AP: 5)    │
├──────────────────────────────┤
│ [W] Move Forward      (1 AP) │ ← Green if affordable
│ [Q] Turn Left         (1 AP) │
│ [E] Turn Right        (1 AP) │
│ [Z] Dive Deeper       (2 AP) │
│ [X] Ascend Shallower  (1 AP) │
│ [F] Fire Deck Gun     (2 AP) │ ← Red if invalid
│ [T] Fire Torpedoes    (2 AP) │
│ [L] Load Torpedoes    (1 AP) │
│ [R] Repair            (2 AP) │
└──────────────────────────────┘
```

### 3.10 Action Confirmation

For destructive/important actions (Fire, Repair):
- Show confirmation dialog
- Display expected outcome
- Allow cancel

### Deliverables

- [ ] `Action` base class and 7 implementations
- [ ] All actions integrated with validation subsystems
- [ ] Action menu UI with hotkeys
- [ ] AP deduction on action execution
- [ ] Action history log
- [ ] Confirmation dialogs for fire actions
- [ ] Visual feedback for action results
- [ ] Keyboard shortcuts for all actions

**Testing**: Execute each action type, verify validation, costs, and state changes

---

## Phase 4: AI & Enemy Phases

**Goal**: Implement AI behaviors from JSON rules

### 4.1 AI Architecture

**New Module**: `core/ai_executor.py`

```python
class AIExecutor:
    """Execute AI behaviors from JSON rules."""
    
    def __init__(self, mission_rules: MissionRules):
        self.rules = mission_rules
    
    def execute_merchant_phase(self, game_state) -> List[str]:
        """Execute merchant ship movements, return log."""
        
    def execute_escort_phase(self, game_state) -> List[str]:
        """Execute escort behaviors, return log."""
        
    def execute_b24_phase(self, game_state) -> List[str]:
        """Execute B24 aircraft, return log."""
```

### 4.2 Merchant AI

**Merchant Rules** (from `mission_1_rules.json`):

```python
class MerchantAI:
    """AI for merchant ships."""
    
    def move_merchant(self, ship: Ship, game_state) -> Optional[HexCoord]:
        """
        Move merchant along dotted line path.
        
        Rules:
        - UNDAMAGED: Always move 1 hex
        - DAMAGED: Roll 1d6, move on 4+
        - Face toward exit point
        """
```

**Implementation**:
- Read path from mission config (waypoints)
- Check if damaged
- Execute move or roll
- Update position and facing
- Log movement

### 4.3 Escort AI

**Escort Rules** (from `escort_ai_baseline.json`):

```python
class EscortAI:
    """AI for corvettes and destroyers."""
    
    def execute_escort_turn(
        self,
        ship: Ship,
        u_boat: UBoat,
        detection_level: int,
        anchor_hex: HexCoord,
        game_state
    ) -> Dict[str, Any]:
        """
        Execute escort sequence based on detection level.
        
        DL 0-1: Patrol anchor point
        DL 2-3: Hunt U-boat
        
        Sequence:
        1. MOVE toward target
        2. TURN if blocked
        3. DEPTH_CHARGE if U-boat in range and DL 1-3
        4. FIRE if U-boat surfaced in range
        """
```

**Target Selection**:
- DL 0-1: Move toward anchor hex
- DL 2-3: Move toward U-boat hex

**Actions**:
- **MOVE**: Pathfind toward target, avoid land
- **TURN**: Face toward target
- **DEPTH_CHARGE**: Range 0-1, U-boat not surfaced
- **FIRE**: Range 1-3, U-boat surfaced, LOS

### 4.4 Pathfinding

**New Module**: `core/pathfinding.py`

```python
def find_path(
    start: HexCoord,
    goal: HexCoord,
    valid_hexes: Set[HexCoord],
    blocked_hexes: Set[HexCoord]
) -> List[HexCoord]:
    """A* pathfinding on hex grid."""
```

### 4.5 Detection Phase Logic

**New Module**: `core/detection.py`

```python
class DetectionCalculator:
    """Calculate detection level changes."""
    
    def update_detection_level(
        self,
        current_dl: int,
        u_boat: UBoat,
        ships: List[Ship],
        actions_this_turn: List[str]
    ) -> tuple[int, List[str]]:
        """
        Calculate DL changes.
        
        Increases:
        - Fire deck gun: set to 3
        - Fire 3 torpedoes: +1
        - Hit with torpedo: +1
        - Surfaced near escorts: visibility checks
        
        Decreases:
        - Medium depth at turn start: -1
        - Deep at turn start: -2
        
        Returns:
            (new_dl, log_messages)
        """
```

### 4.6 Phase Execution Flow

**Integration** in `TurnManager`:

```python
def execute_merchant_phase(self, game_state):
    """Auto-execute merchant movements."""
    executor = AIExecutor(self.mission_rules)
    log = executor.execute_merchant_phase(game_state)
    game_state.add_phase_log("Merchant Phase", log)
    
def execute_escort_phase(self, game_state):
    """Auto-execute escort behaviors."""
    executor = AIExecutor(self.mission_rules)
    log = executor.execute_escort_phase(game_state)
    game_state.add_phase_log("Escort Phase", log)
```

### 4.7 Phase Log Display

**Extend**: `core/renderer.py`

```python
def render_phase_log(self, phase_name: str, log_entries: List[str]):
    """
    Display what happened in AI phase.
    
    Example:
    ┌─────────────────────────────┐
    │ Merchant Phase              │
    ├─────────────────────────────┤
    │ • Merchant moved (1,4)→(1,5)│
    │ • Corvette moved (2,3)→(3,3)│
    ├─────────────────────────────┤
    │ [Space] Continue            │
    └─────────────────────────────┘
    """
```

### Deliverables

- [ ] `AIExecutor` class parsing JSON rules
- [ ] `MerchantAI` moving along paths
- [ ] `EscortAI` with DL-based behavior
- [ ] `DetectionCalculator` for DL changes
- [ ] Pathfinding for escort movement
- [ ] Phase log display UI
- [ ] Merchant, Escort, B24 phases auto-execute
- [ ] Visual feedback for AI movement
- [ ] Animation for ship movement (optional)

**Testing**: Watch escorts patrol at DL 0-1, then hunt at DL 2-3

---

## Phase 5: Combat & Damage

**Goal**: Resolve attacks and apply damage charts

### 5.1 Dice Rolling System

**New Module**: `core/dice.py`

```python
class DiceRoller:
    """Handle all dice rolling with logging."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.roll_history: List[Dict[str, Any]] = []
    
    def roll(
        self,
        num_dice: int,
        sides: int = 6,
        operation: str = 'sum'  # 'sum', 'highest', 'lowest'
    ) -> tuple[int, List[int]]:
        """
        Roll dice and return result.
        
        Returns:
            (result, individual_rolls)
        """
        
    def roll_d6(self) -> int:
        """Roll single d6."""
        
    def roll_2d6(self) -> int:
        """Roll 2d6 sum."""
        
    def get_roll_history(self) -> List[Dict[str, Any]]:
        """Get log of all rolls this turn."""
```

### 5.2 Hit Resolution

**New Module**: `core/combat.py`

```python
class CombatResolver:
    """Resolve attack hits and misses."""
    
    def __init__(self, dice: DiceRoller):
        self.dice = dice
    
    def resolve_deck_gun(
        self,
        attacker: UBoat,
        target_hex: HexCoord,
        ships: List[Ship]
    ) -> Dict[str, Any]:
        """
        Resolve deck gun attack.
        
        Returns:
            {
                'hit': bool,
                'roll': int,
                'target_needed': int,
                'ship': Ship or None
            }
        """
        
    def resolve_torpedo(
        self,
        attacker: UBoat,
        target_hex: HexCoord,
        range: int,
        facing_to_target: str,  # 'front', 'side', 'rear'
        ships: List[Ship]
    ) -> Dict[str, Any]:
        """
        Resolve single torpedo hit.
        
        Hit table from u_boat_ruleset_default.json:
        - R1-2: Side 3+, Front/Rear 4+
        - R3-4: Side 4+, Front/Rear 5+
        - R5-6: Side 5+, Front/Rear 6+
        - R7-9: Side 6+, Front/Rear 7+ (impossible)
        """
        
    def resolve_depth_charge(
        self,
        attacker: Ship,
        target: UBoat,
        range: int
    ) -> Dict[str, Any]:
        """
        Resolve depth charge attack.
        
        Corvette: 1d6 on U-Boat Damage Chart
        Destroyer: 2d6 take lowest on chart
        """
        
    def resolve_surface_fire(
        self,
        attacker: Ship,
        target: UBoat,
        range: int
    ) -> Dict[str, Any]:
        """
        Resolve surface gunfire at surfaced U-boat.
        
        Hit table based on ship type and range.
        """
```

### 5.3 Damage Application

**New Module**: `core/damage.py`

```python
class DamageApplicator:
    """Apply damage from charts."""
    
    def __init__(self, dice: DiceRoller, rules: MissionRules):
        self.dice = dice
        self.rules = rules
    
    def apply_u_boat_damage(
        self,
        u_boat: UBoat,
        roll: int
    ) -> Dict[str, Any]:
        """
        Apply damage from U-Boat Damage Chart.
        
        1: Critical Hit (sub-table)
        2-3: Hull Damage
        4-6: General Damage (sub-table)
        
        5-6: Also roll for crew KIA
        
        Returns:
            {
                'damage_type': str,
                'effects': List[str],
                'crew_kia': Optional[str],
                'forced_ascent': bool
            }
        """
        
    def apply_ship_damage(
        self,
        ship: Ship,
        roll: int
    ) -> Dict[str, Any]:
        """
        Apply damage from Allied Ship Damage Chart.
        
        1-2: Sunk
        3-5: Damaged (move on 4+ next turn)
        6: No effect
        """
        
    def _roll_critical_hit(self, u_boat: UBoat) -> Dict[str, Any]:
        """Roll on Critical Hit sub-table."""
        
    def _roll_general_damage(self, u_boat: UBoat) -> Dict[str, Any]:
        """Roll on General Damage sub-table."""
        
    def _check_crew_kia(self, u_boat: UBoat) -> Optional[str]:
        """Roll for crew KIA and medic save."""
```

### 5.4 Damage Charts Integration

Read from `core_system_rules.json`:
- `u_boat_damage_chart`
  - `outcomes`: main table (1, 2-3, 4-6)
  - `sub_tables.critical_hit_table`
  - `sub_tables.general_damage_table`
  - `crew_kia_system`
- `allied_ship_damage_chart`

### 5.5 Forced Ascent Mechanic

```python
def handle_forced_ascent(
    u_boat: UBoat,
    ships: List[Ship],
    validator: DepthValidator
) -> tuple[bool, Optional[str]]:
    """
    Handle forced ascent from hull damage.
    
    Rules:
    - 1 damage: Cannot go DEEP → ascend to MEDIUM
    - 2 damage: Cannot go MEDIUM → ascend to PERISCOPE
    - 3 damage: Cannot submerge → ascend to SURFACED
    - 4 damage: U-Boat destroyed
    
    Returns:
        (success, message)
        success=False if ship blocks ascent (U-boat destroyed)
    """
```

### 5.6 Combat Animation & Feedback

**Extend**: `core/renderer.py`

```python
def render_combat_result(
    self,
    attacker_pos: HexCoord,
    target_pos: HexCoord,
    hit: bool,
    damage: Optional[Dict[str, Any]]
):
    """
    Show combat result animation.
    
    - Draw line from attacker to target
    - Show HIT or MISS
    - Display damage result
    - Animate explosion on hit
    """
    
def render_damage_report(self, damage_info: Dict[str, Any]):
    """
    Show detailed damage report in popup.
    
    Example:
    ┌─────────────────────────────┐
    │ U-Boat Hit!                 │
    ├─────────────────────────────┤
    │ Roll: 4 (General Damage)    │
    │                             │
    │ Sub-roll: 3                 │
    │ → Torpedo Tubes Damaged     │
    │   Tubes 2 and 4 damaged     │
    │                             │
    │ Crew Check: 5               │
    │ → Sonar Operator            │
    │   Medic save: 3 (FAILED)    │
    │ → Sonar Operator KIA        │
    ├─────────────────────────────┤
    │ [Space] Continue            │
    └─────────────────────────────┘
    """
```

### 5.7 Repair System

Integrate repair from Phase 3:

```python
def execute_repair(
    self,
    u_boat: UBoat,
    repair_target: str,
    depth: Depth
) -> tuple[bool, str]:
    """
    Execute repair action.
    
    Costs:
    - Surfaced: 2 AP
    - Submerged: 4 AP (requires Engineer)
    
    Can repair:
    - Engine (any depth with Engineer)
    - Deck Gun (Surfaced only)
    - Flak Gun (Surfaced only)
    - Torpedo Tubes (any depth, fix 2 tubes)
    
    Cannot repair:
    - Hull damage
    """
```

### Deliverables

- [ ] `DiceRoller` with roll logging
- [ ] `CombatResolver` for all attack types
- [ ] `DamageApplicator` reading from JSON charts
- [ ] U-Boat damage chart with sub-tables
- [ ] Allied ship damage chart
- [ ] Crew KIA system with medic saves
- [ ] Forced ascent from hull damage
- [ ] Combat animation/visual feedback
- [ ] Damage report UI
- [ ] Repair system functional
- [ ] Unit tests for damage tables

**Testing**: Test all damage outcomes, verify chart probabilities, check forced ascent

---

## Phase 6: Victory Conditions & Polish

**Goal**: Complete the game loop with win/loss and refinements

### 6.1 Victory Condition System

**New Module**: `core/victory.py`

```python
class VictoryChecker:
    """Check mission objectives and end conditions."""
    
    def __init__(self, mission_rules: MissionRules):
        self.rules = mission_rules
        self.objectives = self._parse_objectives()
    
    def check_victory(self, game_state) -> Optional[str]:
        """
        Check if player won.
        
        Returns victory reason or None.
        """
        
    def check_defeat(self, game_state) -> Optional[str]:
        """
        Check if player lost.
        
        Returns defeat reason or None.
        """
        
    def get_objectives_status(self, game_state) -> List[Dict[str, Any]]:
        """
        Get current objective completion status.
        
        Returns:
            [
                {
                    'description': str,
                    'completed': bool,
                    'progress': Optional[str]
                },
                ...
            ]
        """
```

**Common Objectives**:
- Sink specific ships
- Exit map at specific hex
- Survive N turns
- Reach specific hex
- Avoid detection above threshold

**Defeat Conditions**:
- U-Boat hull damage = 4 (destroyed)
- Mission-specific failures (merchant escapes, etc.)

### 6.2 Game Over Screen

**New Module**: `core/screens/game_over.py`

```python
class GameOverScreen:
    """Display victory or defeat screen."""
    
    def __init__(self, result: str, reason: str, stats: Dict[str, Any]):
        self.result = result  # 'VICTORY' or 'DEFEAT'
        self.reason = reason
        self.stats = stats
    
    def render(self, screen: pygame.Surface):
        """
        Render game over screen.
        
        Show:
        - Result (VICTORY/DEFEAT)
        - Reason
        - Mission stats (turns, ships sunk, damage taken)
        - Options: Retry, Menu, Quit
        """
```

### 6.3 Mission Statistics

Track during gameplay:
- Turns elapsed
- Ships sunk (by type)
- Torpedoes fired
- Torpedoes hit
- Hull damage taken
- Crew lost
- Detection level max
- Actions taken count

### 6.4 Turn Limit (Optional)

Some missions have turn limits:
- Track in `TurnManager`
- Show turn counter: "Turn 3/12"
- Defeat if exceeded

### 6.5 Polish & Refinements

**UI Polish**:
- [ ] Better typography and layout
- [ ] Color coding (green=valid, red=invalid, yellow=warning)
- [ ] Icons for actions
- [ ] Tooltips on hover
- [ ] Smooth scrolling for logs
- [ ] Better phase transition animations

**Gameplay Polish**:
- [ ] Action preview (show outcome before committing)
- [ ] Undo last action (where applicable)
- [ ] Quick action shortcuts (hotkeys)
- [ ] Tutorial/help overlay (F1)
- [ ] Mission briefing screen before start
- [ ] Save/load game state

**Audio** (Optional):
- [ ] Submarine ambient sounds
- [ ] Torpedo launch sound
- [ ] Explosion sounds
- [ ] Sonar ping
- [ ] Background music

### 6.6 Mission Briefing Screen

**New Module**: `core/screens/briefing.py`

```python
class BriefingScreen:
    """Display mission briefing before gameplay."""
    
    def render(self, screen: pygame.Surface):
        """
        Show:
        - Mission number and name
        - Objective description
        - Map preview
        - Enemy composition
        - Estimated turns
        - Difficulty
        - [Space] Start Mission
        """
```

### 6.7 Pause Menu

**Integration** in `game_state.py`:

```python
def handle_pause(self):
    """Show pause menu overlay."""
    # Resume
    # Save Game
    # Load Game
    # Options
    # Quit to Menu
```

### Deliverables

- [ ] `VictoryChecker` evaluating objectives
- [ ] Game Over screen (victory/defeat)
- [ ] Mission statistics tracking
- [ ] Turn limit enforcement (if applicable)
- [ ] Mission briefing screen
- [ ] Pause menu
- [ ] UI polish (colors, icons, layout)
- [ ] Action tooltips
- [ ] Help overlay (F1)
- [ ] Save/load game state (basic)

**Testing**: Complete Mission 1 by achieving objectives, verify defeat on U-boat destruction

---

## Technical Architecture

### Module Structure

```text
core/
├── models.py              # Data classes (existing)
├── hex_grid.py            # Hex math (existing, extended)
├── assets.py              # Asset loading (existing)
├── renderer.py            # Rendering (existing, extended)
├── game_state.py          # Main game class (existing, extended)
├── turn_manager.py        # NEW: Turn/phase management
├── los.py                 # NEW: Line of sight
├── movement.py            # NEW: Movement validation
├── depth.py               # NEW: Depth validation
├── action_costs.py        # NEW: AP cost calculator
├── actions.py             # NEW: Action implementations
├── ai_executor.py         # NEW: AI from JSON rules
├── pathfinding.py         # NEW: A* pathfinding
├── detection.py           # NEW: Detection level logic
├── dice.py                # NEW: Dice rolling
├── combat.py              # NEW: Hit resolution
├── damage.py              # NEW: Damage application
├── victory.py             # NEW: Victory/defeat checking
└── screens/
    ├── briefing.py        # NEW: Mission briefing
    └── game_over.py       # NEW: End game screen
```

### Data Flow

```text
User Input → Action Selection → Validation → Execution → State Update → Rendering
                                    ↓
                           AP Deduction, Logging
```

**Phase Flow**:

```text
Turn Start
    ↓
[1] U-Boat Phase ← Player actions until AP spent or advance
    ↓
[2] Merchant Phase ← Auto-execute, log, pause for player
    ↓
[3] Detection Phase ← Calculate DL changes
    ↓
[4] Escort Phase ← Auto-execute escort AI
    ↓
[5] B24 Phase ← Auto-execute if aircraft present
    ↓
[6] End Turn Phase ← Check victory/defeat, roll new AP
    ↓
Next Turn
```

### JSON Rules Integration

All gameplay logic reads from JSON:
- Action costs: `u_boat_ruleset_default.json` → `u_boat_action_costs`
- AP rules: `u_boat_ruleset_default.json` → `u_boat_ap_rules`
- Damage tables: `core_system_rules.json` → `u_boat_damage_chart`, `allied_ship_damage`
- AI behaviors: `escort_ai_baseline.json`, `mission_X_rules.json`

### State Management

All game state in `Game` class:
- `u_boat: UBoat`
- `ships: List[Ship]`
- `turn_manager: TurnManager`
- `detection_level: int`
- `mission_config: module`
- `mission_rules: MissionRules`

### Testing Strategy

**Unit Tests**:
- Hex distance calculation
- LOS calculation (all edge cases)
- Movement validation
- Depth validation
- Action cost lookup
- Damage table rolling

**Integration Tests**:
- Complete turn cycle
- AP spending and depletion
- AI phase execution
- Combat resolution end-to-end

**Playtesting**:
- Complete Mission 1 from start to finish
- Test all victory/defeat paths
- Verify AI behaviors at different DL

---

## Development Workflow

### For Each Phase

1. **Plan**: Review phase deliverables
2. **Stub**: Create module structure with docstrings
3. **Implement**: Write code incrementally
4. **Test**: Unit tests for new systems
5. **Integrate**: Connect to `Game` class
6. **Playtest**: Verify in actual gameplay
7. **Refine**: Fix bugs, improve UX

### Git Workflow

Suggested branches:
- `main` - stable releases
- `develop` - integration branch
- `feature/phase-1-turn-system`
- `feature/phase-2-subsystems`
- etc.

### Documentation

Keep updated:
- `README.md` - Development status
- `RULES.md` - Game rules reference
- `GAMEPLAY_DEVELOPMENT_PLAN.md` - This document
- Code docstrings
- JSON schema validation

---

## Risk Mitigation

### Potential Challenges

1. **JSON Rule Complexity**
   - Risk: Hard to parse complex AI sequences
   - Mitigation: Start simple, iterate on structure

2. **Combat Math Balance**
   - Risk: Hit rates too high/low
   - Mitigation: Playtesting, adjustable difficulty

3. **AI Pathfinding Performance**
   - Risk: Slow with many ships
   - Mitigation: Cache paths, limit search depth

4. **UI Clutter**
   - Risk: Too much info on screen
   - Mitigation: Progressive disclosure, toggles

### Dependencies

- **Phase 3** requires **Phase 2** (validation before actions)
- **Phase 4** requires **Phase 1** (AI needs turn structure)
- **Phase 5** requires **Phase 3** (damage needs actions)
- **Phase 6** requires all previous (victory needs complete game)

---

## Success Metrics

**Phase 1**: Can play through multiple turns with AP tracking  
**Phase 2**: Movement/actions validate correctly  
**Phase 3**: All 7 actions work with proper costs  
**Phase 4**: Merchants and escorts move intelligently  
**Phase 5**: Combat resolves with proper damage  
**Phase 6**: Can win/lose Mission 1 following rules  

**Final Success**: Mission 1 is fully playable from briefing to victory/defeat following all original board game rules.

---

## Next Steps

After completing Phase 6:
1. **Mission 2-10**: Extend to remaining missions
2. **Advanced Features**: Save/load, settings, sound
3. **Balance Pass**: Adjust difficulties based on playtesting
4. **Polish Pass**: Visual effects, animations, juice
5. **Performance**: Optimize rendering and AI
6. **Documentation**: Player manual, strategy guide

---

**End of Plan**

This plan provides a clear roadmap from current prototype to fully playable game. Each phase builds incrementally, maintaining a working game at every step.

Ready to start Phase 1? 🚢💥
