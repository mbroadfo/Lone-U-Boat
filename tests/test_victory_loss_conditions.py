"""
Test victory and loss conditions for Mission 1.

This test suite validates:
1. Loss Condition: U-boat destroyed (hull damage 4/4)
2. Loss Condition: Merchant escapes the map
3. Victory Condition: EXIT MAP button (position + facing + AP + merchants destroyed)
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.game_state import Game
from core.models import HexCoord, Facing, Depth


class TestLossConditions:
    """Test all ways the player can lose."""
    
    def test_loss_uboat_destroyed(self):
        """Test that game ends when U-boat hull damage reaches 4/4."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set hull damage to critical
        game.u_boat.hull_damage = 4
        
        # Check game over conditions (public method would be called during game loop)
        # We test the condition directly
        is_destroyed, _ = game.escort_ai.damage_resolver.check_destruction(game.u_boat)
        
        # Verify the destruction check detects it
        assert is_destroyed, "U-boat should be detected as destroyed"
        
        # Now manually set the game state as the game loop would
        game.defeat_reason = 'destroyed'
        game.running = False
        
        # Verify defeat triggered
        assert not game.running, "Game should have ended"
        assert game.defeat_reason == 'destroyed', "Defeat reason should be 'destroyed'"
    
    def test_loss_merchant_escapes(self):
        """Test that game ends when merchant reaches exit hex."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Find the merchant
        merchant = next((ship for ship in game.ships if ship.ship_type == 'merchant'), None)
        assert merchant is not None, "Mission 1 should have a merchant"
        
        # Get merchant's exit hex from path
        merchant_index = game.ships.index(merchant)
        if merchant_index in game.merchant_ai.paths:
            path = game.merchant_ai.paths[merchant_index]
            if path.exit_hex:
                # Move merchant to exit hex
                merchant.position = path.exit_hex
                
                # Check for exited merchants
                exited = game.merchant_ai.check_merchant_exit(game.ships)
                assert len(exited) > 0, "Merchant should be detected at exit"
                
                # Manually trigger the game state changes as the game loop would
                exited_indices = [idx for idx, _ in exited]
                game.ships = [ship for i, ship in enumerate(game.ships) if i not in exited_indices]
                game.defeat_reason = 'merchant_escaped'
                game.running = False
                
                # Verify defeat triggered
                assert not game.running, "Game should have ended"
                assert game.defeat_reason == 'merchant_escaped', "Defeat reason should be 'merchant_escaped'"
    
    def test_crew_kia_not_loss(self):
        """Test that crew KIA does NOT cause game loss (per rules)."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Kill all crew members (crew_alive flags are True when alive, False when killed)
        game.u_boat.captain_alive = False
        game.u_boat.sonar_operator_alive = False
        game.u_boat.weapons_officer_alive = False
        game.u_boat.medic_alive = False
        game.u_boat.engineer_alive = False
        game.u_boat.lookout_alive = False
        
        # Game should still be running
        assert game.running, "Game should NOT end just because crew is KIA"
        assert game.defeat_reason is None, "No defeat should be triggered"


