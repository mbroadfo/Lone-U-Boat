# Mission 1 Rules Audit — Global vs Mission-Specific

## Analysis Methodology

Compare [mission_1_rules.json](mission_1_rules.json) against the full game rules in [rules/combined.txt](../rules/combined.txt) to identify:

1. **GLOBAL RULES** — Core game mechanics that never change across missions
2. **MISSION-SPECIFIC** — Content unique to this mission only
3. **DANGEROUS DUPLICATES** — Rules that will drift if copied to each mission

---

## Audit Results

### ✅ **GLOBAL - Core System Rules** (should never be in mission files)

| Section ID | Type | Rationale |
|------------|------|-----------|
| `u_boat_damage_chart` | `damage_chart` | Standard d6 outcomes, never varies across missions |
| `allied_ship_damage` | `damage_chart` | Merchant/Corvette/Destroyer tables are universal |
| `u_boat_ap_rules` | `ap_rules` | AP calculation (3d6 take highest, +1 if captain alive) is always the same |
| `u_boat_action_costs` | `action_costs` | Action costs by depth are game-wide mechanics |
| `detection_rules` | `detection_rules` | Base detection thresholds (Surfaced 1+, Periscope 2+, etc.) are constant |
| `destroyer_actions` | `escort_action_table` | Destroyer AI d6 table is standard game behavior |
| `corvette_actions` | `escort_action_table` | Corvette AI d6 table is standard game behavior |
| `escort_action_definitions` | `action_definitions` | DEPTH_CHARGE, TURN, FIRE mechanics are universal |
| `escort_activation_order` | `activation_rule` | "Closest first" is a core AI rule |
| `reminder_rules` | `reminder_rules` | Forced dive, shallow water, collision rules are game-wide |

### ⚠️ **MISSION-SPECIFIC - Keep in Mission Files**

| Section ID | Type | Rationale |
|------------|------|-----------|
| `mission_meta` | Mission metadata | Unique to each mission (title, objective) |
| `merchant_movement` | `movement_rules` | Could vary per mission (speed, damage behavior) |
| `b24_phase` | `air_phase_rules` | Mission 1 has no B24; others might |
| `end_of_turn_events` | `event_table` | Varies significantly per mission (per rules) |
| `victory_conditions` | `victory_conditions` | Always mission-specific |
| `u_boat_depth_modifiers` | `depth_modifiers` | **BORDERLINE** - normally global, but could have mission overrides |

### 🔥 **DANGEROUS DUPLICATES** (will cause rules drift)

These are currently in mission_1_rules.json but should NOT be:

1. **U-Boat Damage Chart** — If we copy this to all 10 missions and later decide "Critical Hit on roll 1 should have different outcomes", we'd need to edit 10 files
2. **Allied Ship Damage Chart** — Same problem: one balance change = 10 file edits
3. **Action Costs Table** — If "MOVE at SURFACED should cost 2 AP instead of 1", we'd have to update every mission
4. **Detection Thresholds** — If "MEDIUM should be 5+ instead of 4+", every mission file breaks
5. **Escort AI Tables** — If destroyer behavior changes, we have 10 copies to sync

**Risk**: Rules will silently diverge. Mission 3's Corvette AI will differ from Mission 7's by accident.

---

## Refactoring Strategy

### Layer 1: Core System Rules (`core_system_rules.json`)

**Purpose**: Universal game mechanics that never change

**Contains**:
- U-Boat damage chart (all outcomes, sub-tables)
- Allied ship damage charts (all ship types)
- Crew KIA system
- Hull damage limits
- Repair restrictions
- Forced dive mechanics
- Collision rules
- Line of sight rules (if structured)

**Override Policy**: ❌ **NEVER OVERRIDEABLE**

---

### Layer 2: U-Boat Ruleset (`u_boat_ruleset_default.json`)

**Purpose**: Standard U-Boat capabilities

**Contains**:
- AP calculation rules (dice, modifiers)
- Action costs by depth
- Depth modifiers (DL changes)
- Torpedo rules (range, hit tables)
- Deck gun rules (range, hit tables)
- Repair action rules

**Override Policy**: ⚠️ **RARELY OVERRIDEABLE** — Only for special missions (e.g., "Damaged U-Boat" scenario)

---

### Layer 3: Escort AI Baseline (`escort_ai_baseline.json`)

**Purpose**: Standard escort behavior

**Contains**:
- Destroyer action table (d6 outcomes)
- Corvette action table (d6 outcomes)
- Action definitions (DEPTH_CHARGE, FIRE, TURN, MOVE)
- Activation order rules
- Dice calculation formulas
- Detection mechanics (base thresholds, modifiers)

