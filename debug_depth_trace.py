"""Debug script to trace depth changes through Turn 5."""
import sys
from core.game_state import Game
from core.uboat_ai import UBoatAI

# Initialize game
game = Game(mission_number=1)
ai_captain = UBoatAI(game)

# Fast forward to Turn 5
for turn in range(1, 5):
    success, messages = ai_captain.execute_turn()
    if not success:
        print(f"Failed at turn {turn}")
        sys.exit(1)
    # Advance through all phases
    for _ in range(6):
        game._advance_to_next_phase()

print(f"=== START OF TURN 5 ===")
print(f"Initial depth: {game.u_boat.depth.name}")
print(f"Initial position: {game.u_boat.position}")

# Execute AI turn
print(f"\n=== EXECUTING AI ACTIONS ===")
success, messages = ai_captain.execute_turn()
for msg in messages:
    print(f"  {msg}")

print(f"\nAfter AI execution:")
print(f"  Depth: {game.u_boat.depth.name}")
print(f"  Position: {game.u_boat.position}")
print(f"  Queued actions: {len(game.action_queue.actions)}")

# Phase 1: U-Boat cleanup (commits actions)
print(f"\n=== PHASE 1: U-BOAT CLEANUP ===")
game._advance_to_next_phase()
print(f"After U-Boat cleanup:")
print(f"  Depth: {game.u_boat.depth.name}")
print(f"  Position: {game.u_boat.position}")

# Phase 2: Merchant
print(f"\n=== PHASE 2: MERCHANT ===")
game._advance_to_next_phase()
print(f"After Merchant:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")

# Phase 3: Detection
print(f"\n=== PHASE 3: DETECTION ===")
game._advance_to_next_phase()
print(f"After Detection:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")

# Phase 4: Escort (THIS IS WHERE COMBAT HAPPENS)
print(f"\n=== PHASE 4: ESCORT ===")
print(f"Before Escort phase:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")
game._advance_to_next_phase()
print(f"After Escort phase:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")
print(f"  Hull damage: {game.u_boat.hull_damage}")

# Phase 5: B-24
print(f"\n=== PHASE 5: B-24 ===")
game._advance_to_next_phase()
print(f"After B-24:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")

# Phase 6: End Turn Events
print(f"\n=== PHASE 6: END TURN EVENTS ===")
game._advance_to_next_phase()
print(f"After End Turn Events:")
print(f"  U-Boat depth: {game.u_boat.depth.name}")
