# Escort AI Execution Model

## Purpose

This document explains how the escort AI rules are structured for **deterministic, simulation-safe execution** — not just human readability.

---

## Key Principles

### 1. **Sequence, Not Prose**

**Before (Human-readable):**

```json
"primary_action": "MOVE",
"then": "TURN",
"then_condition": "if blocked"
```

**After (Machine-executable):**

```json
"sequence": [
  {"action": "MOVE", "always": true},
  {"action": "TURN", "condition": {"check": "facing_blocked"}},
  {"action": "DEPTH_CHARGE", "condition": {"check": "u_boat_in_range_and_dl_1_to_3"}}
]
```

Each action in the sequence is evaluated **in order**. Conditions are explicit boolean checks.

---

### 2. **DL-Dependent Targeting (Gap 1 Fixed)**

**TURN behavior changes based on Detection Level:**

```json
"target_selection": {
  "dl_0_1": {"target": "anchor_hex"},
  "dl_2_3": {"target": "u_boat_hex"}
}
```

- **DL 0-1:** Escort circles the Anchor (patrol behavior)
- **DL 2-3:** Escort actively chases U-Boat (engagement behavior)

This controls pacing:
- Early game: escorts patrol area (tension builds)
- Mid-game: escorts converge on U-Boat (chase begins)

---

### 3. **Orientation States (Gap 2 Fixed)**

**Four distinct states:**

```json
"orientation_rules": {
  "facing_target": {
    "detection": {"logic": "on_same_hex_line AND facing_toward"},
    "behavior": {"turn_if": "facing_hex_blocked", "direction": "random"}
  },
  "facing_away": {
    "detection": {"logic": "on_same_hex_line AND facing_away"},
    "behavior": {"turn_if": "always", "direction": "random"}
  },
  "facing_sideways": {
    "detection": {"logic": "NOT on_same_hex_line"},
    "behavior": {"turn_if": "always", "direction": "toward_target_smallest_angle"}
  },
  "same_hex_as_u_boat": {
    "detection": {"logic": "escort_hex == u_boat_hex"},
    "behavior": {"turn_if": "facing_hex_blocked", "direction": "random"}
  }
}
```

**Detection logic determines state:**
1. Calculate hex line between escort and target
2. Check escort facing direction
3. Match to one of four states
4. Execute corresponding behavior

**Why this matters:**
- Escorts don't spin randomly when already facing target
- "Facing away" forces course correction (no reverse movement in game)
- Deterministic execution means replays work identically

---

### 4. **Conditional Action Chains (Gap 3 Fixed)**

**Example: Roll 2**

```json
{
  "roll": 2,
  "sequence": [
    {"action": "MOVE", "always": true},
    {"action": "TURN", "condition": {"check": "facing_blocked"}},
    {"action": "DEPTH_CHARGE", "condition": {"check": "u_boat_in_range_and_dl_1_to_3"}}
  ]
}
```

**Execution flow:**
1. **MOVE** — Always executed (escort moves forward)
2. **TURN** — Only if facing hex is blocked *after movement*
3. **DEPTH_CHARGE** — Only if U-Boat in range 0-1, submerged, and DL 1-3

**Why game state matters:**
- Movement may change range to U-Boat
- New position may block facing hex
- DEPTH_CHARGE eligibility evaluated *after* movement resolves

**Contrast with Roll 3:**

```json
{"action": "TURN", "always": true}  // Unconditional!
```

This ships **always** turns after moving (more aggressive closing behavior).

---

## Implementation Notes

### Condition Evaluation

All condition checks use explicit boolean logic:

```json
"condition": {
  "check": "u_boat_in_range_and_dl_1_to_3",
  "logic": "range_to_u_boat <= 1 AND u_boat.depth != SURFACED AND dl >= 1 AND dl <= 3"
}
```

**Engine must implement:**

- `range_to_u_boat()` — hex distance calculation
- `u_boat.depth` — current depth state
- `dl` — current detection level
- `facing_hex_blocked()` — terrain/collision check

### State Dependencies

Actions have implicit state requirements:

| Action | Requires | Modifies |
|--------|----------|----------|
| `MOVE` | facing_hex, terrain | position |
| `TURN` | orientation_state, dl | facing |
| `DEPTH_CHARGE` | range, u_boat_depth, dl | (triggers damage) |
| `FIRE` | range, LOS, u_boat_depth | dl, (triggers damage) |

**Execution order matters:** Position changes affect subsequent range checks.

---

## Testing Checklist

### Scenario 1: DL Transition (0 → 1)

- **Before:** Escort turns toward Anchor (patrol)
- **After:** Escort still turns toward Anchor (threshold is DL 2+)
- **Test:** Verify target selection doesn't change prematurely

### Scenario 2: DL Transition (1 → 2)

- **Before:** Escort turns toward Anchor
- **After:** Escort switches to U-Boat targeting (chase mode)
- **Test:** Verify immediate behavior change

### Scenario 3: Facing Target While Blocked

- **Setup:** Escort directly facing U-Boat, hex ahead has Land
- **Expected:** Escort turns randomly (not deterministically toward U-Boat)
- **Test:** Random turn occurs, not skipped

### Scenario 4: Facing Away

- **Setup:** Escort on same hex line as U-Boat, facing opposite direction
- **Expected:** Escort must turn randomly (even if facing hex is clear)
- **Test:** Turn always happens, not conditional on blocking

### Scenario 5: Roll 2 vs Roll 3

- **Setup:** Same escort position, different die rolls
- **Roll 2:** Only turns if blocked → may not close distance
- **Roll 3:** Always turns → actively closes on target
- **Test:** Different outcomes with identical starting state

---

## Why This Matters

### ✅ **Simulation Safety**

- Engine can execute rules without human interpretation
- No ambiguous "prose conditions"
- Deterministic execution = reproducible bugs

### ✅ **Automation-Ready**

- AI can evaluate conditions programmatically
- Action sequences are explicit data structures
- State machine implementation is straightforward

### ✅ **Correct Gameplay**

- Anchor vs U-Boat targeting controls pacing
- Orientation states prevent unrealistic behavior
- Conditional chains match rulebook intent

### ✅ **Maintainable**

- Logic is testable (unit tests for conditions)
- Changes don't require code modification
- Mission-specific overrides can tweak behavior

---

## Future: Mission Overrides

This structure allows missions to override specific behaviors:

```json
{
  "inherits": ["escort_ai_baseline"],
  "sections": [
    {
      "id": "destroyer_actions",
      "results": [
        {
          "roll": 1,
          "sequence": [
            {"action": "FIRE", "always": true}  // Elite destroyer always fires!
          ]
        }
      ]
    }
  ]
}
```

Because conditions are data, not code, missions can:
- Make escorts more aggressive (remove conditions)
- Change targeting priorities (swap anchor/u-boat logic)
- Add new conditions (weather, time-of-day)

All without touching core engine code.
