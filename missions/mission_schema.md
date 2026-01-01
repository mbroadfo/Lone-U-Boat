# Mission Metadata Schema

## Design Philosophy

**The mission sheet is not UI — it is a structured rules artifact.**

This schema defines how mission rules are represented as structured data, separate from any rendering or UI concerns. The game engine consumes this metadata to:
- Display appropriate rules based on current phase
- Look up action costs and modifiers
- Determine combat outcomes
- Check victory conditions
- Apply mission-specific constraints

### Core Principles

1. **Explicit over implicit** — No hidden assumptions
2. **Structured over freeform** — No text blobs where structure is needed
3. **Machine-consumable** — Engine can query and apply rules
4. **Human-readable** — Easy to author and maintain
5. **Phase-aware** — Rules grouped by game phase
6. **Extensible** — New mission types don't require schema changes
7. **Layered inheritance** — Missions inherit baseline rules and override only what changes

---

## Layered Architecture

**Prevent Copy-Paste Duplication Across 10 Missions**

Missions use a layered inheritance system to avoid duplicating ~1000 lines of game rules:

### Layer 1: Core System Rules (`core_system_rules.json`)
- **Override Policy:** NEVER - These are immutable game mechanics
- **Contents:** Damage charts, forced dive rules, collision mechanics, repair restrictions
- **Rationale:** Universal rules that never change across missions

### Layer 2: U-Boat Ruleset (`u_boat_ruleset_default.json`)
- **Override Policy:** RARELY - Only for special missions with modified U-Boat
- **Contents:** AP calculation, action costs by depth, torpedo/gun specs, crew effects
- **Rationale:** Standard Type VIIC capabilities

### Layer 3: Escort AI Baseline (`escort_ai_baseline.json`)
- **Override Policy:** RARELY - Only for missions with different AI behavior
- **Contents:** Detection system, destroyer/corvette action tables, merchant movement defaults
- **Rationale:** Standard escort behavior patterns

### Layer 4: Mission-Specific Rules (`mission_X_rules.json`)
- **Override Policy:** ALWAYS - This is where mission uniqueness lives
- **Contents:** Victory conditions, mission-specific events, overrides to baseline rules
- **Rationale:** What makes this mission different

### Inheritance Mechanism

```json
{
  "_comment": "Mission 1 - Delta-only rules",
  "_version": "2.0",
  "inherits": [
    "core_system_rules",
    "u_boat_ruleset_default",
    "escort_ai_baseline"
  ],
  "mission_meta": { ... },
  "sections": [
    // Only mission-specific sections here
    // Inherited sections are automatically loaded
  ]
}
```

**How it works:**
1. Loader reads `inherits` array from mission file
2. Loads each baseline file in order: core → u_boat → escort
3. Merges sections by ID (later layers override earlier ones)
4. Adds mission-specific sections last (highest precedence)
5. Validates that mission doesn't override non-overrideable sections

**Benefits:**
- Single source of truth for game mechanics
- One balance change updates all 10 missions
- Mission files are ~150 lines instead of ~1200 lines
- Clear separation between universal rules and mission-specific content

---

## Schema Structure

### Top-Level Mission Object

```json
{
  "_comment": "Optional description",
  "_version": "2.0",
  "inherits": ["core_system_rules", "u_boat_ruleset_default", "escort_ai_baseline"],
  "mission_meta": { ... },
  "sections": [ ... ]
}
```

---

## Section 1: Mission Metadata

Basic mission identification and objectives.

```json
"mission_meta": {
  "number": 1,
  "title": "Supply Ship Attack: North of Scotland",
  "subtitle": null,
  "objective": "Destroy the Merchant Ship before it exits the map, then exit the map in the direction of the red arrow.",
  "map_image": "assets/maps/mission_1.png",
  "difficulty": "beginner",
  "estimated_turns": 12
}
```

### Fields

- `number` (int): Mission number
- `title` (string): Full mission title
- `subtitle` (string|null): Optional subtitle
- `objective` (string): Primary objective description
- `map_image` (string): Path to map image
- `difficulty` (string): "beginner", "intermediate", "advanced"
- `estimated_turns` (int|null): Typical mission duration

---

## Section 2: Phase 1 — U-Boat Phase Rules

### 2.1 Action Points Rules

