"""
Test script with scripted captain - follows predetermined instructions.
This eliminates randomness to debug specific scenarios consistently.
"""

import pygame
from core.game_state import Game
from core.scripted_captain import ScriptedCaptain
from core.models import GamePhase


def run_scripted_test(num_turns: int = 10):
    """
    Run the game with scripted captain for specified number of turns.
    
    Args:
        num_turns: Number of turns to simulate
    """
    print("="*80)
    print("SCRIPTED U-BOAT CAPTAIN TEST")
    print("="*80)
    print(f"Running {num_turns} turns with scripted orders:\n")
    print("ORDERS:")
    print("  1. Head NW for 4 paces")
    print("  2. Turn southwest")
    print("  3. Engage the enemy (deck gun/torpedoes)")
    print("  4. Move forward and/or rotate")
    print("  5. Repair as needed")
    print("="*80)
    print()
    
    # Initialize game
    game = Game(mission_number=1)
    
    # Captain will create action catalog in plan_turn
    captain = ScriptedCaptain(game, None)
    
    # Show initial state
    print(f"Loaded {len(game.ships)} ships:")
    for ship in game.ships:
        print(f"  {ship.ship_type} at {ship.position}")
    
    print(f"\nU-Boat starting at {game.u_boat.position}")
    print(f"  Depth: {game.u_boat.depth.name}")
    print(f"  Facing: {game.u_boat.facing.name}")
    print(f"  Hull: {game.u_boat.hull_damage}/3\n")
    
    # Statistics tracking
    stats = {
        'turns_completed': 0,
        'total_actions': 0,
        'phases_executed': 0,
        'combat_engaged': 0,
        'damage_taken': 0
    }
    
    try:
        for turn in range(1, num_turns + 1):
            print(f"\n{'='*80}")
            print(f"TURN {turn}")
            print(f"{'='*80}")
            
            # Check phase
            if game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
                print(f"ERROR: Expected U-Boat Phase at turn start")
                break
            
            # Save state for comparison
            old_pos = game.u_boat.position
            old_depth = game.u_boat.depth
            old_facing = game.u_boat.facing
            old_hull = game.u_boat.hull_damage
            old_dl = game.detection_level
            
            # Execute captain's turn (like UBoatAI does)
            _success, messages = captain.execute_turn()
            
            # Show AP roll
            if hasattr(game.turn_manager, 'last_ap_roll') and game.turn_manager.last_ap_roll:
                roll_info = game.turn_manager.last_ap_roll
                print(f"AP Roll: {roll_info['rolls']} -> {roll_info['highest']}+{roll_info['captain_bonus']}(captain) = {game.u_boat.action_points} AP")
            
            # Show Phase 1 actions
            action_summary: list[str] = []
            for msg in messages:
                if any(keyword in msg for keyword in ['MOVE', 'ROTATE', 'REPAIR', 'ENGAGE', 'MANEUVER']):
                    action_summary.append(msg)
            
            if action_summary:
                actions_executed = len([msg for msg in messages if 'executed' in msg])
                if actions_executed:
                    stats['total_actions'] += 1
                print(f"Phase 1 (U-Boat): {', '.join(action_summary[:3])}")
                if len(action_summary) > 3:
                    print(f"                  {', '.join(action_summary[3:])}")
            else:
                print(f"Phase 1 (U-Boat): No actions taken")
            
            # Show position/state changes
            if game.u_boat.position != old_pos or game.u_boat.facing != old_facing or game.u_boat.depth != old_depth:
                changes: list[str] = []
                if game.u_boat.position != old_pos:
                    changes.append(f"->{game.u_boat.position}")
                if game.u_boat.depth != old_depth:
                    changes.append(f"->{game.u_boat.depth.name}")
                if game.u_boat.facing != old_facing:
                    changes.append(f"->{game.u_boat.facing.name}")
                print(f"                  {' '.join(changes)}")
            
            # Execute remaining phases
            phase_count = 0
            merchant = next((s for s in game.ships if s.ship_type == 'merchant'), None)
            escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
            old_merchant_pos = merchant.position if merchant else None
            old_escort_pos = escorts[0].position if escorts else None
            
            while game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
                phase = game.turn_manager.current_phase
                
                # Track merchant position for Phase 2
                if phase == GamePhase.MERCHANT_PHASE and merchant:
                    old_merchant_pos = merchant.position
                
                # Track escorts for Phase 4
                if phase == GamePhase.ESCORT_PHASE and escorts:
                    old_escort_pos = escorts[0].position
                
                # Advance phase (executes current phase logic)
                game._advance_to_next_phase()
                phase_count += 1
                stats['phases_executed'] += 1
                
                # Report phase results
                if phase == GamePhase.MERCHANT_PHASE and merchant:
                    if merchant.position != old_merchant_pos:
                        print(f"Phase 2 (Merchant): Merchant moved {old_merchant_pos} -> {merchant.position}")
                    else:
                        print(f"Phase 2 (Merchant): Merchant stayed at {merchant.position}")
                
                elif phase == GamePhase.DETECTION_PHASE:
                    if game.detection_level != old_dl:
                        print(f"Phase 3 (Detection): DETECTED - DL {old_dl} -> {game.detection_level}")
                        stats['combat_engaged'] += 1
                    else:
                        print(f"Phase 3 (Detection): Not detected (DL: {game.detection_level})")
                
                elif phase == GamePhase.ESCORT_PHASE and escorts:
                    escort = escorts[0]
                    if escort.position != old_escort_pos:
                        print(f"Phase 4 (Escort): {escort.ship_type.capitalize()} moved {old_escort_pos} -> {escort.position}")
                    else:
                        print(f"Phase 4 (Escort): {escort.ship_type.capitalize()} at {escort.position}")
                
                elif phase == GamePhase.B24_PHASE:
                    if game.aircraft:
                        aircraft_pos = game.aircraft[0].position if game.aircraft else None
                        print(f"Phase 5 (B-24 Aircraft): Aircraft at {aircraft_pos}")
                    else:
                        print(f"Phase 5 (B-24 Aircraft): No B-24 present")
                
                elif phase == GamePhase.END_TURN_PHASE:
                    # Check for events
                    event_logs = [log for log in game.turn_manager.phase_logs if 'Event:' in log[1]]
                    if event_logs:
                        for _phase_name, log in event_logs:
                            print(f"Phase 6 (End Turn Events): {log}")
                    else:
                        print(f"Phase 6 (End Turn Events): No events")
            
            # Check for damage taken
            if game.u_boat.hull_damage > old_hull:
                damage_delta = game.u_boat.hull_damage - old_hull
                stats['damage_taken'] += damage_delta
                print(f"\n  *** DAMAGE TAKEN: +{damage_delta} hull damage ***")
            
            # Show turn end summary
            print(f"\n  Turn {turn} End: U-Boat at {game.u_boat.position} ({game.u_boat.depth.name}), Hull {game.u_boat.hull_damage}/3")
            if game.detection_level > 0:
                print(f"              *** DETECTION LEVEL: {game.detection_level} ***")
            else:
                print(f"              Detection Level: {game.detection_level}")
            print(f"              Ships remaining: {len(game.ships)}")
            
            merchant = next((s for s in game.ships if s.ship_type == 'merchant'), None)
            if merchant:
                print(f"              Merchant at: {merchant.position}")
            
            stats['turns_completed'] += 1
            
            # Check for victory/defeat conditions
            if game.u_boat.hull_damage >= 3:
                print("\n*** U-BOAT DESTROYED ***")
                break
            
            if not any(s.ship_type == 'merchant' for s in game.ships):
                print("\n*** MISSION SUCCESS - MERCHANT SUNK ***")
                break
        
        # Print statistics
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        print()
        print("="*80)
        print("STATISTICS")
        print("="*80)
        print(f"Turns completed: {stats['turns_completed']}/{num_turns}")
        print(f"Total actions taken: {stats['total_actions']}")
        print(f"Phases executed: {stats['phases_executed']}")
        print(f"Combat engagements: {stats['combat_engaged']}")
        print(f"Damage taken: {stats['damage_taken']}")
        print(f"Current turn: {game.turn_manager.turn_number}")
        print(f"Current phase: {game.turn_manager.current_phase.name}")
        print(f"Detection Level: {game.detection_level}")
        print(f"U-Boat status:")
        print(f"  Position: {game.u_boat.position}")
        print(f"  Depth: {game.u_boat.depth.name}")
        print(f"  Facing: {game.u_boat.facing.name}")
        print(f"  Hull Damage: {game.u_boat.hull_damage}/3")
        print(f"  Torpedoes: {sum(game.u_boat.torpedo_tubes)}/{len(game.u_boat.torpedo_tubes)} loaded")
        deck_gun_status = 'Unknown'
        if hasattr(game.u_boat, 'deck_gun_loaded'):
            deck_gun_status = 'Ready' if game.u_boat.deck_gun_loaded else 'Fired'  # type: ignore
        print(f"  Deck Gun: {deck_gun_status}")
        print(f"Ships remaining: {len(game.ships)}")
        print("="*80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        pygame.quit()


if __name__ == "__main__":
    run_scripted_test(num_turns=10)
