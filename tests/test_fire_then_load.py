"""
Test script to verify fire-then-load torpedo functionality in the same turn.
This tests the preview state simulation in action_queue.py
"""

from core.models import Depth, TubeState, Facing
from core.actions.fire_torpedo_action import FireTorpedoAction
from core.actions.load_torpedo_action import LoadTorpedoAction
from core.actions.action_queue import ActionQueue
from core.torpedo_validator import TorpedoValidator
from core.action_costs import ActionCostLookup
from core.los import LOSCalculator
from core.combat_resolver import CombatResolver
from core.dice import DiceRoller
from missions.mission_rules_loader import load_mission_rules
from types import SimpleNamespace

if __name__ == "__main__":
    print("=" * 60)
    print("TEST: Fire Torpedoes Then Load in Same Turn")
    print("=" * 60)

    # Create minimal game state with mocked components
    u_boat = SimpleNamespace(
        torpedo_tubes=[TubeState.LOADED] * 5,
        depth=Depth.SURFACED,
        action_points=10,
        position=None,
        facing=Facing.NORTH,
        damaged_components=set(),
        has_engineer=False,
        weapons_officer_alive=True,
        torpedo_count=20  # Plenty of torpedoes in storage
    )

    mission_rules = load_mission_rules(1)
    dice = DiceRoller()
    game_state = SimpleNamespace(
        u_boat=u_boat,
        ships=[],
        hex_grid=None,
        board_layout=None,
        turn_manager=SimpleNamespace(dice=dice, current_phase="test")
    )

    print("\n1. INITIAL STATE:")
    print(f"   Torpedo tubes: {[state.name for state in u_boat.torpedo_tubes]}")
    print(f"   AP: {u_boat.action_points}")

    # Create action queue
    action_queue = ActionQueue()

    # Create dependencies for actions
    cost_lookup = ActionCostLookup(mission_rules)
    validator = TorpedoValidator()
    los_calc = LOSCalculator(set())  # Mock with empty land hexes
    combat_resolver = CombatResolver(dice, mission_rules)

    # Queue fire torpedoes action
    print("\n2. QUEUEING: Fire Tubes 1, 2, 3")
    fire_action = FireTorpedoAction(
        tube_indices=[1, 2, 3],
        fire_direction=Facing.NORTH,
        cost_lookup=cost_lookup,
        validator=validator,
        los_calculator=los_calc,
        combat_resolver=combat_resolver
    )

    success, msg = action_queue.add_action(fire_action, game_state)
    print(f"   Result: {msg}")
    print(f"   Success: {success}")
    print(f"   Queue now has: {len(action_queue.actions)} actions")
    print(f"   Tubes still show: {[state.name for state in u_boat.torpedo_tubes]} (not executed yet)")

    # Try to queue load torpedoes (should work now with preview state)
    print("\n3. QUEUEING: Load Tubes 1, 2")
    load_action = LoadTorpedoAction(
        tube_indices=[1, 2],
        cost_lookup=cost_lookup,
        validator=validator
    )

    success2, msg2 = action_queue.add_action(load_action, game_state)
    print(f"   Result: {msg2}")
    print(f"   Success: {success2}")

    if success2:
        print("\n   ✓ SUCCESS! Can queue load after fire in same turn!")
        print("   This confirms the preview state simulation is working!")
    else:
        print(f"\n   ✗ FAILED: {msg2}")
        print("   The preview state simulation may not be working correctly.")

    print(f"\n   Queue now has: {len(action_queue.actions)} actions")
    print(f"   Tubes still show: {[state.name for state in u_boat.torpedo_tubes]} (until execution)")

    print("\n" + "=" * 60)
    if success2:
        print("✓ TEST PASSED: Fire-then-load preview validation works!")
        print("\nThe fix allows you to:")
        print("  1. Queue 'Fire Torpedoes' (tubes stay LOADED until execution)")
        print("  2. Queue 'Load Torpedoes' (validator sees preview state with tubes EMPTY)")
        print("  3. Both actions execute in order when you commit the queue")
    else:
        print("✗ TEST FAILED: Cannot queue load after fire")
    print("=" * 60)