```json
{
  "id": "u_boat_ap_rules",
  "phase": 1,
  "type": "ap_rules",
  "label": "Action Points",
  "dice": {
    "normal": "3d6",
    "description": "Roll 3 dice (2 dice if Engine is Damaged)"
  },
  "calculation": "highest die rolled",
  "modifiers": [
    {
      "condition": "captain_alive",
      "effect": "+1 AP"
    },
    {
      "condition": "engine_damaged",
      "effect": "roll 2d6 instead"
    }
  ]
}
```

### 2.2 Depth Modifiers

```json
{
  "id": "u_boat_depth_modifiers",
  "phase": 1,
  "type": "depth_modifiers",
  "label": "Detection Level Modifiers by Depth",
  "modifiers": [
    {
      "depth": "SURFACED",
      "dl_modifier": 0
    },
    {
      "depth": "PERISCOPE",
      "dl_modifier": 0
    },
    {
      "depth": "MEDIUM",
      "dl_modifier": -1
    },
    {
      "depth": "DEEP",
      "dl_modifier": -2
    }
  ]
}
```

### 2.3 Action Costs Table

```json
{
  "id": "u_boat_action_costs",
  "phase": 1,
  "type": "action_costs",
  "label": "U-Boat Actions",
  "actions": [
    {
      "action": "MOVE",
      "costs": {
        "SURFACED": 1,
        "PERISCOPE": 2,
        "MEDIUM": 3,
        "DEEP": 3
      },
      "notes": "Can only enter a Ship's hex if Medium/Deep. Can only enter shallows if Surfaced/Periscope"
    },
    {
      "action": "TURN",
      "costs": {
        "SURFACED": 1,
        "PERISCOPE": 2,
        "MEDIUM": 2,
        "DEEP": 3
      },
      "notes": "1 hex edge left or right"
    },
    {
      "action": "CHANGE DEPTH",
      "costs": {
        "SURFACED": 2,
        "PERISCOPE": 1,
        "MEDIUM": 2,
        "DEEP": 1
      },
      "notes": "1 depth level (once per turn) (cannot go below Peri in shallows / above Med beneath ships)"
    },
    {
      "action": "REPAIR (Eng)",
      "costs": {
        "SURFACED": 2,
        "PERISCOPE": 4,
        "MEDIUM": 4,
        "DEEP": 4
      },
      "notes": "Remove 1 damage marker, or fix up to 2 Torp Tubes (Hull cannot be repaired). Only Surface repairs if Engineer is KIA. Flak and Deck Gun repairs only when Surfaced"
    },
    {
      "action": "FIRE DECK GUN",
      "costs": {
        "SURFACED": 0,
        "PERISCOPE": null,
        "MEDIUM": null,
        "DEEP": null
      },
      "notes": "At Ships in LOS (R1–3). Roll 2d6: 7+ to Hit at R1–2 • 8+ to Hit at R3 • On Hit, set DL to 3"
    },
    {
      "action": "LOAD TORPS",
      "costs": {
        "SURFACED": 1,
        "PERISCOPE": 4,
        "MEDIUM": null,
        "DEEP": null
      },
      "notes": "Load 2 tubes; +1 if Weapons Officer is KIA"
    },
    {
      "action": "FIRE TORPS",
      "costs": {
        "SURFACED": 2,
        "PERISCOPE": 2,
        "MEDIUM": null,
        "DEEP": null
      },
      "notes": "Fire 1–3 Torpedoes (R1–9). Roll 1d6 per Torp. If Fire 3, DL +1. Target first ship along line of fire. Missed Torps continue to other Ships beyond. If any hit, DL +1"
    }
  ]
}
```

---

## Section 3: Allied Ship Damage Chart

