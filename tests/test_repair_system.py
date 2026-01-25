"""
Comprehensive tests for the repair system.

Tests repair functionality including:
- Surface repairs for all components
- Submerged repairs with engineer alive
- Submerged repairs blocked without engineer
- Deck Gun and Flak Gun surface-only restrictions
- Torpedo tube repairs
- AP cost changes with depth
- Hull damage not repairable
"""

import pytest
from core.models import UBoat, HexCoord, Facing, Depth, TubeState
from core.repair_validator import RepairValidator
from core.actions.repair_action import RepairAction
from core.action_costs import ActionCostLookup
from core.game_state import Game


class TestRepairValidator:
    """Test the RepairValidator rules."""
    
    def setup_method(self):
        """Create a basic U-boat for testing."""
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=Depth.SURFACED
        )
        self.validator = RepairValidator()
    
    def test_surface_repair_all_components(self):
        """Test that all components can be repaired when surfaced."""
        # Damage all components
        self.u_boat.engine_damaged = True
        self.u_boat.deck_gun_damaged = True
        self.u_boat.flak_gun_damaged = True
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.engineer_alive = True
        self.u_boat.depth = Depth.SURFACED
        
        # All should be repairable at surface
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Engine")
        assert can_repair, "Engine should be repairable at surface"
        
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Deck Gun")
        assert can_repair, "Deck Gun should be repairable at surface"
        
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Flak Gun")
        assert can_repair, "Flak Gun should be repairable at surface"
        
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert can_repair, "Torpedo Tubes should be repairable at surface"
    
    def test_submerged_repair_with_engineer(self):
        """Test that engine and torpedo tubes can be repaired submerged with engineer alive."""
        self.u_boat.engine_damaged = True
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.engineer_alive = True
        self.u_boat.depth = Depth.PERISCOPE
        
        # Engine and torpedoes should be repairable submerged with engineer
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Engine")
        assert can_repair, "Engine should be repairable submerged with engineer"
        
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert can_repair, "Torpedo Tubes should be repairable submerged with engineer"
    
    def test_submerged_repair_blocked_without_engineer(self):
        """Test that submerged repairs are blocked when engineer is KIA."""
        self.u_boat.engine_damaged = True
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.engineer_alive = False  # Engineer KIA
        self.u_boat.depth = Depth.PERISCOPE
        
        # Engine repair should be blocked without engineer
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Engine")
        assert not can_repair, "Engine repair should be blocked submerged without engineer"
        assert "Engineer" in reason, "Reason should mention Engineer requirement"
        
        # Torpedo repair should also be blocked
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert not can_repair, "Torpedo repair should be blocked submerged without engineer"
        assert "Engineer" in reason, "Reason should mention Engineer requirement"
    
    def test_deck_gun_surface_only(self):
        """Test that Deck Gun can only be repaired when surfaced."""
        self.u_boat.deck_gun_damaged = True
        self.u_boat.engineer_alive = True
        
        # At surface - should be repairable
        self.u_boat.depth = Depth.SURFACED
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Deck Gun")
        assert can_repair, "Deck Gun should be repairable at surface"
        
        # At periscope depth - should be blocked
        self.u_boat.depth = Depth.PERISCOPE
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Deck Gun")
        assert not can_repair, "Deck Gun should not be repairable at periscope depth"
        assert "Surfaced" in reason, "Reason should mention surface requirement"
        
        # At medium depth - should be blocked
        self.u_boat.depth = Depth.MEDIUM
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Deck Gun")
        assert not can_repair, "Deck Gun should not be repairable at medium depth"
        assert "Surfaced" in reason, "Reason should mention surface requirement"
        
        # At deep depth - should be blocked
        self.u_boat.depth = Depth.DEEP
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Deck Gun")
        assert not can_repair, "Deck Gun should not be repairable at deep depth"
        assert "Surfaced" in reason, "Reason should mention surface requirement"
    
    def test_flak_gun_surface_only(self):
        """Test that Flak Gun can only be repaired when surfaced."""
        self.u_boat.flak_gun_damaged = True
        self.u_boat.engineer_alive = True
        
        # At surface - should be repairable
        self.u_boat.depth = Depth.SURFACED
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Flak Gun")
        assert can_repair, "Flak Gun should be repairable at surface"
        
        # At periscope depth - should be blocked
        self.u_boat.depth = Depth.PERISCOPE
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Flak Gun")
        assert not can_repair, "Flak Gun should not be repairable at periscope depth"
        assert "Surfaced" in reason, "Reason should mention surface requirement"
    
    def test_torpedo_tube_repairs(self):
        """Test torpedo tube repair detection and repair limits."""
        # Damage multiple tubes
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.torpedo_tubes[1] = TubeState.DAMAGED
        self.u_boat.torpedo_tubes[2] = TubeState.DAMAGED
        self.u_boat.depth = Depth.SURFACED
        
        # Should detect damaged tubes
        damaged_tubes = self.validator.get_damaged_torpedo_tubes(self.u_boat)
        assert len(damaged_tubes) == 3, "Should detect 3 damaged tubes"
        assert 1 in damaged_tubes and 2 in damaged_tubes and 3 in damaged_tubes
        
        # Should be repairable
        can_repair, _ = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert can_repair, "Damaged torpedo tubes should be repairable"
    
    def test_torpedo_tube_not_damaged(self):
        """Test that empty/loaded torpedo tubes are not considered damaged."""
        # All tubes loaded
        self.u_boat.torpedo_tubes = [TubeState.LOADED] * 5
        
        # Should not be repairable
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert not can_repair, "Loaded tubes should not need repair"
        assert "not damaged" in reason, "Reason should mention tubes are not damaged"
        
        # All tubes empty
        self.u_boat.torpedo_tubes = [TubeState.EMPTY] * 5
        
        # Should not be repairable
        can_repair, reason = self.validator.can_repair_component(self.u_boat, "Torpedo Tubes")
        assert not can_repair, "Empty tubes should not need repair"
        assert "not damaged" in reason, "Reason should mention tubes are not damaged"
    
    def test_ap_cost_surface(self):
        """Test that surface repairs cost 2 AP."""
        cost = self.validator.get_repair_ap_cost("Engine", Depth.SURFACED, engineer_alive=True)
        assert cost == 2, "Surface repair should cost 2 AP"
        
        cost = self.validator.get_repair_ap_cost("Deck Gun", Depth.SURFACED, engineer_alive=True)
        assert cost == 2, "Deck Gun repair at surface should cost 2 AP"
        
        cost = self.validator.get_repair_ap_cost("Torpedo Tubes", Depth.SURFACED, engineer_alive=True)
        assert cost == 2, "Torpedo repair at surface should cost 2 AP"
    
    def test_ap_cost_submerged_with_engineer(self):
        """Test that submerged repairs cost 4 AP with engineer alive."""
        cost = self.validator.get_repair_ap_cost("Engine", Depth.PERISCOPE, engineer_alive=True)
        assert cost == 4, "Submerged repair with engineer should cost 4 AP"
        
        cost = self.validator.get_repair_ap_cost("Torpedo Tubes", Depth.MEDIUM, engineer_alive=True)
        assert cost == 4, "Submerged torpedo repair with engineer should cost 4 AP"
    
    def test_ap_cost_submerged_without_engineer(self):
        """Test that submerged repairs are impossible without engineer (0 AP = can't do)."""
        cost = self.validator.get_repair_ap_cost("Engine", Depth.PERISCOPE, engineer_alive=False)
        assert cost == 0, "Submerged repair without engineer should return 0 (impossible)"
        
        cost = self.validator.get_repair_ap_cost("Torpedo Tubes", Depth.DEEP, engineer_alive=False)
        assert cost == 0, "Submerged torpedo repair without engineer should return 0 (impossible)"
    
    def test_ap_cost_changes_with_depth(self):
        """Test that AP cost changes when depth changes."""
        # Surface: 2 AP
        cost_surface = self.validator.get_repair_ap_cost("Engine", Depth.SURFACED, engineer_alive=True)
        assert cost_surface == 2
        
        # Periscope: 4 AP (with engineer)
        cost_periscope = self.validator.get_repair_ap_cost("Engine", Depth.PERISCOPE, engineer_alive=True)
        assert cost_periscope == 4
        
        # Cost changed
        assert cost_periscope > cost_surface, "Submerged repair should cost more than surface repair"
    
    def test_get_repairable_components(self):
        """Test getting list of all currently repairable components."""
        # Damage multiple components
        self.u_boat.engine_damaged = True
        self.u_boat.deck_gun_damaged = True
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.depth = Depth.SURFACED
        self.u_boat.engineer_alive = True
        
        repairable = self.validator.get_repairable_components(self.u_boat)
        assert "Engine" in repairable
        assert "Deck Gun" in repairable
        assert "Torpedo Tubes" in repairable
        assert len(repairable) == 3
    
    def test_get_repairable_components_submerged(self):
        """Test repairable components list changes when submerged."""
        # Damage all components
        self.u_boat.engine_damaged = True
        self.u_boat.deck_gun_damaged = True
        self.u_boat.flak_gun_damaged = True
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.depth = Depth.PERISCOPE
        self.u_boat.engineer_alive = True
        
        repairable = self.validator.get_repairable_components(self.u_boat)
        
        # Only Engine and Torpedo Tubes should be repairable submerged
        assert "Engine" in repairable
        assert "Torpedo Tubes" in repairable
        assert "Deck Gun" not in repairable, "Deck Gun should not be repairable submerged"
        assert "Flak Gun" not in repairable, "Flak Gun should not be repairable submerged"


