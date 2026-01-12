# Phase 3: Action Implementation

**Goal**: Integrate Phase 2 validators into actual gameplay actions with UI

**Status**: ✅ COMPLETE | **Completed**: January 2026

---

## Phase 3 Completion Summary

All 7 core actions implemented with comprehensive test coverage:

### Implemented Actions
1. **MoveAction** - Movement with validation (land, shallow water, ships)
2. **RotateAction** - U-boat rotation (clockwise/counter-clockwise)
3. **DepthChangeAction** - Depth changes with restrictions
4. **RepairAction** - System repairs (engine, guns, torpedoes)
5. **DeckGunAction** - Surface combat with range/LOS
6. **LoadTorpedoAction** - Loading torpedo tubes (1-2 tubes, depth restricted)
7. **FireTorpedoAction** - Firing torpedoes with interactive resolution

### Test Coverage
- **test_action_system.py** - Action queue, AP management, undo/redo
- **test_movement_actions.py** - Move, rotate, depth change (10 tests)
- **test_combat_actions.py** - Repair, deck gun, torpedo basics (9 tests)
- **test_deck_gun_scenario.py** - Interactive deck gun combat
- **test_torpedo_scenario.py** - Complete torpedo workflow (29 tests)
- **test_damage_resolution.py** - Ship/U-boat damage, crew casualties

### Key Features Delivered
- Interactive resolution screens for combat
- Visual feedback for all actions
- Comprehensive validation using Phase 2 validators
- Action cost calculation based on depth
- Detection level tracking and updates
- Damage resolution with charts
- Continue-on-miss mechanics for torpedoes
- Aspect-based hit tables

---

## Prerequisites (Complete ✅)

- ✅ Phase 1: Turn system with 6-phase cycle
- ✅ Phase 2: All 8 validators (DiceRoller, Range/LOS, ActionCostLookup, Movement, Depth, Repair, Combat, Torpedo)
- ✅ JSON rule system with u_boat_ruleset_default.json
- ✅ Comprehensive test coverage for all validators

---

## Phase 3 Implementation Plan

### 3.1 Action System Architecture (Foundation) ✅ COMPLETE

**Priority**: CRITICAL | **Time**: 6-8 hours

Create the core action framework that all gameplay actions will use.

**New Modules**:
- `core/actions/base_action.py` - Abstract base action class
- `core/actions/action_queue.py` - Action planning and execution
- `core/actions/action_executor.py` - Executes actions with validation

**Key Classes**:

```python
class Action(ABC):
    """Base class for all player actions."""
    
    @abstractmethod
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost for this action."""
    
    @abstractmethod
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        """Validate action can be performed."""
    
    @abstractmethod
    def execute(self, game_state: GameState) -> ActionResult:
        """Execute the action and return result."""
    
    @abstractmethod
    def get_preview_data(self, game_state: GameState) -> dict:
        """Get data for visual preview (highlights, etc.)."""

class ActionQueue:
    """Manage planned actions before committing."""
    
    def add_action(self, action: Action) -> bool:
        """Add action to queue if valid."""
    
    def remove_last(self) -> Optional[Action]:
        """Undo last action."""
    
    def get_total_cost(self) -> int:
        """Calculate total AP cost of queued actions."""
    
    def can_afford(self, available_ap: int) -> bool:
        """Check if queue is affordable."""
    
    def commit_all(self, game_state: GameState) -> List[ActionResult]:
        """Execute all queued actions."""

class ActionExecutor:
    """Executes actions with proper validation pipeline."""
    
    def __init__(self, validators: ValidatorCollection):
        self.validators = validators
    
    def execute_action(
        self, 
        action: Action, 
        game_state: GameState
    ) -> ActionResult:
        """Execute single action through validation pipeline."""
```

**UI Components**:
- Action queue display (shows planned actions)
- AP counter with cost preview
- Undo button
- Commit Turn button
- Action history log

