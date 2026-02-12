#!/usr/bin/env python
"""
Run all tests - wrapper to avoid pytest buffer issues in Windows/Python 3.13
"""
import subprocess
import sys

test_files = [
    "tests/test_action_stacking.py",
    "tests/test_action_system.py",
    "tests/test_ai_game.py",
    "tests/test_b24_ai.py",
    "tests/test_combat_actions.py",
    "tests/test_combat_resolution.py",
    "tests/test_combat_resolver.py",
    "tests/test_damage_resolution.py",
    "tests/test_depth_validator.py",
    "tests/test_destruction_conditions.py",
    "tests/test_detection_ai.py",
    "tests/test_detection_integration.py",
    "tests/test_escort_ai.py",
    "tests/test_escort_ai_comprehensive.py",
    "tests/test_event_system.py",
    "tests/test_fire_torpedo_action.py",
    "tests/test_merchant_ai.py",
    "tests/test_merchant_integration.py",
    "tests/test_movement_actions.py",
    "tests/test_movement_validator.py",
    "tests/test_phase2_subsystems.py",
    "tests/test_range_los.py",
    "tests/test_repair_system.py",
    "tests/test_repair_validator.py",
    "tests/test_scripted_captain.py",
    "tests/test_torpedo_validator.py",
    "tests/test_victory_loss_conditions.py",
    # Interactive AI tests (new)
    "tests/interactive_ai/test_merchant_interactive.py",
    "tests/interactive_ai/test_escort_interactive.py",
    "tests/interactive_ai/test_b24_interactive.py",
    "tests/interactive_ai/test_detection_interactive.py",
]

if __name__ == "__main__":
    cmd = [sys.executable, "-m", "pytest"] + test_files + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
