# Test Suite for Lone U-Boat

This directory contains all unit tests for the Lone U-Boat game subsystems.

## Running Tests

Run individual test files from the project root:

```bash
python tests/test_combat_resolver.py
python tests/test_torpedo_validator.py
python tests/test_repair_validator.py
python tests/test_depth_validator.py
python tests/test_movement_validator.py
python tests/test_range_los.py
python tests/test_phase2_subsystems.py
```

Or run all tests:

```bash
python -m pytest tests/
```

## Test Coverage

### Phase 2 Subsystems (100% Complete)

- **test_phase2_subsystems.py** - DiceRoller, ActionCostLookup integration tests
- **test_range_los.py** - Range calculation and line-of-sight validation
- **test_movement_validator.py** - Movement action validation with hex grid
- **test_depth_validator.py** - Depth change validation with ballast tank damage
- **test_repair_validator.py** - Repair action validation with crew status
- **test_combat_resolver.py** - Combat resolution with deck gun and torpedoes
- **test_torpedo_validator.py** - Torpedo loading and firing validation

### Phase 3 Actions (100% Complete)

- **test_action_stacking.py** - Action stacking and queueing validation per RULES.md line 215
- **test_movement_actions.py** - MoveAction, RotateAction tests
- **test_combat_actions.py** - RepairAction, DeckGunAction tests
- **test_action_system.py** - ActionQueue integration tests
- **test_damage_resolution.py** - Damage application tests

### Phase 4 Enemy AI (100% Complete)

- **test_merchant_ai.py** (14 tests) - Merchant movement along predefined paths, damage rules
- **test_merchant_integration.py** (3 tests) - Merchant phase integration with game loop
- **test_detection_ai.py** (16 tests) - Escort detection rolls, range/LOS checks, depth modifiers
- **test_detection_integration.py** (5 tests) - Detection phase integration with game loop
- **test_escort_ai.py** (39 tests) - Escort ship behaviors, movement, and attack logic
- **test_escort_ai_comprehensive.py** (26 tests) - Comprehensive escort AI die roll scenarios
- **test_b24_ai.py** - B-24 Liberator aircraft AI tests

### Game Victory/Loss Conditions (100% Complete)

- **test_victory_loss_conditions.py** (13 tests) - Victory and defeat condition validation
  - Loss: U-boat destroyed (hull damage 4/4)
  - Loss: Merchant escapes map (mission objective failure)
  - Victory: EXIT MAP button (position + facing + AP + merchants destroyed)
  - Defeat reason tracking system

All tests validate against JSON rule definitions from `missions/u_boat_ruleset_default.json`.

## Test Organization

Each test file follows this pattern:
1. Setup test fixtures (DiceRoller, validators, U-Boat state)
2. Test individual validation functions
3. Test edge cases and error conditions
4. Test info/display methods
5. Integration tests where applicable

All tests use deterministic seeded random numbers for reproducibility.