**Deliverables**:
- [ ] Base action classes
- [ ] Action queue system
- [ ] Action executor with validation
- [ ] UI for action planning
- [ ] Unit tests for action system

---

### 3.2 Movement Actions (Quick Win) ✅ COMPLETE

**Priority**: HIGH | **Time**: 4-6 hours

Refactor existing WASD controls into proper action system.

**New Modules**:
- `core/actions/move_action.py`
- `core/actions/rotate_action.py`
- `core/actions/depth_action.py`

**Actions to Implement**:

```python
class MoveAction(Action):
    """Move U-boat to adjacent hex."""
    
    def __init__(self, target_hex: HexCoord):
        self.target_hex = target_hex
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Use MovementValidator
        # Check terrain (land, shallow, ships)
        # Check if adjacent
    
    def execute(self, game_state: GameState) -> ActionResult:
        # Update U-boat position
        # Deduct AP cost
        # Trigger any movement events

class RotateAction(Action):
    """Rotate U-boat 60 degrees."""
    
    def __init__(self, direction: str):  # 'left' or 'right'
        self.direction = direction

class DepthChangeAction(Action):
    """Change U-boat depth by one level."""
    
    def __init__(self, new_depth: Depth):
        self.new_depth = new_depth
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Use DepthValidator
        # Check once-per-turn
        # Check hull damage limits
        # Check shallow water
        # Check ships overhead
```

**Features**:
- Visual feedback (green highlight for valid moves)
- Show AP cost per action
- Enforce depth change once per turn
- Handle forced dive/ascent

**Deliverables**:
- ✅ MoveAction with MovementValidator integration
- ✅ RotateAction implementation
- ✅ DepthChangeAction with DepthValidator integration
- ✅ Visual hex highlighting for valid moves
- ✅ Tests for movement actions (test_movement_actions.py)
- ⚠️ Refactor WASD to use action system (deferred - direct controls preferred)

---

### 3.3 Repair Actions ✅ COMPLETE

**Priority**: MEDIUM | **Time**: 4-5 hours

Add repair action with selection UI.

**New Modules**:
- `core/actions/repair_action.py`
- UI for selecting repair targets

**Actions to Implement**:

```python
class RepairAction(Action):
    """Repair damaged U-boat systems."""
    
    def __init__(self, repair_targets: List[str]):
        self.repair_targets = repair_targets  # e.g., ['engine', 'tube_2']
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Use RepairValidator
        # Check surface requirement for deck/flak
        # Check engineer status
        # Check tube repair limit (2 per action)
    
    def execute(self, game_state: GameState) -> ActionResult:
        # Clear damage flags
        # Show repair notification
```

**UI Components**:
- Repair selection popup
- Show what can be repaired
- Display AP costs
- Engineer status indicator
- Disabled options when not at surface

**Deliverables**:
- ✅ RepairAction with RepairValidator integration
- ✅ Repair selection UI (buttons in game screen)
- ✅ Visual feedback for repaired systems
- ✅ Tests for repair actions (test_combat_actions.py)

---

### 3.4 Combat Actions - Deck Gun ✅ COMPLETE

**Priority**: HIGH | **Time**: 5-6 hours

Implement deck gun targeting and firing.

**New Modules**:
- `core/actions/deck_gun_action.py`
- Target selection UI

**Actions to Implement**:

```python
class DeckGunAction(Action):
    """Fire deck gun at target ship."""
    
    def __init__(self, target_ship: Ship):
        self.target_ship = target_ship
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Must be Surfaced
        # Deck gun not damaged
        # Use RangeLOS to check range (1-3) and line of sight
        # Target in valid hex
    
    def execute(self, game_state: GameState) -> ActionResult:
        # Use CombatResolver.resolve_deck_gun_attack()
        # If hit: set detection level to 3
        # If hit: trigger ship damage resolution
        # Show combat log message
```

**Features**:
- Click ship to target
- Range/LOS indicator
- Hit/miss resolution
- Combat log display
- Detection level update
- Link to damage resolution