```json
{
  "id": "allied_ship_damage",
  "phase": 1,
  "type": "damage_chart",
  "label": "Allied Ship Damage Chart",
  "description": "For each Torpedo / Deck Gun Hit on a Ship, roll d6",
  "ship_classes": [
    {
      "ship_type": "merchant",
      "outcomes": [
        {
          "roll_min": 1,
          "roll_max": 1,
          "result": "NO_DAMAGE",
          "description": "No significant damage"
        },
        {
          "roll_min": 2,
          "roll_max": 3,
          "result": "DAMAGED",
          "description": "Damaged → Sunk"
        },
        {
          "roll_min": 4,
          "roll_max": 6,
          "result": "CATASTROPHIC",
          "description": "Catastrophic Hit — Sunk"
        }
      ]
    },
    {
      "ship_type": "corvette",
      "outcomes": [
        {
          "roll_min": 1,
          "roll_max": 2,
          "result": "NO_DAMAGE",
          "description": "No significant damage"
        },
        {
          "roll_min": 3,
          "roll_max": 4,
          "result": "DAMAGED",
          "description": "Damaged → Sunk"
        },
        {
          "roll_min": 5,
          "roll_max": 6,
          "result": "CATASTROPHIC",
          "description": "Catastrophic Hit — Sunk"
        }
      ]
    },
    {
      "ship_type": "destroyer",
      "outcomes": [
        {
          "roll_min": 1,
          "roll_max": 3,
          "result": "NO_DAMAGE",
          "description": "No significant damage"
        },
        {
          "roll_min": 4,
          "roll_max": 5,
          "result": "DAMAGED",
          "description": "Damaged → Sunk"
        },
        {
          "roll_min": 6,
          "roll_max": 6,
          "result": "CATASTROPHIC",
          "description": "Catastrophic Hit — Sunk"
        }
      ]
    }
  ],
  "notes": [
    "A ship already Damaged that takes another hit is Sunk",
    "Catastrophic hits sink the ship immediately regardless of prior state"
  ]
}
```

---

## Section 4: Phase 2 — Merchant Phase Rules

```json
{
  "id": "merchant_movement",
  "phase": 2,
  "type": "movement_rules",
  "label": "Merchant Ships Phase",
  "rules": [
    {
      "condition": "UNDAMAGED",
      "action": "MOVE",
      "distance": 1,
      "notes": "Always face dotted line"
    },
    {
      "condition": "DAMAGED",
      "action": "ROLL_TO_MOVE",
      "dice": "1d6",
      "success": "4+",
      "on_success": {
        "action": "MOVE",
        "distance": 1
      },
      "on_fail": {
        "action": "NO_MOVE"
      },
      "notes": "Always face dotted line"
    }
  ]
}
```

---

## Section 5: Phase 3 — Detection Phase Rules

```json
{
  "id": "detection_rules",
  "phase": 3,
  "type": "detection_rules",
  "label": "Detection Phase",
  "procedure": "Roll 1d6 for each Escort that has the U-Boat in LOS and within 3 hexes. Each success = +1 DL",
  "base_detection_thresholds": [
    {
      "depth": "SURFACED",
      "roll_required": "1+"
    },
    {
      "depth": "PERISCOPE",
      "roll_required": "2+"
    },
    {
      "depth": "MEDIUM",
      "roll_required": "4+"
    },
    {
      "depth": "DEEP",
      "roll_required": "5+"
    }
  ],
  "modifiers": [
    {
      "condition": "engine_damaged",
      "effect": "Decrease roll required by 1",
      "description": "Engine damage makes detection easier"
    },
    {
      "condition": "sonar_operator_alive",
      "effect": "Increase roll required by 1",
      "description": "Sonar operator makes detection harder"
    }
  ]
}
```

---

## Section 6: Phase 4 — Escorts Phase Rules

### 6.1 Activation Order

```json
{
  "id": "escort_activation_order",
  "phase": 4,
  "type": "activation_rule",
  "label": "Escorts Activation Order",
  "rule": "Activate closest first (you choose for ties)"
}
```

### 6.2 Destroyer Action Table

```json
{
  "id": "destroyer_actions",
  "phase": 4,
  "type": "escort_action_table",
  "label": "Destroyer Actions",
  "ship_type": "destroyer",
  "dice": "1d6",
  "results": [
    {
      "roll": 1,
      "primary_action": "FIRE",
      "alternate_action": "DEPTH_CHARGE",
      "condition": "DL 1–3"
    },
    {
      "roll": 2,
      "primary_action": "MOVE",
      "fallback": "TURN",
      "condition": "if blocked"
    },
    {
      "roll": 3,
      "primary_action": "MOVE",
      "then": "TURN"
    },
    {
      "roll": 4,
      "primary_action": "MOVE",
      "then": "DEPTH_CHARGE",
      "condition": "if DL 1–3"
    },
    {
      "roll": 5,
      "primary_action": "MOVE",
      "then": "DEPTH_CHARGE",
      "condition": "if DL 1–3"
    },
    {
      "roll": 6,
      "primary_action": "MOVE",
      "then": "TURN"
    }
  ]
}
```

### 6.3 Corvette Action Table

