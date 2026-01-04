# Phase 2: Action Subsystems (REFINED)

**Goal**: Build validation and utility systems that read from JSON rules to support Phase 3 actions

**Status**: ✅ Phase 1 Complete | 🚧 Phase 2 In Progress

---

## What We Already Have (Phase 1)

✅ **Detection Level Modification** - `turn_manager.apply_depth_detection_modifier()`  
✅ **Action Point Rolling** - `turn_manager._roll_action_points()` with engine/captain logic  
✅ **Turn System** - Full 6-phase cycle with AP tracking

---

## Phase 2 Subsystems (Gameplay Order)

### 2.1 General Dice Roller (Priority: HIGH)

**New Module**: `core/dice.py`

```python
class DiceRoller:
    """General-purpose dice rolling with logging."""
    
    def roll_dice(self, count: int, sides: int = 6) -> List[int]
    def roll_2d6(self) -> int  # For deck gun, torpedoes
    def roll_1d6(self) -> int  # For damage charts
    def roll_highest(self, count: int) -> tuple[int, List[int]]  # Already used for AP
```

**Usage**: Reused for AP rolls, combat, damage charts  
**No JSON needed** - pure utility class

---

### 2.2 Range & LOS Calculator (Priority: HIGH)

**Extends**: `core/hex_grid.py`  
**New Module**: `core/los.py`

```python
# In hex_grid.py
class HexGrid:
    @staticmethod
    def hex_distance(a: HexCoord, b: HexCoord) -> int:
        """Axial distance for range checks."""
    
    def hexes_in_range(center: HexCoord, range: int) -> Set[HexCoord]:
        """Get all hexes within range."""

# In los.py
class LOSCalculator:
    def has_line_of_sight(
        from_hex: HexCoord,
        to_hex: HexCoord,
        land_hexes: Set[HexCoord]
    ) -> tuple[bool, Optional[str]]:
        """
        Check LOS for deck gun and torpedoes.
        Rules: Land blocks, ships don't block.
        """
```

**JSON Source**: `u_boat_ruleset_default.json` → `FIRE DECK GUN` & `FIRE TORPS` requirements  
**Usage**: Deck gun (range 1-3), Torpedoes (range 1-9)

---

### 2.3 Action Cost Lookup (Priority: HIGH)

**New Module**: `core/action_costs.py`

```python
class ActionCostLookup:
    """Read action costs from JSON rules."""
    
    def __init__(self, mission_rules: MissionRules):
        self.costs = self._parse_costs()
    
    def get_cost(self, action: str, depth: Depth) -> Optional[int]:
        """
        Get AP cost for action at current depth.
        Returns None if action unavailable at depth.
        """
    
    def _parse_costs(self) -> Dict[str, Dict[Depth, int]]:
        """Parse u_boat_action_costs from JSON."""
```

**JSON Source**: `u_boat_ruleset_default.json` → `u_boat_action_costs`  
**Actions**: MOVE, TURN, CHANGE DEPTH, REPAIR, FIRE DECK GUN, LOAD TORPS, FIRE TORPS

**Example**:

```json
"MOVE": {
  "SURFACED": 1,
  "PERISCOPE": 2,
  "MEDIUM": 3,
  "DEEP": 3
}
```

---

### 2.4 Movement Validator (Priority: HIGH)

**New Module**: `core/movement_validator.py`

```python
class MovementValidator:
    """Validate U-Boat movement based on terrain and state."""
    
    def can_move_to(
        self,
        u_boat: UBoat,
        target_hex: HexCoord,
        ships: List[Ship]
    ) -> tuple[bool, str]:
        """
        Validate movement to target hex.
        
        Checks from JSON restrictions:
        - Cannot enter Land hexes
        - Cannot enter Shallow unless Surfaced or Periscope
        - Cannot enter Ship hex unless Medium or Deep
        """
```

**JSON Source**: `u_boat_ruleset_default.json` → `MOVE` restrictions  
**Data Needed**: `land_hexes`, `shallow_hexes` from mission config