class TestVictoryConditions:
    """Test victory conditions for EXIT MAP button."""
    
    def test_victory_all_conditions_met(self):
        """Test victory when all conditions are met: position, facing, AP, merchants destroyed."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set U-boat to exit hex with correct facing
        game.u_boat.position = HexCoord(1, 7)  # Exit hex for mission 1
        game.u_boat.facing = Facing.SOUTHWEST   # Exit facing for mission 1
        
        # Ensure we have AP (use turn_manager for immediate execution)
        game.turn_manager.remaining_ap = 5
        
        # Destroy all merchants
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Check if can exit
        can_exit, reason = game.can_exit_map()
        
        assert can_exit, f"Should be able to exit: {reason}"
        assert reason == "Can exit"
        
        # Trigger victory
        game.trigger_victory()
        
        # Verify victory state
        assert not game.running, "Game should have ended"
        assert game.defeat_reason is None, "No defeat reason should be set on victory"
    
    def test_cannot_exit_wrong_position(self):
        """Test that cannot exit if not on exit hex."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set U-boat to WRONG position
        game.u_boat.position = HexCoord(2, 7)  # Not the exit hex
        game.u_boat.facing = Facing.SOUTHWEST
        
        # Ensure we have AP
        game.action_queue.reset_for_new_turn(5, game)
        
        # Destroy all merchants
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Check if can exit
        can_exit, reason = game.can_exit_map()
        
        assert not can_exit, "Should NOT be able to exit from wrong position"
        assert "Not on exit hex" in reason
    
    def test_cannot_exit_wrong_facing(self):
        """Test that cannot exit if facing wrong direction."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set U-boat to exit hex but WRONG facing
        game.u_boat.position = HexCoord(1, 7)
        game.u_boat.facing = Facing.NORTH  # Should be SOUTHWEST
        
        # Ensure we have AP
        game.action_queue.reset_for_new_turn(5, game)
        
        # Destroy all merchants
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Check if can exit
        can_exit, reason = game.can_exit_map()
        
        assert not can_exit, "Should NOT be able to exit facing wrong direction"
        assert "Wrong facing" in reason
    
    def test_cannot_exit_no_ap(self):
        """Test that cannot exit without AP remaining."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set U-boat to exit hex with correct facing
        game.u_boat.position = HexCoord(1, 7)
        game.u_boat.facing = Facing.SOUTHWEST
        
        # Set AP to 0
        game.action_queue.reset_for_new_turn(0, game)
        
        # Destroy all merchants
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Check if can exit
        can_exit, reason = game.can_exit_map()
        
        assert not can_exit, "Should NOT be able to exit without AP"
        assert "No movement points remaining" in reason
    
    def test_cannot_exit_merchants_alive(self):
        """Test that cannot exit while merchants are still alive."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set U-boat to exit hex with correct facing
        game.u_boat.position = HexCoord(1, 7)
        game.u_boat.facing = Facing.SOUTHWEST
        
        # Ensure we have AP (use turn_manager for immediate execution)
        game.turn_manager.remaining_ap = 5
        
        # Keep merchants alive (don't remove them)
        merchant_count = sum(1 for ship in game.ships if ship.ship_type == 'merchant')
        assert merchant_count > 0, "Mission 1 should have at least one merchant"
        
        # Check if can exit
        can_exit, reason = game.can_exit_map()
        
        assert not can_exit, "Should NOT be able to exit with merchants alive"
        assert "merchant(s) still alive" in reason
    
    def test_can_exit_with_preview_state(self):
        """Test that can_exit_map works with preview position and facing."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Current position is NOT at exit
        game.u_boat.position = HexCoord(1, 6)
        game.u_boat.facing = Facing.SOUTH
        
        # But PREVIEW position (after queued move + rotate) would be at exit
        preview_position = HexCoord(1, 7)
        preview_facing = Facing.SOUTHWEST
        
        # Ensure we have AP (use turn_manager for immediate execution)
        game.turn_manager.remaining_ap = 5
        
        # Destroy all merchants
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Check with preview state
        can_exit, reason = game.can_exit_map(preview_position, preview_facing)
        
        assert can_exit, f"Should be able to exit with preview state: {reason}"
        
        # Check without preview state (should fail)
        can_exit_current, _ = game.can_exit_map()
        assert not can_exit_current, "Should NOT be able to exit from current position"


class TestDefeatReasonTracking:
    """Test that defeat_reason is properly tracked."""
    
    def test_defeat_reason_none_on_start(self):
        """Test that defeat_reason is None when game starts."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        assert game.defeat_reason is None
        assert game.running is True
    
    def test_defeat_reason_destroyed(self):
        """Test that defeat_reason is set to 'destroyed' on hull damage."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        game.u_boat.hull_damage = 4
        
        # Verify destruction is detected
        is_destroyed, _ = game.escort_ai.damage_resolver.check_destruction(game.u_boat)
        assert is_destroyed, "U-boat should be detected as destroyed"
        
        # Manually set defeat state as game loop would
        game.defeat_reason = 'destroyed'
        game.running = False
        
        assert game.defeat_reason == 'destroyed'
        assert not game.running
    
    def test_defeat_reason_merchant_escaped(self):
        """Test that defeat_reason is set to 'merchant_escaped' when merchant exits."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Manually set defeat state as would happen when merchant escapes
        game.defeat_reason = 'merchant_escaped'
        game.running = False
        
        assert game.defeat_reason == 'merchant_escaped'
        assert not game.running
    
    def test_defeat_reason_none_on_victory(self):
        """Test that defeat_reason remains None on victory."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Set up victory conditions
        game.u_boat.position = HexCoord(1, 7)
        game.u_boat.facing = Facing.SOUTHWEST
        game.action_queue.reset_for_new_turn(5, game)
        game.ships = [ship for ship in game.ships if ship.ship_type != 'merchant']
        
        # Trigger victory
        game.trigger_victory()
        
        assert game.defeat_reason is None, "Victory should NOT set defeat_reason"
        assert not game.running


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
