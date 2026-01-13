# Repository Reorganization - January 13, 2026

## Overview

This document tracks the repository reorganization performed to improve code structure and separate documentation concerns.

## Changes Made

### 1. Test Files Moved to Proper Locations

**Moved to `tests/scenarios/`:**
- `test_deck_gun_scenario.py` → `tests/scenarios/test_deck_gun_scenario.py`
- `test_torpedo_scenario.py` → `tests/scenarios/test_torpedo_scenario.py`
- `test_output.txt` → `tests/scenarios/test_output.txt`

**Rationale:** These are integration test scenarios, not unit tests. They test full gameplay flows and belong in a dedicated scenarios subfolder.

### 2. Utility Scripts Moved to `utils/`

**Moved to `utils/`:**
- `editor.py` → `utils/editor.py` (deprecated, kept for reference)
- `extract_maps.py` → `utils/extract_maps.py`

**Rationale:** These are development utilities, not core game code. Separating them keeps the root directory clean.

### 3. Development Documentation Moved to `docs/`

**Moved to `docs/`:**
- `ALIGNMENT_MODE_CONTROLS.md` → `docs/ALIGNMENT_MODE_CONTROLS.md`
- `ARCHITECTURE_BOARD_LAYOUT.md` → `docs/ARCHITECTURE_BOARD_LAYOUT.md`
- `REFACTOR_PLAN_RULES_REDUNDANCY.md` → `docs/REFACTOR_PLAN_RULES_REDUNDANCY.md`
- `PHASE_1_AUDIT.md` → `docs/PHASE_1_AUDIT.md`
- `PHASE_5_PLAN.md` → `docs/PHASE_5_PLAN.md`

**Rationale:** These are completed development documents and internal architecture notes. Moving them to `docs/` keeps the root directory focused on user-facing documentation.

### 4. Root Directory Cleanup

**Files Remaining in Root (User-Facing):**
- `README.md` - Main project documentation
- `RULES.md` - Player-facing game rules reference
- `main.py` - Game entry point

**Benefits:**
- Cleaner root directory
- Clear separation between user documentation and developer documentation
- Easier to find relevant files
- Better organization for newcomers to the project

## Updated README Structure

The README was completely rewritten to:

1. **Clarify Architecture:**
   - Added comprehensive architecture overview
   - Explained code vs. configuration separation
   - Documented JSON-driven rules engine
   - Showed configuration flow diagrams

2. **Document JSON Rules System:**
   - Explained relationship between JSON files and Python code
   - Documented rule loading mechanism
   - Provided example of rules parsing
   - Clarified mission-specific vs. baseline rules

3. **Improve Navigation:**
   - Added clear project structure tree
   - Linked to relevant documentation files in `docs/`
   - Organized sections logically (Quick Start → Architecture → Testing → Utilities)
   - Added table of contents through clear headings

4. **Update Status:**
   - Reflected current phase progress (Phase 4 in progress)
   - Updated test count (225+ tests)
   - Noted JSON refactoring completion
   - Removed obsolete development plans

## Documentation Strategy Going Forward

### Root Directory (User-Facing)
- `README.md` - Getting started, architecture overview, quick reference
- `RULES.md` - Player-facing game rules

### `docs/` (Developer-Facing)
- Architecture documentation
- Completed phase audits
- Design decisions and planning documents
- Internal technical documentation

### `missions/` (Configuration Documentation)
- `mission_schema.md` - JSON format reference
- `README_METADATA.md` - Mission system guide
- `EXECUTION_MODEL.md` - AI execution model

### `tests/` (Test Documentation)
- `tests/README.md` - Test suite overview and guidelines

## File Location Quick Reference

| File Type | Location | Examples |
|-----------|----------|----------|
| User Documentation | Root | README.md, RULES.md |
| Developer Documentation | docs/ | ARCHITECTURE_BOARD_LAYOUT.md, PHASE_1_AUDIT.md |
| Configuration Docs | missions/ | mission_schema.md, README_METADATA.md |
| Test Documentation | tests/ | tests/README.md |
| Utility Scripts | utils/ | editor.py, extract_maps.py |
| Test Scenarios | tests/scenarios/ | test_deck_gun_scenario.py |

## Breaking Changes

None. All documentation links were updated in README.md. All imports and paths remain functional.

## Next Steps

- [ ] Review and consolidate remaining markdown files in missions/
- [ ] Consider moving RULES.md examples to a dedicated examples/ folder
- [ ] Add architectural decision records (ADRs) to docs/ as decisions are made
- [ ] Update contributor guide once collaboration opens