**Override Policy**: ⚠️ **RARELY OVERRIDEABLE** — Only for mission-specific variants (e.g., "Elite Destroyer Squadron")

---

### Layer 4: Mission Rules (`mission_X_rules.json`)

**Purpose**: Mission-specific content ONLY

**Contains**:
- Mission metadata (title, objective, difficulty)
- Phase enablement (B24 present? Event table?)
- Victory/failure conditions
- Mission-specific movement rules (if different)
- End-of-turn event tables
- **Overrides** (if any special rules apply)

**Example Mission 1 (stripped down)**:

```json
{
  "mission_meta": {
    "number": 1,
    "title": "Supply Ship Attack: North of Scotland",
    "objective": "Destroy the Merchant Ship before it exits the map..."
  },
  "sections": [
    {
      "id": "merchant_movement",
      "phase": 2,
      "type": "movement_rules",
      "label": "Merchant Ships Phase",
      "rules": [ ... ]
    },
    {
      "id": "b24_phase",
      "phase": 5,
      "enabled": false
    },
    {
      "id": "end_of_turn_events",
      "phase": 6,
      "enabled": false
    },
    {
      "id": "victory_conditions",
      "phase": null,
      "type": "victory_conditions",
      "label": "Victory Conditions",
      "primary": { "description": "Destroy the Merchant Ship", ... }
    }
  ],
  "inherits": [
    "core_system_rules",
    "u_boat_ruleset_default",
    "escort_ai_baseline"
  ]
}
```

---

## Override Hierarchy

``` text
core_system_rules.json (NEVER override)
  ↓
u_boat_ruleset_default.json (rarely override)
  ↓
escort_ai_baseline.json (rarely override)
  ↓
mission_X_rules.json (mission-specific + overrides)
```

**Resolution Order**: Mission rules override baseline, baseline overrides core (where allowed)

---

## What Can Be Overridden?

### ❌ **NEVER OVERRIDEABLE**

- Damage chart outcomes (core game balance)
- Crew KIA system
- Hull damage limits (4 = destroyed)
- Forced dive mechanics
- Collision resolution
- Phase sequencing

### ⚠️ **OVERRIDEABLE WITH CAUTION**

- Action costs (e.g., "Tutorial Mission: All actions cost 1 AP")
- Detection thresholds (e.g., "Foggy Mission: All detection +1 harder")
- Escort AI behavior (e.g., "Aggressive Destroyer: Different dice table")
- Repair restrictions (e.g., "Advanced U-Boat: Can repair hull")

### ✅ **ALWAYS OVERRIDEABLE**

- Phase enablement (B24 yes/no, events yes/no)
- Victory conditions
- Mission objectives
- End-of-turn event tables
- NPC movement patterns
- Special mission-specific rules

---

## Example: Mission with Overrides

**Mission 7 hypothetical**: "Night Attack — Reduced Visibility"

```json
{
  "mission_meta": {
    "number": 7,
    "title": "Night Attack",
    "special_rules": "Reduced visibility due to darkness"
  },
  "sections": [
    {
      "id": "detection_rules_override",
      "phase": 3,
      "type": "detection_rules",
      "override": true,
      "label": "Night Detection",
      "base_detection_thresholds": [
        { "depth": "SURFACED", "roll_required": 2 },
        { "depth": "PERISCOPE", "roll_required": 3 },
        { "depth": "MEDIUM", "roll_required": 5 },
        { "depth": "DEEP", "roll_required": 6 }
      ],
      "note": "Night conditions: All detection rolls +1 harder"
    }
  ],
  "inherits": [
    "core_system_rules",
    "u_boat_ruleset_default",
    "escort_ai_baseline"
  ]
}
```

---

## Benefits of Layering

✅ **Single source of truth** — Core rules defined once  
✅ **Easy balancing** — Change action cost in one file, applies to all missions  
✅ **No drift** — Missions automatically get rule updates  
✅ **Clear intent** — Mission files show only what's unique  
✅ **Smaller files** — Mission JSONs are 90% smaller  
✅ **Extensibility** — New missions inherit defaults automatically  

---

## Migration Plan

1. ✅ **Audit complete** (this document)
2. ⬜ Create `core_system_rules.json`
3. ⬜ Create `u_boat_ruleset_default.json`
4. ⬜ Create `escort_ai_baseline.json`
5. ⬜ Strip `mission_1_rules.json` to delta-only
6. ⬜ Update `mission_rules_loader.py` to support layering
7. ⬜ Add `inherits` field resolution
8. ⬜ Add override detection and merging
9. ⬜ Test that Mission 1 resolves correctly
10. ⬜ Document layering system in schema

---

**Status**: Audit complete, ready for implementation  
**Next**: Create the three baseline rule files
