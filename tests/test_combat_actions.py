"""
Tests for Phase 3.3-3.5 - Repair and Combat Actions.

Tests:
- RepairAction with RepairValidator integration
- DeckGunAction with RangeLOSValidator and CombatResolver
- LoadTorpedoAction with TorpedoValidator
- FireTorpedoAction with TorpedoValidator and CombatResolver
"""

import sys
import os
from typing import List, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import actions directly
from core.actions.repair_action import RepairAction
from core.actions.deck_gun_action import DeckGunAction
from core.actions.load_torpedo_action import LoadTorpedoAction
from core.actions.fire_torpedo_action import FireTorpedoAction

# Import models directly
from core.models import UBoat, Ship, HexCoord, Depth, Facing, TubeState

# Import validators and resolvers directly
from core.repair_validator import RepairValidator
from core.los import LOSCalculator
from core.combat_resolver import CombatResolver
from core.torpedo_validator import TorpedoValidator
from core.action_costs import ActionCostLookup
from core.dice import DiceRoller
from missions.mission_rules_loader import load_mission_rules


# Load mission rules for cost lookup
MISSION_RULES = load_mission_rules(1)


class MockGameState:
    """Minimal game state for testing."""
    def __init__(self, u_boat: UBoat, ships: Optional[List[Ship]] = None):
        self.u_boat = u_boat
        self.ships = ships or []
        self.land_hexes = set()
        self.mission_hexes = set()  # Empty set for testing
        self.destroyed_this_phase = []  # Track destroyed entities


def test_repair_action_engine():
    """Test RepairAction for engine."""
    print("\n=== Testing RepairAction - Engine ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        action_points=10,
        engine_damaged=True  # Damaged engine
    )
    
    game_state = MockGameState(u_boat)
    
    action = RepairAction("Engine", cost_lookup, validator)
    
    cost = action.get_cost(u_boat)
    print(f"Repair cost at surface: {cost}")
    assert cost == 2
    
    can_repair, msg = action.validate(game_state)
    print(f"Repair validation: {can_repair}, reason: {msg}")
    assert can_repair, f"Engine repair should be valid: {msg}"
    
    result = action.execute(game_state)
    print(f"Repair result: {result}")
    assert result.success
    assert game_state.u_boat.engine_damaged == False
    assert "Engine" in result.message
    
    print("✅ RepairAction engine tests passed!")


def test_repair_action_torpedoes():
    """Test RepairAction for torpedo tubes."""
    print("\n=== Testing RepairAction - Torpedoes ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        action_points=10,
        torpedo_tubes=[TubeState.LOADED, TubeState.DAMAGED, TubeState.DAMAGED, TubeState.LOADED, TubeState.LOADED]  # 2 damaged
    )
    
    game_state = MockGameState(u_boat)
    
    action = RepairAction("Torpedo Tubes", cost_lookup, validator)
    
    can_repair, _ = action.validate(game_state)
    print(f"Torpedo repair validation: {can_repair}")
    assert can_repair
    
    result = action.execute(game_state)
    print(f"Repair result: {result}")
    assert result.success
    # Repaired tubes should be EMPTY (need to be loaded again)
    assert game_state.u_boat.torpedo_tubes[1] == TubeState.EMPTY
    assert game_state.u_boat.torpedo_tubes[2] == TubeState.EMPTY
    assert "2 torpedo tubes" in result.message
    
    print("✅ RepairAction torpedo tests passed!")


def test_repair_action_submerged_requires_engineer():
    """Test RepairAction requires engineer when submerged."""
    print("\n=== Testing RepairAction - Submerged Requires Engineer ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        action_points=10,
        engine_damaged=True,
        engineer_alive=False  # Engineer KIA
    )
    
    game_state = MockGameState(u_boat)
    
    action = RepairAction("Engine", cost_lookup, validator)
    
    can_repair, msg = action.validate(game_state)
    print(f"Submerged repair without engineer: {can_repair}, reason: {msg}")
    assert not can_repair
    assert "engineer" in msg.lower() or "surface" in msg.lower()
    
    print("✅ RepairAction engineer requirement tests passed!")