```json
{
  "id": "corvette_actions",
  "phase": 4,
  "type": "escort_action_table",
  "label": "Corvette Actions",
  "ship_type": "corvette",
  "dice": "1d6",
  "results": [
    {
      "roll": 1,
      "primary_action": "FIRE",
      "alternate_action": "DEPTH_CHARGE",
      "condition": "DL 1–3"
    },
    {
      "roll": 2,
      "primary_action": "MOVE",
      "then": "DEPTH_CHARGE",
      "condition": "if DL 1–3"
    },
    {
      "roll": 3,
      "primary_action": "MOVE",
      "then": "FIRE",
      "condition": "if DL 1–3"
    },
    {
      "roll": 4,
      "primary_action": "MOVE",
      "then": "TURN"
    },
    {
      "roll": 5,
      "primary_action": "MOVE",
      "then": "DEPTH_CHARGE",
      "condition": "if DL 1–3"
    },
    {
      "roll": 6,
      "primary_action": "MOVE",
      "then": "DEPTH_CHARGE",
      "condition": "if DL 1–3"
    }
  ]
}
```

### 6.4 Escort Action Definitions

```json
{
  "id": "escort_action_definitions",
  "phase": 4,
  "type": "action_definitions",
  "label": "Escort Actions Detail",
  "actions": [
    {
      "action": "DEPTH_CHARGE",
      "conditions": [
        "U-Boat not Surfaced",
        "Range 0–1"
      ],
      "effect": {
        "roll": "1d6",
        "table": "U-Boat Damage Chart"
      },
      "special": {
        "destroyer": "rolls 2d6, take lowest"
      }
    },
    {
      "action": "TURN",
      "logic": [
        {
          "condition": "DL 0–1",
          "effect": "turn 1 hex towards Anchor"
        },
        {
          "condition": "DL 2–3",
          "effect": "turn 1 hex towards U-Boat"
        }
      ]
    },
    {
      "action": "FIRE",
      "conditions": [
        "U-Boat Surfaced",
        "LOS exists",
        "Range 1–3"
      ],
      "effect": {
        "detection": "Set DL to 3",
        "damage": "Roll Critical Hit on U-Boat Damage Chart"
      }
    }
  ]
}
```

---

## Section 7: Phase 5 — Allied B24 Phase

```json
{
  "id": "b24_phase",
  "phase": 5,
  "type": "air_phase_rules",
  "label": "Allied B24 Phase",
  "enabled": false,
  "note": "Not present in Mission 1"
}
```

---

## Section 8: Phase 6 — End-of-Turn Events

```json
{
  "id": "end_of_turn_events",
  "phase": 6,
  "type": "event_table",
  "label": "End-of-Turn Events",
  "enabled": false,
  "note": "Mission 1 has no end-of-turn event table"
}
```

---

## Section 9: U-Boat Damage Chart

```json
{
  "id": "u_boat_damage_chart",
  "phase": null,
  "type": "damage_chart",
  "label": "U-Boat Damage Chart",
  "description": "Apply when U-Boat takes damage from depth charges or surface fire",
  "outcomes": [
    {
      "roll_min": 1,
      "roll_max": 1,
      "result": "CRITICAL_HIT",
      "description": "Critical Hit",
      "sub_table": "critical_hit_table"
    },
    {
      "roll_min": 2,
      "roll_max": 3,
      "result": "HULL_DAMAGE",
      "description": "Hull Damage",
      "effect": "Add 1 Hull damage marker (cannot be repaired)",
      "limit": "4 Hull damage = U-Boat destroyed"
    },
    {
      "roll_min": 4,
      "roll_max": 6,
      "result": "GENERAL_DAMAGE",
      "description": "General Damage",
      "sub_table": "general_damage_table"
    }
  ],
  "sub_tables": {
    "critical_hit_table": {
      "label": "Critical Hit Sub-Table",
      "dice": "1d6",
      "outcomes": [
        {
          "roll_min": 1,
          "roll_max": 2,
          "result": "HULL_DAMAGE",
          "description": "Hull Damage",
          "effect": "Add 1 Hull damage (cannot be repaired)"
        },
        {
          "roll_min": 3,
          "roll_max": 4,
          "result": "GENERAL_DAMAGE",
          "description": "General Damage",
          "effect": "Roll on General Damage table"
        },
        {
          "roll_min": 5,
          "roll_max": 5,
          "result": "CREW_KIA",
          "description": "Crew KIA",
          "effect": "Roll 1d6 to determine crew member. Medic may save on 5+"
        },
        {
          "roll_min": 6,
          "roll_max": 6,
          "result": "CATASTROPHIC",
          "description": "Catastrophic Damage",
          "effect": "U-Boat destroyed"
        }
      ]
    },
    "general_damage_table": {
      "label": "General Damage Sub-Table",
      "dice": "1d6",
      "outcomes": [
        {
          "roll_min": 1,
          "roll_max": 2,
          "result": "TORPEDO_DAMAGE",
          "description": "Torpedo Tube Damaged",
          "effect": "Randomly select 1 torpedo tube and mark as damaged"
        },
        {
          "roll_min": 3,
          "roll_max": 4,
          "result": "ENGINE_DAMAGE",
          "description": "Engine Damaged",
          "effect": "Mark engine as damaged. Roll 2d6 for AP instead of 3d6"
        },
        {
          "roll_min": 5,
          "roll_max": 5,
          "result": "DECK_GUN_DAMAGE",
          "description": "Deck Gun Damaged",
          "effect": "Mark deck gun as damaged. Cannot use until repaired"
        },
        {
          "roll_min": 6,
          "roll_max": 6,
          "result": "FLAK_GUN_DAMAGE",
          "description": "Flak Gun Damaged",
          "effect": "Mark flak gun as damaged. Cannot use until repaired"
        }
      ]
    }
  }
}
```