---

### 2.5 Depth Change Validator (Priority: HIGH)

**New Module**: `core/depth_validator.py`

```python
class DepthValidator:
    """Validate depth change based on terrain and damage."""
    
    def can_change_depth(
        self,
        u_boat: UBoat,
        new_depth: Depth,
        current_hex: HexCoord,
        shallow_hexes: Set[HexCoord],
        ships: List[Ship],
        depth_changed_this_turn: bool
    ) -> tuple[bool, str]:
        """
        Validate depth change.
        
        Checks from JSON restrictions:
        - Can only change depth once per turn
        - Can only change by one level at a time
        - Cannot go below Periscope in shallow water
        - Cannot go above Medium beneath ships
        - Hull damage limits max depth (3 dmg = Surfaced only, 2 = Periscope, 1 = Medium)
        """
    
    @staticmethod
    def max_depth_for_hull_damage(hull_damage: int) -> Depth:
        """Calculate max allowed depth based on hull damage."""
```

**JSON Source**: `u_boat_ruleset_default.json` → `CHANGE DEPTH` restrictions  
**JSON Source**: `core_system_rules.json` → hull damage depth limits (implicit in forced ascent)

---

### 2.6 Repair Validator (Priority: MEDIUM)

**New Module**: `core/repair_validator.py`

```python
class RepairValidator:
    """Validate repair actions and requirements."""
    
    def can_repair(
        self,
        u_boat: UBoat,
        repair_target: str,
        depth: Depth
    ) -> tuple[bool, str]:
        """
        Validate repair action.
        
        Checks from JSON:
        - Hull damage cannot be repaired
        - Flak/Deck Gun: Surfaced only
        - Engine/Torpedo Tubes: any depth (2 AP surface, 4 AP submerged + Engineer)
        - If Engineer KIA: only surface repairs
        """
    
    def get_repairable_items(self, u_boat: UBoat, depth: Depth) -> List[str]:
        """List what can be repaired in current state."""
```

**JSON Source**: `u_boat_ruleset_default.json` → `REPAIR` requirements & restrictions

---

### 2.7 Combat Hit Calculator (Priority: MEDIUM)

**New Module**: `core/combat_resolver.py`

```python
class CombatResolver:
    """Resolve combat hit/miss using JSON tables."""
    
    def __init__(self, dice: DiceRoller, mission_rules: MissionRules):
        self.dice = dice
        self.hit_tables = self._parse_hit_tables()
    
    def resolve_deck_gun_shot(
        self,
        range: int
    ) -> tuple[bool, int, int]:
        """
        Roll to hit with deck gun.
        Returns: (hit, roll, target_needed)
        
        From JSON:
        - Range 1-2: 7+ on 2d6
        - Range 3: 8+ on 2d6
        """
    
    def resolve_torpedo_shot(
        self,
        range: int,
        aspect: str  # 'side', 'front', 'rear'
    ) -> tuple[bool, int, int]:
        """
        Roll to hit with single torpedo.
        Returns: (hit, roll, target_needed)
        
        From JSON:
        - Range 1-2: Side 3+, Front/Rear 4+ on 1d6
        - Range 3-4: Side 4+, Front/Rear 5+ on 1d6
        - Range 5-6: Side 5+, Front/Rear 6+ on 1d6
        - Range 7-9: Side 6+, Front/Rear 7+ (impossible)
        """
```

**JSON Source**: `u_boat_ruleset_default.json` → `FIRE DECK GUN` & `FIRE TORPS` to_hit tables

---

### 2.8 Torpedo Loading Validator (Priority: LOW)

**New Module**: `core/torpedo_validator.py`

