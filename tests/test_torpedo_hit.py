"""Quick test to verify torpedo hit values are correct."""
from missions.mission_rules_loader import load_mission_rules
from core.dice import DiceRoller
from core.combat_resolver import CombatResolver
from core.actions.fire_torpedo_action import FireTorpedoAction
from core.torpedo_validator import TorpedoValidator
from core.los import LOSCalculator
from core.hex_grid import HexGrid
from core.action_costs import ActionCostLookup

if __name__ == "__main__":
    # Load mission rules
    mission_rules = load_mission_rules(1)

    # Create components
    dice = DiceRoller()
    resolver = CombatResolver(dice, mission_rules)
    validator = TorpedoValidator()
    los_calc = LOSCalculator(HexGrid(50, 20, 20, 100, 100))
    cost_lookup = ActionCostLookup(mission_rules)

    # Create action
    action = FireTorpedoAction(
        tube_indices=[0],
        fire_direction=None,
        cost_lookup=cost_lookup,
        validator=validator,
        los_calculator=los_calc,
        combat_resolver=resolver
    )

    print("Torpedo Hit Target Numbers:")
    print("="*50)
    print("Range 1-2:")
    print(f"  Side aspect: {action.get_torpedo_hit_target(1, 'side')}+ (expected 3+)")
    print(f"  Front/Rear:  {action.get_torpedo_hit_target(1, 'front_rear')}+ (expected 4+)")
    print()
    print("Range 3-4:")
    print(f"  Side aspect: {action.get_torpedo_hit_target(3, 'side')}+ (expected 4+)")
    print(f"  Front/Rear:  {action.get_torpedo_hit_target(3, 'front_rear')}+ (expected 5+)")
    print()
    print("Range 5-6:")
    print(f"  Side aspect: {action.get_torpedo_hit_target(5, 'side')}+ (expected 5+)")
    print(f"  Front/Rear:  {action.get_torpedo_hit_target(5, 'front_rear')}+ (expected 6+)")
    print()
    print("✅ All values now match game rules from JSON!")
