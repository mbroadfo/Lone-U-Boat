# Mission Metadata System

## Overview

The Mission Metadata System transforms mission rules from implicit UI formatting into explicit, structured data that the game engine can consume programmatically. This enables:

- **Phase-aware rule display** — Show only relevant rules for current phase
- **Programmatic rule queries** — AI and combat systems query rules directly
- **Consistent mission authoring** — All missions follow the same schema
- **Future automation** — Rules logic can be automated without code changes
- **Zero ambiguity** — No interpretation needed, all rules are explicit

## Core Principle

> **"The mission sheet is not UI — it is a structured rules artifact."**

Mission rules are data, not formatting. The UI consumes this data and decides how to render it.

## Quick Start

### Loading Mission Rules

```python
from missions.mission_rules_loader import load_mission_rules

# Load Mission 1
rules = load_mission_rules(1)

print(f"Mission: {rules.mission_title}")
print(f"Objective: {rules.objective}")
```

### Querying Action Costs

```python
# Get AP cost for MOVE action at MEDIUM depth
cost = rules.get_action_cost("MOVE", "MEDIUM")
print(f"MOVE at MEDIUM depth costs {cost} AP")

# Get all available actions at a given depth
actions = rules.get_available_actions("SURFACED")
for action in actions:
    print(f"{action['action']}: {action['cost']} AP")
```

### Checking Ship Damage

```python
# Roll damage for a merchant ship
roll = 4
outcome = rules.get_ship_damage_outcome("merchant", roll)
print(f"Merchant hit (roll {roll}): {outcome['result']}")
print(f"Description: {outcome['description']}")
```

### Getting Phase-Specific Rules

```python
# Get all rules sections for Phase 4 (Escorts)
phase_4_sections = rules.get_sections_by_phase(4)
for section in phase_4_sections:
    print(f"- {section['label']}")
```

### Detection Mechanics

```python
# Get detection threshold for current depth
threshold = rules.get_detection_threshold("PERISCOPE")
print(f"Detection at PERISCOPE: {threshold}+ on d6")

# Get detection modifiers
modifiers = rules.get_detection_modifiers()
for mod in modifiers:
    print(f"{mod['condition']}: {mod['description']}")
```

## File Structure

``` text
missions/
├── mission_schema.md              # Complete schema documentation
├── mission_1_rules.json           # Mission 1 structured rules
├── mission_rules_loader.py        # Python query interface
├── mission_1_config.py            # Existing config (positions, terrain)
├── M1.txt                         # Original mission card text
└── README_METADATA.md             # This file
```

## Architecture

### Separation of Concerns

**mission_X_config.py** (Python)
- Starting positions
- Terrain layout (shallow/land hexes)
- Victory conditions
- Exit positions
- Patrol routes

**mission_X_rules.json** (JSON)
- Action costs by depth
- Damage charts and roll tables
- Detection thresholds
- Escort behavior tables
- Phase-specific rules
- Reminder rules

**mission_rules_loader.py** (Python)
- Query interface for rules
- Convenience methods
- Type-safe access

### Integration Points

The mission metadata system integrates with:

1. **Action System** (Phase 2A)
   - Query action costs: `get_action_cost(action, depth)`
   - Validate actions: `get_action_notes(action)`

2. **Combat System** (Phase 3)
   - Roll ship damage: `get_ship_damage_outcome(ship_type, roll)`
   - Roll U-Boat damage: `get_u_boat_damage_outcome(roll)`
   - Sub-table lookups: `get_u_boat_sub_table_outcome(table, roll)`

3. **Detection System** (Phase 3B)
   - Base thresholds: `get_detection_threshold(depth)`
   - Modifiers: `get_detection_modifiers()`

4. **Escort AI** (Phase 4C-F)
   - Action tables: `get_escort_action_result(ship_type, roll)`
   - Action definitions: `get_escort_action_definition(action)`

5. **Victory Conditions** (Phase 5C)
   - Check conditions: `get_victory_conditions()`

6. **UI Display** (All Phases)
   - Phase filtering: `get_sections_by_phase(phase)`
   - Section types: `get_sections_by_type(type)`

## Schema Overview

### Section Types

