"""Test script to verify U-boat destruction triggers game over correctly."""
from core.game_state import Game

def test_destruction_check():
    """Test that game ends when U-boat is destroyed."""
    print("\n" + "="*60)
    print("TEST: U-Boat Destruction Check")
    print("="*60)
    
    # Create game instance
    game = Game()
    
    # Manually damage the U-boat to near-destruction
    print(f"\nInitial hull damage: {game.u_boat.hull_damage}")
    print(f"Max hull damage: {game.escort_ai.damage_resolver.max_hull_damage}")
    
    # Apply damage up to max
    max_damage = game.escort_ai.damage_resolver.max_hull_damage
    game.u_boat.hull_damage = max_damage - 1
    print(f"\nSet hull damage to {game.u_boat.hull_damage} (one below max)")
    
    # Check if game is still running
    print(f"Game running: {game.running}")
    
    # Check destruction status
    is_destroyed, reason = game.escort_ai.damage_resolver.check_destruction(game.u_boat)
    print(f"Is destroyed: {is_destroyed}, Reason: {reason}")
    
    # Now apply one more damage to reach max
    game.u_boat.hull_damage = max_damage
    print(f"\nSet hull damage to {game.u_boat.hull_damage} (at max)")
    
    # Check destruction status again
    is_destroyed, reason = game.escort_ai.damage_resolver.check_destruction(game.u_boat)
    print(f"Is destroyed: {is_destroyed}, Reason: {reason}")
    
    # Call the game over check
    print("\nCalling _check_game_over_conditions()...")
    game._check_game_over_conditions()  # type: ignore[attr-defined]
    
    # Check if game stopped
    print(f"Game running after check: {game.running}")
    
    # Test exceeding max damage
    game.running = True  # Reset for second test
    game.u_boat.hull_damage = max_damage + 1
    print(f"\nSet hull damage to {game.u_boat.hull_damage} (above max)")
    
    is_destroyed, reason = game.escort_ai.damage_resolver.check_destruction(game.u_boat)
    print(f"Is destroyed: {is_destroyed}, Reason: {reason}")
    
    game._check_game_over_conditions()  # type: ignore[attr-defined]
    print(f"Game running after check: {game.running}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_destruction_check()