def test_deck_gun_action():
    """Test DeckGunAction."""
    print("\n=== Testing DeckGunAction ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    los_calculator = LOSCalculator(land_hexes=set())
    dice_roller = DiceRoller()
    combat_resolver = CombatResolver(dice_roller)
    from core.damage.ship_damage import ShipDamageResolver
    ship_damage = ShipDamageResolver(dice_roller, MISSION_RULES)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        action_points=10,
        deck_gun_damaged=False
    )
    
    target_ship = Ship(
        position=HexCoord(5, 7),  # Range 2
        facing=Facing.NORTH,
        ship_type="merchant"
    )
    
    game_state = MockGameState(u_boat, [target_ship])
    
    # DeckGunAction expects list of (ship, distance) tuples
    action = DeckGunAction([(target_ship, 2)], cost_lookup, los_calculator, combat_resolver, ship_damage)
    
    cost = action.get_cost(u_boat)
    print(f"Deck gun cost: {cost}")
    assert cost == 2
    
    can_fire, msg = action.validate(game_state)
    print(f"Deck gun validation: {can_fire}, reason: {msg}")
    assert can_fire, f"Deck gun should be valid: {msg}"
    
    result = action.execute(game_state)
    print(f"Deck gun result: {result}")
    assert result.success
    assert "deck gun" in result.message.lower()
    
    # Check preview
    preview = action.get_preview_data(game_state)
    print(f"Preview: {preview}")
    assert preview["type"] == "deck_gun"
    assert preview["range"] == 2
    
    print("✅ DeckGunAction tests passed!")


def test_deck_gun_requires_surface():
    """Test DeckGunAction requires surface."""
    print("\n=== Testing DeckGunAction - Surface Required ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    los_calculator = LOSCalculator(land_hexes=set())
    dice_roller = DiceRoller()
    combat_resolver = CombatResolver(dice_roller)
    from core.damage.ship_damage import ShipDamageResolver
    ship_damage = ShipDamageResolver(dice_roller, MISSION_RULES)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,  # Not surfaced
        action_points=10
    )
    
    target_ship = Ship(
        position=HexCoord(5, 7),
        facing=Facing.NORTH,
        ship_type="merchant"
    )
    
    game_state = MockGameState(u_boat, [target_ship])
    
    # DeckGunAction expects list of (ship, distance) tuples
    action = DeckGunAction([(target_ship, 2)], cost_lookup, los_calculator, combat_resolver, ship_damage)
    
    can_fire, msg = action.validate(game_state)
    print(f"Submerged deck gun: {can_fire}, reason: {msg}")
    assert not can_fire
    assert "surface" in msg.lower()
    
    print("✅ DeckGunAction surface requirement tests passed!")


def test_load_torpedo_action():
    """Test LoadTorpedoAction."""
    print("\n=== Testing LoadTorpedoAction ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        action_points=10,
        torpedo_tubes=[TubeState.EMPTY, TubeState.EMPTY, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED]  # 2 empty
    )
    
    game_state = MockGameState(u_boat)
    
    # Load 2 tubes (use 1-based indices: tubes 1 and 2)
    action = LoadTorpedoAction([1, 2], cost_lookup, validator)
    
    cost = action.get_cost(u_boat)
    print(f"Load torpedo cost at surface: {cost}")
    assert cost == 1
    
    can_load, msg = action.validate(game_state)
    print(f"Load validation: {can_load}, reason: {msg}")
    assert can_load, f"Loading should be valid: {msg}"
    
    result = action.execute(game_state)
    print(f"Load result: {result}")
    assert result.success
    assert game_state.u_boat.torpedo_tubes[0] == TubeState.LOADED  # Tube 1 (index 0)
    assert game_state.u_boat.torpedo_tubes[1] == TubeState.LOADED  # Tube 2 (index 1)
    assert "Tube 1" in result.message or "Tube 2" in result.message
    
    print("✅ LoadTorpedoAction tests passed!")


