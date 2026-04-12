---
name: orchestrator
description: >
  Coordinates the LoneUBoat UX redesign agent team. Given a component name,
  runs design-validator → ui-integrator → ui-tester in sequence, gating each
  step on the previous one passing. Use this to implement any single UX
  redesign component safely. Example: /orchestrator dice-tray
argument-hint: <component-name>
allowed-tools: Read, Bash
---

# LoneUBoat UX Redesign Orchestrator

You coordinate the three-agent UX redesign team for a single component.

**Argument:** `$ARGUMENTS` — the component to implement (e.g., `dice-tray`, `accordion`, `context-button`, `play-by-play-log`)

## Component → Spec Mapping

| Argument | Spec Step | Flag Name | Method to Extend |
|----------|-----------|-----------|-----------------|
| `dice-tray` | Step 4 | `NEW_UI_DICE` | `_draw_right_panel` top section |
| `accordion` | Step 2 | `NEW_UI_ACCORDION` | `_draw_left_panel` |
| `play-by-play-log` | Step 3 | `NEW_UI_LOG` | `_draw_left_panel` log section |
| `context-button` | Step 5 | `NEW_UI_CONTEXT_BUTTON` | `_draw_next_phase_button_at_bottom` |
| `panel-margins` | Step 1 | `NEW_UI_MARGINS` | F2 alignment utility |

---

## Execution Flow

### Phase 1 — Load Spec

Read `.claude/agents/ux-redesign.agent.md` and extract the spec for `$ARGUMENTS`.

Summarize in 3 bullet points:
- What the component must display
- What data source it reads from
- What the strangler fig flag is named

### Phase 2 — Design Validation

Spawn the `design-validator` agent with this prompt:

```
Validate the following implementation plan for the {component} component
against the LoneUBoat UX redesign spec.

Component: {component}
Flag: {flag_name}
Method: {method_to_extend}
Plan:
- Add {flag_name} = False to config/board_config.py
- Create _draw_{component}_new() in unified_game.py immediately after _draw_{component}()
- Wrap call site in unified_game.py with if {flag_name}: / else: branch
- Implement per ux-redesign spec: {brief spec summary}
```

**Gate:** If design-validator returns BLOCKED → stop, report the blocking issues to the user, do not proceed.

### Phase 3 — Implementation

Spawn the `ui-integrator` agent with this prompt:

```
Implement the {component} component for the LoneUBoat UX redesign.

Design validation: APPROVED
Component: {component}
Flag: {flag_name}
Method to create: _draw_{component}_new()
Call site to wrap: {location in unified_game.py}

Follow the strangler fig protocol in your instructions.
The spec is in .claude/agents/ux-redesign.agent.md Step {N}.
```

**Gate:** If integrator returns blocked or incomplete → report to user, do not run tester.

### Phase 4 — Verification

Spawn the `ui-tester` agent with this prompt:

```
Verify the {component} component implementation for the LoneUBoat UX redesign.

Component: {component}
Expected method: _draw_{component}_new()
Feature flag: {flag_name}
Integrator report: {paste integrator's completion summary}

Run all checks per your verification process.
```

**Gate:**
- GAPS_FOUND → report gaps to user, suggest re-running integrator with the gap details
- HUMAN_NEEDED → report what needs visual verification and how to enable the flag for testing
- PASSED → report success and next steps

---

## Final Report Format

```
## UX Component Complete: {component}

### Pipeline Results
- Design Validation: {APPROVED / BLOCKED}
- Implementation: {COMPLETE / BLOCKED}
- Verification: {PASSED / GAPS_FOUND / HUMAN_NEEDED}

### What Was Built
{2-3 sentence description of what was implemented}

### To Test Visually
1. Open config/board_config.py
2. Set {flag_name} = True
3. Run: python main.py
4. {What to look for}

### To Merge (when visually approved)
The old implementation is preserved. Once satisfied:
- Keep {flag_name} = True permanently
- Old method _draw_{component}() can be removed in a future cleanup commit

### Next Component (suggested)
{Next step in the build order from ux-redesign.agent.md}
```

---

## Error Handling

**If design-validator blocks:**
Report exact blocking issues. Do not run integrator.
Suggest: "Fix the plan and re-run `/orchestrator $ARGUMENTS`"

**If integrator is blocked by architectural change (Rule 4):**
Report the architectural question to the user and wait for a decision before re-running.

**If tester finds gaps:**
Run a brief targeted fix: spawn integrator again with the specific gap description as context.
Limit to one retry — if still failing, escalate to user.

**If context is running low (you see a CONTEXT WARNING):**
Complete the current phase cleanly and report status before context expires.
Do not start a new phase when context is below 35%.