**Deliverables**:
- ✅ DeckGunAction with Range/LOS/Combat integration
- ✅ Target selection UI (interactive resolution screen)
- ✅ Range indicator overlay
- ✅ Combat result notifications
- ✅ Tests for deck gun actions (test_combat_actions.py, test_deck_gun_scenario.py)

---

### 3.5 Combat Actions - Torpedoes ✅ COMPLETE

**Priority**: HIGH | **Time**: 6-8 hours

Implement torpedo loading and firing.

**New Modules**:
- `core/actions/load_torpedo_action.py`
- `core/actions/fire_torpedo_action.py`
- Torpedo tube status UI

**Actions to Implement**:

```python
class LoadTorpedoAction(Action):
    """Load torpedo tubes."""
    
    def __init__(self, tube_numbers: List[int]):
        self.tube_numbers = tube_numbers  # 1-5 (user-facing)
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Use TorpedoValidator.can_load_tubes()
        # Check depth (Surfaced or Periscope)
        # Check WO status (2 tubes vs 1)
        # Check tubes not damaged
    
    def execute(self, game_state: GameState) -> ActionResult:
        # Mark tubes as loaded
        # Show loading notification

class FireTorpedoAction(Action):
    """Fire torpedoes at target."""
    
    def __init__(
        self, 
        tube_numbers: List[int],
        target_ship: Ship,
        aspect: str  # 'side', 'front_rear'
    ):
        self.tube_numbers = tube_numbers
        self.target_ship = target_ship
        self.aspect = aspect
    
    def validate(self, game_state: GameState) -> tuple[bool, str]:
        # Use TorpedoValidator.can_fire_tubes()
        # Check depth (Surfaced or Periscope)
        # Check front OR rear (not both)
        # Check 1-3 torpedoes
        # Check range (1-9)
        # Check tubes loaded
    
    def execute(self, game_state: GameState) -> ActionResult:
        # For each torpedo:
        #   Use CombatResolver.resolve_torpedo_attack()
        #   If miss: continue to next ship in line
        # Update detection level (+1 if 3 fired, +1 per hit)
        # Unload fired tubes
        # Trigger damage for hits
```

**UI Components**:
- Torpedo tube status display (5 tubes: ●○●○●)
- Tube selection UI (front 1-4 OR rear 5)
- Aspect calculation from geometry
- Multi-torpedo salvo selection
- Torpedo path visualization

**Deliverables**:
- ✅ LoadTorpedoAction with TorpedoValidator integration
- ✅ FireTorpedoAction with TorpedoValidator integration
- ✅ Torpedo tube status UI (5 torpedo boxes on game board)
- ✅ Tube selection interface (interactive buttons)
- ✅ Aspect auto-detection from positioning
- ✅ Miss continuation logic
- ✅ Detection level updates (max +2 per salvo)
- ✅ Tests for torpedo actions (test_torpedo_scenario.py - 29 comprehensive tests)

---

### 3.6 Damage Resolution System ✅ COMPLETE

**Priority**: HIGH | **Time**: 8-10 hours

Implement damage charts and effects.

**New Modules**:
- `core/damage/ship_damage.py`
- `core/damage/uboat_damage.py`
- Damage notification UI

**Damage Systems**:

```python
class ShipDamageResolver:
    """Resolve Allied ship damage."""
    
    def __init__(self, dice: DiceRoller):
        self.dice = dice
    
    def apply_damage(
        self, 
        ship: Ship, 
        weapon_type: str  # 'deck_gun' or 'torpedo'
    ) -> DamageResult:
        # Roll on Allied Ship Damage Chart
        # Merchant: Simple 1d6
        # Escort: Modified rolls
        # Apply damage (Damaged or Catastrophic)
        # Damaged + hit again = Sunk
        # Catastrophic = immediate Sunk
        # Remove sunken ships from map

class UBoatDamageResolver:
    """Resolve U-boat damage."""
    
    def __init__(self, dice: DiceRoller):
        self.dice = dice
    
    def apply_damage(
        self, 
        u_boat: UBoat,
        damage_type: str  # 'critical', 'general'
    ) -> DamageResult:
        # Roll on U-Boat Damage Chart
        # Critical Hit: Roll on critical sub-table
        # Hull Damage: Cannot repair, max 4, affects depth
        # General Damage: Roll on general sub-table
        # Crew KIA: Select random crew, medic save (5+)
        # System damage: tubes, engine, guns
        # Check U-boat destruction (hull 4+ or critical)
```

