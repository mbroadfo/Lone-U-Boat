"""Debug merchant movement issue."""
from core.game_state import Game
from core.models import HexCoord, GamePhase

game = Game(mission_number=1)
game.turn_manager.start_new_turn(game.u_boat)

merchant = game.ships[0]

print(f"Starting position: {merchant.position}")
print(f"Merchant AI paths: {game.merchant_ai.paths}")

for turn_num in range(1, 5):
    print(f"\n=== Turn {turn_num} ===")
    print(f"Before: {merchant.position}")
    
    # Get the path and check next waypoint
    path = game.merchant_ai.paths[0]
    next_wp = path.get_next_waypoint(merchant.position)
    print(f"Next waypoint should be: {next_wp}")
    
    # Advance through U-Boat phase
    game._advance_to_next_phase()
    
    # Advance through merchant phase
    game._advance_to_next_phase()
    
    print(f"After merchant phase: {merchant.position}")
    
    # Skip other phases to start next turn
    while game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
        game._advance_to_next_phase()
    
    print(f"Final position turn {turn_num}: {merchant.position}")
