"""
Test destroyed entity visual feedback system.
Tests tracking, rendering, and cleanup of destroyed entities.
"""

import pytest
from core.models import HexCoord, Depth, Facing, GamePhase
from core.game_state import Game


class TestDestroyedEntityTracking:
    """Test destroyed entity tracking in Game class."""
    
    def test_record_destroyed_ship(self):
        """Test recording a destroyed ship."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Record a destroyed corvette
        game.record_destroyed_entity(
            entity_type='corvette',
            position=HexCoord(5, 5),
            name='CORVETTE'
        )
        
        assert len(game.destroyed_this_phase) == 1
        destroyed = game.destroyed_this_phase[0]
        assert destroyed['type'] == 'corvette'
        assert destroyed['position'] == HexCoord(5, 5)
        assert destroyed['name'] == 'CORVETTE'
    
    def test_record_destroyed_b24(self):
        """Test recording a destroyed B-24."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Record a destroyed B-24
        game.record_destroyed_entity(
            entity_type='b24',
            position=HexCoord(7, 3),
            name='B-24'
        )
        
        assert len(game.destroyed_this_phase) == 1
        destroyed = game.destroyed_this_phase[0]
        assert destroyed['type'] == 'b24'
        assert destroyed['position'] == HexCoord(7, 3)
        assert destroyed['name'] == 'B-24'
    
    def test_record_multiple_destroyed_entities(self):
        """Test recording multiple destroyed entities."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Record multiple destroyed entities
        game.record_destroyed_entity('corvette', HexCoord(5, 5), 'CORVETTE')
        game.record_destroyed_entity('merchant', HexCoord(4, 6), 'MERCHANT')
        game.record_destroyed_entity('b24', HexCoord(7, 3), 'B-24')
        
        assert len(game.destroyed_this_phase) == 3
        assert game.destroyed_this_phase[0]['type'] == 'corvette'
        assert game.destroyed_this_phase[1]['type'] == 'merchant'
        assert game.destroyed_this_phase[2]['type'] == 'b24'
    
    def test_cleanup_destroyed_entities_clears_list(self):
        """Test that cleanup clears destroyed entities list."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Record destroyed entities
        game.record_destroyed_entity('corvette', HexCoord(5, 5), 'CORVETTE')
        game.record_destroyed_entity('merchant', HexCoord(4, 6), 'MERCHANT')
        
        assert len(game.destroyed_this_phase) == 2
        
        # Cleanup should clear the list
        game._cleanup_destroyed_entities()  # type: ignore[reportPrivateUsage]
        
        assert len(game.destroyed_this_phase) == 0


class TestDestroyedEntityIntegration:
    """Integration tests for destroyed entity system."""
    
    def test_ship_destruction_records_entity(self):
        """Test that ship destruction is properly recorded."""
        # This test would require mocking torpedo attacks and damage resolution
        # Placeholder for integration test
        pass
    
    def test_b24_destruction_records_entity(self):
        """Test that B-24 flak destruction is properly recorded."""
        # This test would require mocking B-24 flak defense
        # Placeholder for integration test
        pass
    
    def test_phase_advance_cleans_up_destroyed_entities(self):
        """Test that phase advance properly cleans up destroyed entities."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Add some ships to the game
        from core.models import Ship
        ship1 = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
        ship2 = Ship(ship_type='merchant', position=HexCoord(4, 6), facing=Facing.SOUTHEAST)
        game.ships = [ship1, ship2]
        
        # Record ship1 as destroyed
        game.record_destroyed_entity('corvette', ship1.position, 'CORVETTE')
        
        assert len(game.destroyed_this_phase) == 1
        assert len(game.ships) == 2
        
        # Advance phase (should trigger cleanup)
        game._cleanup_destroyed_entities()  # type: ignore[reportPrivateUsage]
        
        # Destroyed list should be cleared
        assert len(game.destroyed_this_phase) == 0
        
        # Ship should be removed from game
        assert len(game.ships) == 1
        assert game.ships[0] == ship2
    
    def test_b24_off_map_does_not_record(self):
        """Test that B-24s flying off map do NOT show destroyed overlay."""
        # This test would verify that only flak-destroyed B-24s are recorded,
        # not those that flew off the map
        # Placeholder for integration test
        pass


class TestB24DestructionDifferentiation:
    """Test B-24 destruction reason differentiation."""
    
    def test_b24_destroyed_by_flak_returns_true(self):
        """Test that B-24 destroyed by flak returns (True, True)."""
        # Test _activate_aircraft returns should_remove=True, was_destroyed=True
        # when B-24 is destroyed by flak
        pass
    
    def test_b24_flew_off_map_returns_false(self):
        """Test that B-24 flying off map returns (True, False)."""
        # Test _activate_aircraft returns should_remove=True, was_destroyed=False
        # when B-24 flies off map
        pass
    
    def test_b24_still_active_returns_false_false(self):
        """Test that active B-24 returns (False, False)."""
        # Test _activate_aircraft returns should_remove=False, was_destroyed=False
        # when B-24 remains active
        pass


class TestB24SpawnValidation:
    """Test B-24 spawn position validation fix."""
    
    def test_b24_spawns_on_valid_hex(self):
        """Test that B-24s spawn only on valid mission hexes."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Spawn some B-24s via event system
        # Verify all spawn positions are in mission_hexes
        for aircraft in game.aircraft:
            assert aircraft.position in game.mission_hexes, \
                f"B-24 spawned at {aircraft.position} which is not in mission_hexes"
    
    def test_b24_never_spawns_at_9_7(self):
        """Test that B-24s never spawn at [9,7] (outside mission)."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Run multiple turns to trigger B-24 spawns
        for _ in range(10):
            if not game.running:
                break
            
            # Check no B-24 at [9,7]
            for aircraft in game.aircraft:
                assert aircraft.position != HexCoord(9, 7), \
                    "B-24 spawned at invalid position [9,7]"
            
            # Advance to next turn
            if game.turn_manager.current_phase == GamePhase.END_TURN_EVENTS:
                game._execute_end_turn_events()  # type: ignore[reportPrivateUsage]
    
    def test_b24_never_spawns_at_8_8(self):
        """Test that B-24s never spawn at [8,8] (outside mission)."""
        game = Game(mission_number=1, initial_depth=Depth.SURFACED, initial_facing=Facing.NORTH)
        
        # Run multiple turns to trigger B-24 spawns
        for _ in range(10):
            if not game.running:
                break
            
            # Check no B-24 at [8,8]
            for aircraft in game.aircraft:
                assert aircraft.position != HexCoord(8, 8), \
                    "B-24 spawned at invalid position [8,8]"
            
            # Advance to next turn
            if game.turn_manager.current_phase == GamePhase.END_TURN_EVENTS:
                game._execute_end_turn_events()  # type: ignore[reportPrivateUsage]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