**Features**:
- Damage chart implementation from JSON
- Ship state tracking (Undamaged → Damaged → Sunk)
- Crew casualty system
- Medic save rolls (5+ on 1d6)
- Hull damage depth restrictions
- U-boat destruction conditions
- Damage animations/notifications
- Victory/defeat condition checking

**Deliverables**:
- ✅ ShipDamageResolver with damage charts
- ✅ UBoatDamageResolver with damage charts
- ✅ Crew casualty and medic save system
- ✅ Hull damage depth enforcement
- ✅ Ship removal on sinking
- ✅ Damage notification UI (interactive resolution screens)
- ⚠️ Victory/defeat condition checks (deferred to Phase 4)
- ✅ Tests for damage resolution (test_damage_resolution.py, test_combat_actions.py)

---

## Implementation Schedule

### Week 1: Foundation & Movement

- **Days 1-2**: Action System Architecture (3.1)
  - Base classes, queue, executor
  - UI components for action planning
  
- **Days 3-4**: Movement Actions (3.2)
  - Refactor WASD into actions
  - Visual feedback and validation
  
- **Day 5**: Repair Actions (3.3)
  - Repair selection UI
  - Integration with RepairValidator

### Week 2: Combat

- **Days 1-2**: Deck Gun (3.4)
  - Target selection
  - Hit resolution
  - Combat notifications
  
- **Days 3-5**: Torpedoes (3.5)
  - Loading system
  - Firing with tube selection
  - Multi-torpedo salvos
  - Miss continuation

### Week 3: Damage & Polish

- **Days 1-3**: Damage Resolution (3.6)
  - Ship damage charts
  - U-boat damage charts
  - Crew casualties
  
- **Days 4-5**: Integration & Testing
  - End-to-end combat flow
  - Victory/defeat conditions
  - Bug fixes and polish

---

## Testing Strategy

### Unit Tests

- ✅ Action validation logic (test_action_system.py)
- ✅ Action queue operations (test_action_system.py)
- ✅ Damage calculations (test_damage_resolution.py)
- ✅ Crew casualty rolls (test_damage_resolution.py)
- ✅ Medic saves (test_damage_resolution.py)

### Integration Tests

- ✅ Full combat sequences (test_deck_gun_scenario.py, test_torpedo_scenario.py)
- ✅ Movement → Detection → Combat flow (test_movement_actions.py, test_combat_actions.py)
- ✅ Repair → System recovery (test_combat_actions.py)
- ✅ Multiple actions in one turn (action queue system)

### Gameplay Tests

- ✅ AP management works correctly (test_action_system.py)
- ✅ Can't exceed AP limit (action queue validation)
- ✅ Undo works properly (action queue undo)
- ✅ Turn commit works (action execution)
- ✅ All validators integrate correctly (all test files)

---

## Success Criteria

Phase 3 is complete when:
- ✅ Player can plan and execute all 7 core actions
- ✅ All Phase 2 validators properly integrated
- ✅ Combat resolves hits/misses correctly
- ✅ Damage charts work and affect game state
- ✅ Ships sink and are removed from map
- ✅ U-boat damage affects capabilities
- ✅ AP system prevents overspending
- ✅ All actions have proper visual feedback
- ✅ Comprehensive test coverage

---

## Next Phase Preview

**Phase 4**: Enemy AI & Automation
- Merchant ship movement AI
- Escort ship combat AI
- Patrol boat behavior
- Event phase automation