class TestRepairAction:
    """Test the RepairAction execution."""
    
    def setup_method(self):
        """Set up a game for testing."""
        self.game = Game(mission_number=1)
        self.u_boat = self.game.u_boat
        self.validator = RepairValidator()
        self.cost_lookup = ActionCostLookup(self.game.mission_rules)
    
    def test_repair_engine(self):
        """Test repairing the engine."""
        self.u_boat.engine_damaged = True
        self.u_boat.depth = Depth.SURFACED
        
        action = RepairAction("Engine", self.cost_lookup, self.validator)
        result = action.execute(self.game)
        
        assert result.success, "Engine repair should succeed"
        assert not self.u_boat.engine_damaged, "Engine should no longer be damaged"
        assert result.ap_spent == 2, "Surface repair should cost 2 AP"
    
    def test_repair_deck_gun(self):
        """Test repairing the deck gun."""
        self.u_boat.deck_gun_damaged = True
        self.u_boat.depth = Depth.SURFACED
        
        action = RepairAction("Deck Gun", self.cost_lookup, self.validator)
        result = action.execute(self.game)
        
        assert result.success, "Deck Gun repair should succeed"
        assert not self.u_boat.deck_gun_damaged, "Deck Gun should no longer be damaged"
        assert result.ap_spent == 2, "Surface repair should cost 2 AP"
    
    def test_repair_flak_gun(self):
        """Test repairing the flak gun."""
        self.u_boat.flak_gun_damaged = True
        self.u_boat.depth = Depth.SURFACED
        
        action = RepairAction("Flak Gun", self.cost_lookup, self.validator)
        result = action.execute(self.game)
        
        assert result.success, "Flak Gun repair should succeed"
        assert not self.u_boat.flak_gun_damaged, "Flak Gun should no longer be damaged"
        assert result.ap_spent == 2, "Surface repair should cost 2 AP"
    
    def test_repair_torpedo_tubes(self):
        """Test repairing torpedo tubes (up to 2 at once)."""
        # Damage 3 tubes
        self.u_boat.torpedo_tubes[0] = TubeState.DAMAGED
        self.u_boat.torpedo_tubes[1] = TubeState.DAMAGED
        self.u_boat.torpedo_tubes[2] = TubeState.DAMAGED
        self.u_boat.depth = Depth.SURFACED
        
        action = RepairAction("Torpedo Tubes", self.cost_lookup, self.validator)
        result = action.execute(self.game)
        
        assert result.success, "Torpedo tube repair should succeed"
        
        # Should repair 2 tubes maximum
        repaired_count = sum(1 for tube in self.u_boat.torpedo_tubes if tube == TubeState.EMPTY)
        assert repaired_count == 2, "Should repair exactly 2 tubes"
        
        # One tube should still be damaged
        damaged_count = sum(1 for tube in self.u_boat.torpedo_tubes if tube == TubeState.DAMAGED)
        assert damaged_count == 1, "One tube should still be damaged"
        
        assert result.ap_spent == 2, "Surface repair should cost 2 AP"
    
    def test_repair_validation_blocked(self):
        """Test that repair validation blocks invalid repairs."""
        # Try to repair Deck Gun while submerged
        self.u_boat.deck_gun_damaged = True
        self.u_boat.depth = Depth.PERISCOPE
        
        action = RepairAction("Deck Gun", self.cost_lookup, self.validator)
        can_repair, reason = action.validate(self.game)
        
        assert not can_repair, "Deck Gun repair should be blocked when submerged"
        assert "Surfaced" in reason, "Reason should mention surface requirement"
    
    def test_repair_submerged_with_engineer(self):
        """Test that submerged repairs work with engineer alive."""
        self.u_boat.engine_damaged = True
        self.u_boat.depth = Depth.PERISCOPE
        self.u_boat.engineer_alive = True
        
        action = RepairAction("Engine", self.cost_lookup, self.validator)
        result = action.execute(self.game)
        
        assert result.success, "Engine repair should succeed submerged with engineer"
        assert not self.u_boat.engine_damaged, "Engine should no longer be damaged"
        assert result.ap_spent == 4, "Submerged repair should cost 4 AP"
    
    def test_repair_submerged_without_engineer_blocked(self):
        """Test that submerged repairs are blocked without engineer."""
        self.u_boat.engine_damaged = True
        self.u_boat.depth = Depth.PERISCOPE
        self.u_boat.engineer_alive = False
        
        action = RepairAction("Engine", self.cost_lookup, self.validator)
        can_repair, reason = action.validate(self.game)
        
        assert not can_repair, "Submerged repair should be blocked without engineer"
        assert "Engineer" in reason, "Reason should mention engineer requirement"
    
    def test_hull_damage_not_repairable(self):
        """Test that hull damage cannot be repaired."""
        self.u_boat.hull_damage = 2
        
        # RepairValidator doesn't have a "Hull" component
        # This test ensures hull damage is not in the repairable components list
        assert "Hull" not in self.validator.REPAIRABLE_COMPONENTS
        assert "Hull Damage" not in self.validator.REPAIRABLE_COMPONENTS
        
        # Hull damage is tracked but cannot be repaired - it's permanent
        # The game rules state hull damage cannot be repaired
        # Verify this by checking that hull damage value persists
        assert self.u_boat.hull_damage == 2, "Hull damage should persist"
        
        # Get repairable components - hull should not be in the list
        repairable = self.validator.get_repairable_components(self.u_boat)
        assert "Hull" not in repairable
        assert "Hull Damage" not in repairable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
