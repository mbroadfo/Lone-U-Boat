# Documentation Inventory

This file tracks the documentation structure for the Lone U-Boat project.

## Root Documentation

- **README.md** - Project overview and quick start
- **CHANGELOG.md** - Complete change history (all evolution tracked here)
- **RULES.md** - Game rules reference

## docs/ - Current Documentation

### Architecture
- **ARCHITECTURE_BOARD_LAYOUT.md** - Board layout system and hex coordinate system
- **STRANGLER_FIG_INTERACTIVE_AI.md** - Interactive AI architecture (queue-based execution)

### Future Planning
- **FUTURE_IDEAS.md** - Feature wishlist and enhancement proposals

### Archive (docs/archive/)

Historical documentation preserved for reference:

#### archive/sessions/
Work session logs:
- `SESSION_2026_01_26_LOGGING_AND_TORPEDO_FIX.md`
- `SESSION_2026_02_03_UI_POLISH.md`
- `SESSION_2026_02_06_ANIMATIONS_AND_TYPE_HINTS.md`
- `BUG_FIXES_SESSION.md`

#### archive/phases/
Phase completion reports:
- `PHASE_1_AUDIT.md`
- `PHASE_1_SUMMARY.md`
- `PHASE_2_APPROACH.md`
- `PHASE_2_COMPLETION.md`
- `PHASE_4_COMPLETION.md`
- `PHASE_5_EVENT_LOG_CLEANUP.md`

#### archive/implementations/
Implementation documentation:
- `DESTROYED_ENTITY_IMPLEMENTATION.md`
- `VICTORY_DEFEAT_SYSTEM.md`
- `TORPEDO_PREVIEW_FIX.md`
- `ESCORT_AI_TEST_COVERAGE.md`
- `TEST_ANALYSIS.md`

#### archive/
Deprecated tools:
- `ALIGNMENT_MODE_CONTROLS.md` - Editor alignment mode (deprecated)

## Documentation Principles

1. **CHANGELOG.md is the single source of truth for evolution** - All changes tracked chronologically
2. **Current docs state facts as if they were always there** - No planning language, no evolution narrative
3. **Archive preserves history** - Session logs and phase completions for reference only
4. **Keep it lean** - Only document what's needed, when it's needed

---

*Last Updated: February 15, 2026*
**Content:** Mission file format schema
**Relevance:** Current, describes JSON structure
**Action:** None

### ✅ README_METADATA.md
**Status:** KEEP
**Content:** Mission metadata documentation
**Relevance:** Current, describes mission system
**Action:** None

### ✅ EXECUTION_MODEL.md
**Status:** KEEP
**Content:** Mission execution model
**Relevance:** Current, describes game flow
**Action:** None

---

## SUMMARY

**Total Documents:** 33
- ✅ **KEEP (Current):** 8 files
- 📚 **ARCHIVE (Historic):** 17 files
- 🗑️ **DELETE (Obsolete):** 3 files
- 🔄 **CONSOLIDATE:** 1 file (Phase 5 Plan)

**Recommended Actions:**
1. Create docs/archive/ structure (sessions/, phases/, implementations/)
2. Move 17 historic docs to archive
3. Delete 3 obsolete refactor plans
4. Create FUTURE_IDEAS.md consolidating future plans from Phase 5
5. Update docs with cleaner structure

**Archive Structure:**
```
docs/
  archive/
    sessions/          # Bug fix and work sessions
    phases/            # Phase completion reports
    implementations/   # Feature implementation details
  ARCHITECTURE_BOARD_LAYOUT.md  # Current
  FUTURE_IDEAS.md                # New - consolidated future plans
```