| Type | Purpose | Phase | Example |
|------|---------|-------|---------|
| `ap_rules` | Action point calculation | 1 | How many dice to roll, modifiers |
| `depth_modifiers` | DL changes by depth | 1 | Medium: -1 DL |
| `action_costs` | AP costs by depth | 1 | MOVE at SURFACED: 1 AP |
| `damage_chart` | Roll outcome tables | Any | Ship/U-Boat damage results |
| `movement_rules` | NPC movement logic | 2 | Merchant moves if undamaged |
| `detection_rules` | Detection mechanics | 3 | Detection thresholds by depth |
| `escort_action_table` | AI behavior dice | 4 | Destroyer roll 1-6 actions |
| `action_definitions` | Action mechanics | 4 | How DEPTH_CHARGE works |
| `air_phase_rules` | Aircraft behavior | 5 | B24 movement and attacks |
| `event_table` | Random events | 6 | End-of-turn event rolls |
| `reminder_rules` | Edge cases | Any | Forced dive at DL 3 |
| `victory_conditions` | Win/loss conditions | Any | Sink merchant, exit map |

### Key Design Patterns

**Roll Tables**

```json
{
  "outcomes": [
    {
      "roll_min": 1,
      "roll_max": 3,
      "result": "NO_DAMAGE",
      "description": "No significant damage"
    }
  ]
}
```

**Conditional Logic**

```json
{
  "condition": "DAMAGED",
  "action": "ROLL_TO_MOVE",
  "dice": "1d6",
  "success": "4+",
  "on_success": { "action": "MOVE" },
  "on_fail": { "action": "NO_MOVE" }
}
```

**Depth-Based Costs**

```json
{
  "action": "MOVE",
  "costs": {
    "SURFACED": 1,
    "PERISCOPE": 2,
    "MEDIUM": 3,
    "DEEP": 3
  }
}
```

## Usage Examples

### Example 1: Action Validation

```python
def can_perform_action(rules, action_name, depth, available_ap):
    """Check if player has enough AP for an action."""
    cost = rules.get_action_cost(action_name, depth)
    
    if cost is None:
        return False, f"{action_name} not available at {depth}"
    
    if cost > available_ap:
        return False, f"Need {cost} AP, have {available_ap}"
    
    return True, f"OK: {action_name} costs {cost} AP"
```

### Example 2: Combat Resolution

```python
def resolve_torpedo_hit(rules, ship_type, roll):
    """Resolve torpedo hit on a ship."""
    outcome = rules.get_ship_damage_outcome(ship_type, roll)
    
    if outcome['result'] == 'CATASTROPHIC':
        return 'SUNK', 'Ship sunk immediately'
    elif outcome['result'] == 'DAMAGED':
        return 'DAMAGED', 'Ship damaged, will sink if hit again'
    else:
        return 'NO_DAMAGE', 'Hit but no significant damage'
```

### Example 3: Detection Check

```python
def check_detection(rules, depth, engine_damaged, sonar_alive):
    """Calculate modified detection threshold."""
    base_threshold = rules.get_detection_threshold(depth)
    
    # Apply modifiers
    if engine_damaged:
        base_threshold -= 1  # Easier to detect
    if sonar_alive:
        base_threshold += 1  # Harder to detect
    
    return max(1, min(6, base_threshold))
```

### Example 4: Escort AI

```python
def resolve_escort_action(rules, ship_type, roll, detection_level):
    """Get what action an escort takes."""
    result = rules.get_escort_action_result(ship_type, roll)
    
    if not result:
        return None
    
    # Check conditions
    if result.get('condition'):
        if 'DL 1–3' in result['condition']:
            if detection_level not in [1, 2, 3]:
                # Fall back to primary action only
                return result['primary_action']
    
    return result
```

### Example 5: UI Phase Display

```python
def render_phase_rules(rules, current_phase):
    """Render only rules relevant to current phase."""
    sections = rules.get_sections_by_phase(current_phase)
    
    for section in sections:
        print(f"\n=== {section['label']} ===")
        
        if section['type'] == 'action_costs':
            for action in section['actions']:
                print(f"  {action['action']}")
                for depth, cost in action['costs'].items():
                    if cost is not None:
                        print(f"    {depth}: {cost} AP")
```

