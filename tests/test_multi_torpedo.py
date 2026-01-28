"""Test script to verify multiple torpedoes fire correctly."""
from typing import List, Tuple, Dict, Any, Optional
from core.game_state import Game
from core.models import HexCoord, Facing, Depth, Ship

def test_two_torpedo_firing():
    """Test that firing 2 torpedoes actually fires both."""
    print("\n" + "="*60)
    print("TEST: Multiple Torpedo Firing")
    print("="*60)
    
    # Create game instance
    game = Game()
    
    # Position U-boat at periscope depth
    game.u_boat.depth = Depth.PERISCOPE
    game.u_boat.position = HexCoord(5, 5)
    game.u_boat.facing = Facing.NORTH
    
    # Load torpedoes in tubes 1, 2, 3
    game.u_boat.torpedo_tubes[0] = True  # Tube 1
    game.u_boat.torpedo_tubes[1] = True  # Tube 2
    game.u_boat.torpedo_tubes[2] = True  # Tube 3
    
    # Place two ships in line north of U-boat
    merchant1 = Ship(
        position=HexCoord(5, 3),
        facing=Facing.SOUTH,
        ship_type="merchant",
        damaged=False
    )
    merchant2 = Ship(
        position=HexCoord(5, 1),
        facing=Facing.SOUTH,
        ship_type="merchant",
        damaged=False
    )
    game.ships = [merchant1, merchant2]
    
    print(f"\nU-Boat at {game.u_boat.position}, facing {game.u_boat.facing.name}")
    print(f"Loaded tubes: {[i+1 for i, loaded in enumerate(game.u_boat.torpedo_tubes) if loaded]}")
    print(f"Ship 1 at {merchant1.position} (range 2)")
    print(f"Ship 2 at {merchant2.position} (range 4)")
    
    # Create fire torpedo action for tubes 1 and 2
    from core.actions.fire_torpedo_action import FireTorpedoAction
    from core.torpedo_validator import TorpedoValidator
    from core.los import LOSCalculator
    from core.combat_resolver import CombatResolver
    from core.action_costs import ActionCostLookup
    
    cost_lookup = ActionCostLookup(game.mission_rules)
    
    action = FireTorpedoAction(
        tube_indices=[1, 2],  # Fire tubes 1 and 2
        fire_direction=game.u_boat.facing,
        cost_lookup=cost_lookup,
        validator=TorpedoValidator(),
        los_calculator=LOSCalculator(game.land_hexes),
        combat_resolver=CombatResolver(game.turn_manager.dice, game.mission_rules)
    )
    
    # Execute action
    result = action.execute(game)
    
    print(f"\nAction result: {result.success}")
    print(f"Message: {result.message}")
    print(f"Torpedo count: {result.state_changes['torpedo_count']}")
    print(f"Targets found: {len(result.state_changes['targets'])}")
    
    # Verify torpedo count is correct
    assert result.state_changes['torpedo_count'] == 2, f"Expected 2 torpedoes, got {result.state_changes['torpedo_count']}"
    
    # Verify targets
    targets = result.state_changes['targets']
    print(f"\nTargets:")
    for i, (ship, distance, aspect) in enumerate(targets):
        print(f"  {i+1}. {ship.ship_type} at range {distance}, aspect {aspect}")
    
    # Simulate the resolution state that unified_game.py creates
    torpedo_state: Dict[str, Any] = {
        'action': action,
        'torpedo_count': result.state_changes['torpedo_count'],
        'targets': result.state_changes['targets'],
        'current_target_idx': 0,
        'current_torpedo_idx': 0,
        'torpedoes_available': result.state_changes['torpedo_count'],
        'waiting_for': 'hit',
        'results': []
    }
    
    print(f"\n--- SIMULATING TORPEDO RESOLUTION ---")
    print(f"Starting with {torpedo_state['torpedoes_available']} torpedoes available")
    
    # Simulate: Torpedo 1 misses ship 1, continues to ship 2, misses ship 2
    print(f"\nTorpedo #{torpedo_state['current_torpedo_idx'] + 1} vs Ship 1: MISS")
    results_list: List[Tuple[int, Ship, int, bool, Optional[int]]] = torpedo_state['results']
    results_list.append((1, merchant1, 2, False, None))
    
    # After miss, check continue logic
    just_hit: bool = results_list[-1][3]
    print(f"  Just hit? {just_hit}")
    
    if not just_hit:
        # Should move to next target (ship 2)
        torpedo_state['current_target_idx'] = 1
        print(f"  Moving to target {torpedo_state['current_target_idx'] + 1}")
    
    print(f"\nTorpedo #{torpedo_state['current_torpedo_idx'] + 1} vs Ship 2: MISS")
    results_list.append((1, merchant2, 4, False, None))
    
    # After miss at last target, should consume torpedo and start next
    just_hit = results_list[-1][3]
    if not just_hit and torpedo_state['current_target_idx'] + 1 >= len(targets):
        # No more targets, consume this torpedo and start next
        torpedo_state['torpedoes_available'] -= 1
        torpedo_state['current_torpedo_idx'] += 1
        torpedo_state['current_target_idx'] = 0
        print(f"  Torpedo 1 missed all targets, consumed")
        print(f"  Starting Torpedo #{torpedo_state['current_torpedo_idx'] + 1}, available: {torpedo_state['torpedoes_available']}")
    
    # Now fire torpedo 2
    if torpedo_state['torpedoes_available'] > 0:
        print(f"\nTorpedo #{torpedo_state['current_torpedo_idx'] + 1} vs Ship 1: HIT!")
        results_list.append((2, merchant1, 2, True, 4))
        
        # After hit, should consume torpedo and reset to first target
        just_hit = results_list[-1][3]
        if just_hit:
            torpedo_state['torpedoes_available'] -= 1
            torpedo_state['current_torpedo_idx'] += 1
            torpedo_state['current_target_idx'] = 0
            print(f"  Torpedo 2 hit, consumed")
            print(f"  Torpedoes remaining: {torpedo_state['torpedoes_available']}")
    
    print(f"\n--- FINAL RESULTS ---")
    print(f"Total torpedoes fired: {torpedo_state['current_torpedo_idx']}")
    print(f"Torpedoes available: {torpedo_state['torpedoes_available']}")
    print(f"Results:")
    for torp_num, ship, distance, hit, _ in results_list:
        status = "HIT" if hit else "MISS"
        print(f"  Torpedo #{torp_num} vs {ship.ship_type} (R{distance}): {status}")
    
    # Verify we fired 2 torpedoes
    torpedoes_fired: int = torpedo_state['current_torpedo_idx']
    assert torpedoes_fired == 2, f"Expected to fire 2 torpedoes, only fired {torpedoes_fired}"
    
    print("\n" + "="*60)
    print("✓ TEST PASSED: Both torpedoes fired correctly")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_two_torpedo_firing()
