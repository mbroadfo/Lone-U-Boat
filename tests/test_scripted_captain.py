"""
Test script with scripted captain - follows predetermined instructions.
This eliminates randomness to debug specific scenarios consistently.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            # Extract [OK] messages which show executed actions
            action_msgs = [msg for msg in messages if msg.startswith('[OK]')]
            combat_msgs = [msg for msg in messages if msg.startswith('[COMBAT]') or msg.startswith('[DAMAGE]')]
            
            if action_msgs:
                # Count actions for stats
                stats['total_actions'] += len(action_msgs)
                
                # Simplify action messages for display
                action_display = []
                combat_results = []
                for msg in action_msgs:
                    # Extract just the action type from messages like "[OK] Moved from..."
                    if 'Moved' in msg:
                        action_display.append('Move(2AP)')
                    elif 'Rotated' in msg:
                        direction = 'R' if 'clockwise' in msg and 'counter' not in msg else 'L'
                        action_display.append(f'Rotate-{direction}(1AP)')
                    elif 'depth' in msg.lower():
                        action_display.append('Depth(2AP)')
                    elif 'Repaired' in msg:
                        # Extract what was repaired
                        if 'Engine' in msg:
                            action_display.append('Repair(Engine)')
                        elif 'Deck Gun' in msg:
                            action_display.append('Repair(DeckGun)')
                        elif 'Torpedo' in msg:
                            action_display.append('Repair(Tubes)')
                        else:
                            action_display.append('Repair')
                    elif 'Fired deck gun' in msg:
                        action_display.append('DeckGun(2AP)')
                        # Extract hit/miss info
                        if 'Hit' in msg:
                            combat_results.append(f"  DeckGun: HIT! {msg.split('Hit')[1].strip()}")
                        elif 'Miss' in msg:
                            combat_results.append(f"  DeckGun: MISS")
                    elif 'Fire' in msg or 'torpedo' in msg.lower():
                        # Count how many torpedoes
                        import re
                        torp_match = re.search(r'(\d+) torpedo', msg)
                        if torp_match:
                            num_torps = torp_match.group(1)
                            action_display.append(f'FireTorp(x{num_torps})')
                        else:
                            action_display.append('FireTorp')
                        # Extract hit/miss info
                        if 'Hit' in msg:
                            hits = msg.count('Hit')
                            combat_results.append(f"  Torpedoes: {hits} HIT(S)!")
                        elif 'Miss' in msg or 'missed' in msg:
                            combat_results.append(f"  Torpedoes: All missed")
                    else:
                        action_display.append('Action')
                
                print(f"Phase 1 (U-Boat): {', '.join(action_display)} [{len(action_msgs)} actions]")
                # Show combat results if any
                for result in combat_results:
                    print(f"                  {result}")
                # Show detailed combat messages from AI combat resolution
                for msg in combat_msgs:
                    print(f"                  {msg}")
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
            
            # Execute remaining phases (2-7)
            phase_count = 0
            
            # Get references before phase loop
            merchant = next((s for s in game.ships if s.ship_type == 'merchant'), None)
            escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
            
            # Track positions before phases
            old_merchant_pos = merchant.position if merchant else None
            old_escort_pos = escorts[0].position if escorts else None
            
            # Advance through phases until we wrap back to UBOAT_PHASE
            # There are 6 more phases: MERCHANT, DETECTION, ESCORT, B24, END_TURN_EVENTS, END_TURN_PHASE
            # Then END_TURN_PHASE should wrap to UBOAT_PHASE for next turn
            for _ in range(7):  # Need 7 advances to complete turn and wrap back
                current_phase = game.turn_manager.current_phase
                
                # Advance to next phase (this executes current phase's logic)
                game._advance_to_next_phase()  # type: ignore[reportPrivateUsage]
                phase_count += 1
                stats['phases_executed'] += 1
                
                # Break if we've wrapped back to UBOAT_PHASE (start of next turn)
                if game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
                    break
                
                # Get updated references after phase execution
                merchant = next((s for s in game.ships if s.ship_type == 'merchant'), None)
                escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
                
                # Report what happened in the phase we just executed
                if current_phase == GamePhase.MERCHANT_PHASE:
                    new_merchant_pos = merchant.position if merchant else None
                    if merchant and new_merchant_pos != old_merchant_pos:
                        print(f"Phase 2 (Merchant): Moved {old_merchant_pos} -> {new_merchant_pos}")
                    elif merchant:
                        print(f"Phase 2 (Merchant): Stayed at {new_merchant_pos}")
                    else:
                        print(f"Phase 2 (Merchant): No merchants")
                    old_merchant_pos = new_merchant_pos
                
                elif current_phase == GamePhase.DETECTION_PHASE:
                    if game.detection_level != old_dl:
                        print(f"Phase 3 (Detection): DETECTED! DL {old_dl} -> {game.detection_level}")
                        stats['combat_engaged'] += 1
                    else:
                        # Check if escorts are in range
                        in_range = False
                        if escorts and merchant:
                            for escort in escorts:
                                dist = game.hex_grid.hex_distance(escort.position, game.u_boat.position)
                                if dist <= 3:
                                    in_range = True
                                    break
                        if in_range:
                            print(f"Phase 3 (Detection): Detection attempt failed (DL: {game.detection_level})")
                        else:
                            print(f"Phase 3 (Detection): No detection - escorts out of range (DL: {game.detection_level})")
                
                elif current_phase == GamePhase.ESCORT_PHASE:
                    new_escort_pos = escorts[0].position if escorts else None
                    if escorts and new_escort_pos != old_escort_pos:
                        escort = escorts[0]
                        print(f"Phase 4 (Escort): {escort.ship_type.capitalize()} moved {old_escort_pos} -> {new_escort_pos}")
                    elif escorts:
                        escort = escorts[0]
                        print(f"Phase 4 (Escort): {escort.ship_type.capitalize()} at {new_escort_pos}")
                    else:
                        print(f"Phase 4 (Escort): No escorts")
                    old_escort_pos = new_escort_pos
                
                elif current_phase == GamePhase.B24_PHASE:
                    if game.aircraft:
                        aircraft_pos = game.aircraft[0].position
                        print(f"Phase 5 (B-24 Aircraft): Aircraft at {aircraft_pos}")
                    else:
                        print(f"Phase 5 (B-24 Aircraft): No B-24 present")
                
                elif current_phase == GamePhase.END_TURN_EVENTS:
                    # Show event roll if available
                    print(f"Phase 6 (End Turn Events): Executed")
                
                elif current_phase == GamePhase.END_TURN_PHASE:
                    # This wraps back to UBOAT_PHASE
                    break
            
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
        from core.models import TubeState
        print(f"U-Boat status:")
        print(f"  Position: {game.u_boat.position}")
        print(f"  Depth: {game.u_boat.depth.name}")
        print(f"  Facing: {game.u_boat.facing.name}")
        print(f"  Hull Damage: {game.u_boat.hull_damage}/3")
        loaded_tubes = sum(1 for tube in game.u_boat.torpedo_tubes if tube == TubeState.LOADED)
        print(f"  Torpedoes: {loaded_tubes}/{len(game.u_boat.torpedo_tubes)} loaded")
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