## Benefits

### For Developers

- **No hardcoded rules** — All rules in structured data
- **Easy to debug** — Rules are explicit and searchable
- **Type-safe queries** — Python interface prevents errors
- **Version controlled** — JSON changes tracked in git
- **Test-friendly** — Mock or override rules for testing

### For Game Design

- **Rapid iteration** — Change rules without code changes
- **Consistent format** — All missions use same structure
- **Easy balancing** — Adjust costs, thresholds, outcomes
- **Mission variants** — Override specific rules per mission
- **Documentation** — Schema serves as rules reference

### For Future Features

- **Phase-aware UI** — Expand/collapse based on active phase
- **Mission editor** — Visual tool to create missions
- **Rule automation** — AI applies rules programmatically
- **Mod support** — Players create custom missions
- **Difficulty modes** — Adjust costs and thresholds
- **Tutorial system** — Highlight relevant rules during play

## Migration Strategy

### Current State (Before)

```python
# Rules implied in UI text
mission_text = """
MOVE: 1 AP (Surfaced), 2 AP (Periscope), 3 AP (Medium/Deep)
"""
# UI parses and interprets this text
```

### Future State (After)

```python
# Rules are structured data
rules = load_mission_rules(1)
cost = rules.get_action_cost("MOVE", "SURFACED")
# UI queries and displays
```

### Backward Compatibility

- Existing `mission_X_config.py` files remain unchanged
- `mission_X_rules.json` is additive
- UI can gradually migrate from text parsing to structured queries
- Both systems can coexist during transition

## Validation

Future implementation should include:

```python
# JSON Schema validation
validate_mission_schema(mission_data)

# Type checking
assert isinstance(cost, int) or cost is None

# Range validation
assert 1 <= roll <= 6

# Cross-reference validation
assert ship_type in VALID_SHIP_TYPES
```

## Extending the Schema

### Adding New Section Types

```json
{
  "id": "weather_effects",
  "phase": null,
  "type": "weather_modifiers",
  "label": "Weather Effects",
  "conditions": [
    {
      "weather": "fog",
      "visibility_range": 2,
      "detection_modifier": -1
    }
  ]
}
```

### Mission-Specific Overrides

```json
{
  "id": "mission_2_ap_rules",
  "phase": 1,
  "type": "ap_rules",
  "override": true,
  "dice": {
    "normal": "2d6",
    "description": "Stormy weather: only 2d6"
  }
}
```

### New Ship Types

```json
{
  "ship_type": "tanker",
  "outcomes": [
    {
      "roll_min": 1,
      "roll_max": 2,
      "result": "DAMAGED",
      "description": "Damaged (leaking fuel)"
    }
  ]
}
```

## Testing

```python
# Unit tests for rules loader
def test_action_cost_lookup():
    rules = load_mission_rules(1)
    assert rules.get_action_cost("MOVE", "SURFACED") == 1
    assert rules.get_action_cost("MOVE", "DEEP") == 3
    assert rules.get_action_cost("INVALID", "SURFACED") is None

def test_damage_chart():
    rules = load_mission_rules(1)
    outcome = rules.get_ship_damage_outcome("merchant", 4)
    assert outcome['result'] == 'CATASTROPHIC'

def test_phase_filtering():
    rules = load_mission_rules(1)
    phase_1 = rules.get_sections_by_phase(1)
    assert len(phase_1) > 0
    assert all(s['phase'] == 1 for s in phase_1)
```

## Next Steps

1. ✅ Schema design complete
2. ✅ Mission 1 metadata created
3. ✅ Rules loader implemented
4. ⬜ Integrate with action system (Phase 2A)
5. ⬜ Integrate with combat system (Phase 3)
6. ⬜ Integrate with detection system (Phase 3B)
7. ⬜ Integrate with escort AI (Phase 4)
8. ⬜ Add JSON schema validation
9. ⬜ Create missions 2-10 metadata
10. ⬜ Phase-aware UI display

## Questions?

See `missions/mission_schema.md` for complete schema documentation and examples.

---

**Created:** January 1, 2026  
**Status:** Phase 1D — Schema and loader complete, integration pending