---

## Section 10: Reminder Rules

```json
{
  "id": "reminder_rules",
  "phase": null,
  "type": "reminder_rules",
  "label": "Important Reminders",
  "rules": [
    {
      "category": "forced_dive",
      "title": "Forced Dive",
      "description": "If DL reaches 3, U-Boat must immediately dive to at least Periscope depth (no AP cost)",
      "trigger": "DL = 3"
    },
    {
      "category": "shallow_water",
      "title": "Shallow Water Constraints",
      "description": "Cannot go below Periscope depth in shallow water hexes",
      "applies_to": "CHANGE DEPTH action"
    },
    {
      "category": "ship_hex_entry",
      "title": "Entering Ship Hexes",
      "description": "Can only enter a hex occupied by a ship when at Medium or Deep depth",
      "applies_to": "MOVE action"
    },
    {
      "category": "collision",
      "title": "Collision with Ships",
      "description": "If U-Boat enters a ship's hex at Surfaced or Periscope depth, collision occurs (see collision rules)",
      "severity": "critical"
    },
    {
      "category": "depth_change_limit",
      "title": "Depth Change Limit",
      "description": "Can only change depth once per turn",
      "applies_to": "CHANGE DEPTH action"
    },
    {
      "category": "beneath_ships",
      "title": "Depth Beneath Ships",
      "description": "Cannot go above Medium depth while in a hex occupied by a ship",
      "applies_to": "CHANGE DEPTH action"
    }
  ]
}
```

---

## Section 11: Victory Conditions

```json
{
  "id": "victory_conditions",
  "phase": null,
  "type": "victory_conditions",
  "label": "Victory Conditions",
  "primary": {
    "description": "Destroy the Merchant Ship",
    "condition": "merchant_sunk"
  },
  "secondary": {
    "description": "Exit the map in the direction of the red arrow",
    "condition": "u_boat_exits"
  },
  "failure": {
    "description": "Merchant Ship exits the map",
    "condition": "merchant_escapes"
  },
  "bonus": {
    "description": "Sink all enemy vessels",
    "condition": "all_ships_sunk"
  }
}
```

---

## Usage Examples

### Querying Rules by Phase

```python
def get_phase_sections(mission_data, phase_number):
    """Get all rule sections for a specific phase."""
    return [
        section for section in mission_data["sections"]
        if section.get("phase") == phase_number
    ]
```

### Looking Up Action Costs

```python
def get_action_cost(mission_data, action_name, depth):
    """Get AP cost for an action at a given depth."""
    for section in mission_data["sections"]:
        if section["type"] == "action_costs":
            for action in section["actions"]:
                if action["action"] == action_name:
                    return action["costs"].get(depth)
    return None
```

### Rolling on Damage Tables

```python
def apply_ship_damage(mission_data, ship_type, roll):
    """Determine damage result for a ship."""
    for section in mission_data["sections"]:
        if section["id"] == "allied_ship_damage":
            for ship_class in section["ship_classes"]:
                if ship_class["ship_type"] == ship_type:
                    for outcome in ship_class["outcomes"]:
                        if outcome["roll_min"] <= roll <= outcome["roll_max"]:
                            return outcome["result"]
    return None
```

