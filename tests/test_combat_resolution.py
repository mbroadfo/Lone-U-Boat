"""Test combat resolution with captain AI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from core.game_state import Game
from core.uboat_ai import UBoatAI
from core.models import HexCoord, Depth, TubeState

def test_combat_resolution():
    """Test that captain can resolve torpedo and deck gun combat."""
    pygame.init()
    
    # Create game with mission 1
    game = Game(mission_number=1)
    
    # Position U-boat close to merchant for torpedo/deck gun attack
    # Place at range 2 from merchant, surfaced to enable deck gun
    game.u_boat.position = HexCoord(q=3, r=4)  # Range 2 to merchant at (1,4)
    game.u_boat.depth = Depth.SURFACED  # Must be surfaced for deck gun
    
    # Create AI captain
    captain = UBoatAI(game)
    
    print("=" * 80)
    print("COMBAT RESOLUTION TEST")
    print("=" * 80)
    print(f"U-Boat at: {game.u_boat.position}, Depth: {game.u_boat.depth.name}")
    print(f"Merchant at: {game.ships[0].position}")
    print(f"Corvette at: {game.ships[1].position if len(game.ships) > 1 else 'N/A'}")
    print(f"Distance to merchant: {game.hex_grid.hex_distance(game.u_boat.position, game.ships[0].position)}")
    print()
    
    # Run multiple attempts to capture combat
    print("Running 5 attempts to trigger combat:")
    print("-" * 80)
    
    for attempt in range(5):
        # Reset for each attempt
        if attempt > 0:
            game = Game(mission_number=1)
            game.u_boat.position = HexCoord(q=3, r=4)
            game.u_boat.depth = Depth.SURFACED
            captain = UBoatAI(game)
        
        print(f"\nAttempt {attempt + 1}:")
        _success, messages = captain.execute_turn()
        
        # Check for combat
        deck_gun_msgs = [m for m in messages if 'deck gun' in m.lower()]
        torpedo_msgs = [m for m in messages if 'torpedo' in m.lower() and '[OK]' in m]
        combat_detail_msgs = [m for m in messages if 'HIT' in m or 'MISS' in m]
        
        if deck_gun_msgs or torpedo_msgs:
            print(f"  ✓ Combat action taken!")
            for msg in messages:
                if any(keyword in msg for keyword in ['[OK]', 'HIT', 'MISS', '[COMBAT]', '[DAMAGE]', '[DL]']):
                    print(f"    {msg}")
            if combat_detail_msgs:
                break  # Found combat with results
        else:
            print(f"  - No combat actions (chose to move/rotate)")
    
    print("\n" + "=" * 80)
    
    pygame.quit()

if __name__ == "__main__":
    test_combat_resolution()
