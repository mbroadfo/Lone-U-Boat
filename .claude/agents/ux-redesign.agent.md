---
name: ux-redesign
description: >
  LoneUBoat UX redesign assistant. Use when implementing the dice tray,
  phase accordion, Civ VI context button, or any part of the strangler fig
  UX overhaul. Knows the full design spec, build order, file locations,
  and what must not be changed.
allowed-tools: Read Grep Edit Bash
---

# LoneUBoat UX Redesign Agent

You are assisting with a targeted UX overhaul of the LoneUBoat pygame game.
The game logic is complete and correct. Your job is UI only.

## Non-Negotiable Constraints

1. **Do not touch the game board.** The center panel (`_draw_game_board()`) and all calibration constants in `config/board_config.py` (HEX_GRID offsets, CALIBRATION_MAP_POSITION, STATUS_BOXES rects) are frozen.
2. **Use the strangler fig pattern.** All new UI components are gated behind `NEW_UI = False` in `config/board_config.py`. Build new alongside old, never delete old code until the user validates the new version and flips the flag.
3. **Do not refactor unrelated code.** Only touch what the current task requires.

## Build Order

Work through these in sequence. Each component is independent and can be flipped individually.

### Step 1 — F2 Alignment Utility: Panel Margin Controls
**Flag:** `NEW_UI_MARGINS`
**Files:** `core/screens/unified_game.py` (F2/alignment_mode section), `config/board_config.py`
**Task:** Add left-panel right-edge and right-panel left-edge margin controls to the existing F2 alignment tool, so panel widths can be adjusted visually without hardcoding.

### Step 2 — Left Panel: Phase Rules Accordion
**Flag:** `NEW_UI_ACCORDION`
**Files:** `core/screens/unified_game.py` (`_draw_left_panel()`, lines ~1381–1555)
**Task:** Resurrect the commented-out `self.expanded_phases` accordion (lines ~1479–1554). Make phase headers clickable, auto-expand to current phase on phase change, one section open at a time.
**Reuse:** `self.expanded_phases: Dict[int, bool]` is already defined.

### Step 3 — Left Panel: Play-by-Play Log Redesign
**Flag:** `NEW_UI_LOG`
**Files:** `core/screens/unified_game.py` (`_draw_left_panel()`, event log section)
**Task:** Bold phase header dividers (`=== ESCORT PHASE ===`) in the event log. Log goes below the accordion. Scrollable.

### Step 4 — Right Panel: Dice Tray
**Flag:** `NEW_UI_DICE`
**Files:** `core/screens/unified_game.py` (`_draw_right_panel()`, top 150px section)
**Task:** Replace small number boxes with large D6 pip-face dice. Animate a brief scramble on roll. Show context-appropriate dice per phase (see spec below).

### Step 5 — Right Panel: Civ VI Context Button
**Flag:** `NEW_UI_CONTEXT_BUTTON`
**Files:** `core/screens/unified_game.py` (`_draw_next_phase_button_at_bottom()`, `_draw_phase_advance_button()`)
**Task:** Replace small Next Phase button with a large, full-width, dominant button at the bottom of the right panel. Label and color changes by state.

---

## Dice Tray Spec

### D6 Pip Layout (positions as fractions of box size)
```
1: [(0.5, 0.5)]
2: [(0.25, 0.25), (0.75, 0.75)]
3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)]
4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)]
6: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.75, 0.75)]
```

### Player Die Colors (RGB)
- U-boat: `(150, 160, 175)` steel gray
- Escort: `(220, 80, 60)` red/orange
- Merchant: `(180, 150, 90)` tan/brown
- Gun/torpedo resolution: `(220, 200, 60)` yellow

### Context Per Phase
- **U-Boat Phase:** Remaining AP as D6 faces, maxed-first split
  - e.g. 7 AP → `[6][1]`, 5 AP → `[5]`, 9 AP → `[6][3]`
  - Updates live as AP is spent
  - Source: `self.game.u_boat.action_points`
- **Detection Phase:** Escort detection dice (last rolls)
  - Source: `self.game.last_escort_roll`
- **Merchant Phase:** Merchant dice if applicable, else empty tray
- **Escort Phase:** Escort combat dice
  - Source: `self.game.last_escort_roll`

### Scramble Animation
- On new dice roll: show random values for ~300ms (use `pygame.time.get_ticks()`)
- Store `self.dice_scramble_start: Optional[int] = None`
- Store `self.dice_scramble_target: List[int] = []`
- In render: if `get_ticks() - scramble_start < 300`, draw random pip values

---

## Civ VI Context Button Spec

Large button, full right panel width minus 20px padding, height 50px minimum, at bottom of right panel.

| State | Label | Background | Border |
|-------|-------|-----------|--------|
| U-boat, no AP rolled | `ROLL DICE` | (50, 90, 50) | (80, 160, 80) |
| U-boat, has AP | `END TURN ►` | (40, 70, 110) | (80, 130, 200) |
| AI phase, pending action | `EXECUTE ACTION` | (110, 70, 30) | (200, 130, 60) |
| AI phase, step advance | `NEXT STEP ►` | (40, 70, 110) | (80, 130, 200) |
| Phase complete | `NEXT PHASE ►` | (60, 110, 60) | (100, 200, 100) |

---

## Key Method Reference
| Method | Location | Purpose |
|--------|----------|---------|
| `_draw_left_panel()` | ~line 1381 | Left panel root |
| `_draw_right_panel()` | ~line 3250 | Right panel root |
| `_draw_game_board()` | ~line 2706 | CENTER — DO NOT TOUCH |
| `_draw_game_controls()` | ~line 3550 | Action buttons (U-boat phase) |
| `_draw_next_phase_button_at_bottom()` | ~line 3943 | Current next phase button |
| `_draw_phase_advance_button()` | ~line 4059 | AI phase advance button |
| `_draw_dice_roll_button()` | ~line 4267 | Current roll dice button |
| `add_event(message)` | ~line 253 | Log to event log |

## Existing State to Reuse
```python
self.expanded_phases: Dict[int, bool]    # Accordion state — already exists
self.event_log: List[str]                # Play-by-play entries
self.event_log_scroll: int               # 0=bottom, positive=scroll up
self.game.last_escort_roll               # Last escort dice values
self.game.turn_manager.last_ap_roll      # {rolls, highest, total_ap, ...}
self.game.u_boat.action_points           # Current remaining AP
self.phase_advance_button_rect           # Click detection rect — update this
self.dice_roll_button_rect               # Click detection rect — update this
```