---

## Mission Authoring Guide

### Creating a New Mission

**Step 1: Start with minimal template**

```json
{
  "_comment": "Mission X - Delta-only rules",
  "_version": "2.0",
  "inherits": [
    "core_system_rules",
    "u_boat_ruleset_default",
    "escort_ai_baseline"
  ],
  "mission_meta": {
    "number": X,
    "title": "Your Mission Title",
    "objective": "Mission objective description",
    "map_image": "assets/maps/mission_X.png",
    "difficulty": "beginner|intermediate|advanced",
    "estimated_turns": 12
  },
  "sections": []
}
```

**Step 2: Add mission-specific sections only**

Do NOT copy action costs, damage charts, or detection rules from other missions. Only add sections that are:
- **Unique to this mission** (victory conditions, special events)
- **Modified from baseline** (different merchant movement, special AI behavior)
- **Disabled baseline features** (no B24, no end-of-turn events)

**Step 3: Test inheritance**

```python
from missions.mission_rules_loader import load_mission_rules

rules = load_mission_rules(X)
print(f"Sections loaded: {len(rules.sections)}")  # Should be ~20-25
print(f"Inherits from: {rules.inherits}")  # Should list 3 baseline files

# Test queries work
print(rules.get_action_cost("MOVE", "PERISCOPE"))  # Should return 2
print(rules.get_detection_threshold("MEDIUM"))     # Should return 4
```

### When to Override Baseline Rules

**DON'T override if:**
- Standard U-Boat Type VIIC behavior (use default)
- Standard escort AI patterns (use default)
- Universal damage mechanics (use default)

**DO override if:**
- Mission has special merchant ship behavior
- Mission introduces new ship types
- Mission has unique B24 or air rules
- Mission has special detection modifiers
- Mission disables standard phases

### Example: Mission with Modified Merchant Movement

```json
{
  "inherits": ["core_system_rules", "u_boat_ruleset_default", "escort_ai_baseline"],
  "mission_meta": { "number": 5, "title": "Fast Convoy" },
  "sections": [
    {
      "id": "merchant_movement",
      "phase": 2,
      "type": "movement_rules",
      "label": "Fast Merchant Ships",
      "rules": [
        {
          "condition": "UNDAMAGED",
          "action": "MOVE",
          "distance": 2,
          "notes": "Fast merchants move 2 hexes"
        }
      ]
    },
    {
      "id": "victory_conditions",
      "type": "victory_conditions",
      "primary": { "description": "Sink at least 2 merchants" }
    }
  ]
}
```

**Result:** Mission inherits all 20+ baseline sections but overrides just merchant movement (150 lines vs 1200 lines).

### Validation Rules

The loader automatically validates:
1. ✓ Mission doesn't override `u_boat_damage_chart`
2. ✓ Mission doesn't override `allied_ship_damage`
3. ✓ Mission doesn't override `reminder_rules`
4. ✓ All 3 baseline files exist and are readable

If validation fails, you'll get a clear error message:
```
ValueError: Mission attempts to override non-overrideable section: u_boat_damage_chart.
Core system rules from core_system_rules.json cannot be overridden.
```

---

## Extension Points

### Adding New Mission Types

New missions can include additional section types:
- `weather_effects`
- `special_events`
- `reinforcement_rules`
- `minefield_rules`
- `night_rules`

### Adding New Ship Types

Ship damage tables are extensible:

```json
{
  "ship_type": "tanker",
  "outcomes": [ ... ]
}
```

### Mission-Specific Overrides

Missions can override base rules:

```json
{
  "id": "mission_2_ap_rules",
  "phase": 1,
  "type": "ap_rules",
  "override": true,
  "dice": {
    "normal": "2d6",
    "description": "Mission 2: Stormy weather reduces dice to 2d6"
  }
}
```

---

## Schema Validation

Future implementation should include:
- JSON Schema validation
- Type checking for numeric ranges
- Phase number validation (1-6)
- Required field validation
- Cross-reference validation (e.g., ship types)

---

## Migration Path

This schema is designed for backward compatibility:
1. Existing mission config files remain valid
2. JSON metadata files are additive
3. UI code can gradually migrate to consume structured data
4. Legacy text-based rules can coexist during transition