def test_load_torpedo_requires_surface_or_periscope():
    """Test LoadTorpedoAction depth restriction."""
    print("\n=== Testing LoadTorpedoAction - Depth Restriction ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,  # Too deep
        action_points=10,
        torpedo_tubes=[TubeState.EMPTY, TubeState.EMPTY, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED]
    )
    
    game_state = MockGameState(u_boat)
    
    action = LoadTorpedoAction([0, 1], cost_lookup, validator)
    
    can_load, msg = action.validate(game_state)
    print(f"Load at medium depth: {can_load}, reason: {msg}")
    assert not can_load
    assert "surface" in msg.lower() or "periscope" in msg.lower()
    
    print("✅ LoadTorpedoAction depth restriction tests passed!")


def test_fire_torpedo_action():
    """Test FireTorpedoAction."""
    print("\n=== Testing FireTorpedoAction ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = TorpedoValidator()
    los_calculator = LOSCalculator(land_hexes=set())
    dice_roller = DiceRoller()
    combat_resolver = CombatResolver(dice_roller)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        action_points=10,
        torpedo_tubes=[TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED]  # All loaded
    )
    
    target_ship = Ship(
        position=HexCoord(5, 8),  # Range 3
        facing=Facing.NORTH,
        ship_type="destroyer"
    )
    
    game_state = MockGameState(u_boat, [target_ship])
    
    # Fire 2 torpedoes from front tubes (use 1-based: tubes 1 and 2)
    action = FireTorpedoAction(
        tube_indices=[1, 2],
        fire_direction=u_boat.facing,
        cost_lookup=cost_lookup,
        validator=validator,
        los_calculator=los_calculator,
        combat_resolver=combat_resolver
    )
    
    cost = action.get_cost(u_boat)
    print(f"Fire torpedo cost: {cost}")
    assert cost == 2
    
    can_fire, msg = action.validate(game_state)
    print(f"Fire validation: {can_fire}, reason: {msg}")
    assert can_fire, f"Firing should be valid: {msg}"
    
    result = action.execute(game_state)
    print(f"Fire result: {result}")
    assert result.success
    assert "torpedo" in result.message.lower()
    assert game_state.u_boat.torpedo_tubes[0] == TubeState.EMPTY  # Unloaded
    assert game_state.u_boat.torpedo_tubes[1] == TubeState.EMPTY  # Unloaded
    
    # Check preview
    preview = action.get_preview_data(game_state)
    print(f"Preview: {preview}")
    assert preview["type"] == "fire_torpedoes"
    assert preview["torpedo_count"] == 2
    
    print("✅ FireTorpedoAction tests passed!")


def test_fire_torpedo_front_and_rear_restriction():
    """Test FireTorpedoAction front/rear restriction."""
    print("\n=== Testing FireTorpedoAction - Front/Rear Restriction ===")
    
    cost_lookup = ActionCostLookup(MISSION_RULES)
    validator = TorpedoValidator()
    los_calculator = LOSCalculator(land_hexes=set())
    dice_roller = DiceRoller()
    combat_resolver = CombatResolver(dice_roller)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        action_points=10,
        torpedo_tubes=[TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED]
    )
    
    target_ship = Ship(
        position=HexCoord(5, 8),
        facing=Facing.NORTH,
        ship_type="destroyer"
    )
    
    game_state = MockGameState(u_boat, [target_ship])
    
    # Try to fire front and rear tubes (invalid - use tubes 1 and 5)
    action = FireTorpedoAction(
        tube_indices=[1, 5],
        fire_direction=u_boat.facing,
        cost_lookup=cost_lookup,
        validator=validator,
        los_calculator=los_calculator,
        combat_resolver=combat_resolver
    )
    
    can_fire, msg = action.validate(game_state)
    print(f"Front+rear firing: {can_fire}, reason: {msg}")
    assert not can_fire
    assert "front" in msg.lower() or "rear" in msg.lower()
    
    print("✅ FireTorpedoAction front/rear restriction tests passed!")


if __name__ == "__main__":
    print("Phase 3.3-3.5 Tests - Repair and Combat Actions")
    
    test_repair_action_engine()
    test_repair_action_torpedoes()
    test_repair_action_submerged_requires_engineer()
    test_deck_gun_action()
    test_deck_gun_requires_surface()
    test_load_torpedo_action()
    test_load_torpedo_requires_surface_or_periscope()
    test_fire_torpedo_action()
    test_fire_torpedo_front_and_rear_restriction()
    
    print("\n✅ ALL REPAIR AND COMBAT ACTION TESTS PASSED!")