```python
class TorpedoValidator:
    """Validate torpedo loading/firing."""
    
    def can_load_tubes(
        self,
        u_boat: UBoat,
        tube_indices: List[int],
        depth: Depth
    ) -> tuple[bool, str]:
        """
        Validate tube loading.
        
        From JSON:
        - Cannot load damaged tubes
        - Load 2 tubes (1 if Weapons Officer KIA)
        - Can only load at Surfaced (1 AP) or Periscope (4 AP)
        """
    
    def can_fire_tubes(
        self,
        u_boat: UBoat,
        tube_indices: List[int],
        depth: Depth
    ) -> tuple[bool, str]:
        """
        Validate tube firing.
        
        From JSON:
        - Front 4 tubes OR rear 1 tube (not both)
        - Tubes must be loaded
        - Can fire 1, 2, or 3 torpedoes
        - Can only fire at Surfaced or Periscope
        """
```

**JSON Source**: `u_boat_ruleset_default.json` → `LOAD TORPS` & `FIRE TORPS` restrictions

---

## Implementation Order

### Week 1: Core Utilities

1. **DiceRoller** (2.1) - 2 hours
   - Refactor turn_manager to use it
   - Add roll logging

2. **ActionCostLookup** (2.3) - 3 hours
   - Parse u_boat_action_costs from JSON
   - Test all 7 actions at all 4 depths

3. **Range & LOS** (2.2) - 4 hours
   - hex_distance() in HexGrid
   - LOSCalculator with land blocking
   - Unit tests for edge cases

### Week 2: Validators

1. **MovementValidator** (2.4) - 3 hours
   - Terrain checks
   - Ship collision logic
   - Visual feedback (green hexes)

2. **DepthValidator** (2.5) - 3 hours
   - Once-per-turn tracking
   - Hull damage limits
   - Shallow water restrictions

3. **RepairValidator** (2.6) - 2 hours
   - Parse repair requirements
   - Surface vs submerged logic

4. **CombatResolver** (2.7) - 4 hours
   - Deck gun hit tables
   - Torpedo hit tables
   - Aspect calculation

5. **TorpedoValidator** (2.8) - 2 hours
   - Load validation
   - Fire direction validation

---

## Testing Strategy

### Unit Tests

- [ ] DiceRoller: Distribution tests, deterministic seeding
- [ ] hex_distance: All axial coordinate cases
- [ ] LOS: Land blocking at ranges 1-3, edge cases
- [ ] MovementValidator: Each terrain type, ship collisions
- [ ] DepthValidator: All depth transitions, hull damage limits
- [ ] CombatResolver: Hit probability at each range

### Integration Tests

- [ ] Turn manager uses DiceRoller
- [ ] Action costs match JSON for all actions
- [ ] Movement highlights valid hexes correctly

---

## Deliverables

✅ = Complete | 🚧 = In Progress | ⬜ = Not Started

- ⬜ `core/dice.py` - General dice roller
- ⬜ `core/action_costs.py` - AP cost lookup from JSON
- ⬜ `core/hex_grid.py` - Extended with hex_distance()
- ⬜ `core/los.py` - Line of sight calculator
- ⬜ `core/movement_validator.py` - Movement validation
- ⬜ `core/depth_validator.py` - Depth change validation
- ⬜ `core/repair_validator.py` - Repair validation
- ⬜ `core/combat_resolver.py` - Hit resolution
- ⬜ `core/torpedo_validator.py` - Torpedo load/fire validation
- ⬜ Unit tests for all subsystems
- ⬜ Visual feedback for valid actions (green highlights)

---

## Dependencies

**Phase 1 → Phase 2**:
- TurnManager provides depth_changed_this_turn flag
- TurnManager will use DiceRoller after refactor

**Phase 2 → Phase 3**:
- All actions in Phase 3 depend on these validators
- CombatResolver needed before weapon actions work

---

## Notes

- **JSON-Driven**: Every rule comes from JSON, no hardcoding
- **Reusable**: Validators used by both player and AI
- **Testable**: Pure functions with clear inputs/outputs
- **Extensible**: Easy to add new actions in Phase 3

**Estimated Effort**: 23 hours total (~3 days)

---

Ready to start? I suggest beginning with **DiceRoller** → **ActionCostLookup** → **Range/LOS** as they're needed by everything else.
