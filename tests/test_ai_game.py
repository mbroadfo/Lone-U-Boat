"""
Test script to run the game with AI U-boat captain.
Tests full turn cycle through all phases automatically.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
import sys
from io import StringIO
from contextlib import contextmanager
from core.game_state import Game
from core.uboat_ai import UBoatAI
from core.models import GamePhase


@contextmanager
def capture_output():
    """Context manager to capture stdout."""
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    try:
        yield captured_output
    finally:
        sys.stdout = old_stdout


def run_ai_test(num_turns: int = 5, delay_ms: int = 500, verbose: bool = False):
    """
    Run the game with AI captain for specified number of turns.
    
    Args:
        num_turns: Number of turns to simulate
        delay_ms: Delay between phases in milliseconds (for readability)
        verbose: If True, show detailed AI action messages
    """
    print("="*80)
    print("AI U-BOAT CAPTAIN TEST")
    print("="*80)
    print(f"Running {num_turns} turns with AI captain...\n")
    
    # Initialize game
    game = Game(mission_number=1)
    ai_captain = UBoatAI(game)
    
    # Debug: Check what ships we have and track initial merchant position
    print(f"Loaded {len(game.ships)} ships:")
    for i, ship in enumerate(game.ships):
        print(f"  Ship {i}: {ship.ship_type} at {ship.position}")
    
    initial_merchant_pos = game.ships[0].position if game.ships and game.ships[0].ship_type == 'merchant' else None
    print(f"Initial merchant position: {initial_merchant_pos}\n")
    
    # Track statistics
    stats = {
        'turns_completed': 0,
        'total_actions': 0,
        'phases_executed': 0,
        'errors': []
    }
    
    try:
        for turn in range(1, num_turns + 1):
            print(f"\n{'='*80}")
            print(f"TURN {turn}")
            print(f"{'='*80}")
            
            # Ensure we're in U-Boat phase
            if game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
                print(f"ERROR: Expected U-Boat Phase, but in {game.turn_manager.current_phase}")
                stats['errors'].append(f"Turn {turn}: Wrong phase at start")
                break
            
            # Phase 0: AP Roll (before Phase 1)
            # Capture old position/depth for comparison
            old_pos = game.u_boat.position
            old_depth = game.u_boat.depth
            old_facing = game.u_boat.facing
            
            # Suppress [EVENT] output
            suppressed_output = StringIO()
            old_stdout = sys.stdout
            sys.stdout = suppressed_output
            
            try:
                success, messages = ai_captain.execute_turn()
                sys.stdout = old_stdout
                
                if not success:
                    print("AI execution failed")
                    stats['errors'].append(f"Turn {turn}: AI execution failed")
                    break
                
                # Extract AP roll from messages and show detailed breakdown
                ap_roll_msg = [m for m in messages if 'rolled' in m and 'AP' in m]
                if ap_roll_msg:
                    ap_value = int(ap_roll_msg[0].split()[2])  # "AI rolled X AP"
                    # Get roll details from turn_manager
                    if hasattr(game.turn_manager, 'last_ap_roll') and game.turn_manager.last_ap_roll:
                        roll_info = game.turn_manager.last_ap_roll
                        dice_str = str(roll_info['rolls'])
                        highest = roll_info['highest']
                        captain_bonus = roll_info['captain_bonus']
                        if captain_bonus > 0:
                            print(f"AP Roll: {dice_str} -> {highest}+{captain_bonus}(captain) = {ap_value} AP")
                        else:
                            print(f"AP Roll: {dice_str} -> {highest} = {ap_value} AP")
                    else:
                        print(f"AP Roll: {ap_value} AP")
                
                # Show Phase 1 with actions and costs
                print(f"Phase 1 (U-Boat):", end=" ")
                
                # Parse action messages - format is "[OK] Rotated..." or "[OK] Moved..."
                # Infer AP costs based on action type and changes
                action_details = []
                total_ap_used = 0
                
                for msg in messages:
                    if msg.startswith('[OK]'):
                        if 'Moved from' in msg:
                            # Movement costs 2 AP
                            action_details.append("Move(2AP)")
                            total_ap_used += 2
                        elif 'Rotated' in msg:
                            # Rotation costs 1 AP - differentiate L/R
                            if 'clockwise' in msg and 'counter' not in msg:
                                action_details.append("Rotate-R(1AP)")
                            else:
                                action_details.append("Rotate-L(1AP)")
                            total_ap_used += 1
                        elif 'depth' in msg.lower() or 'Submerged' in msg or 'Surfaced' in msg:
                            # Depth change costs 2 AP
                            action_details.append("Depth(2AP)")
                            total_ap_used += 2
                
                # Show what changed for confirmation
                changes = []
                if game.u_boat.position != old_pos:
                    changes.append(f"->{game.u_boat.position}")
                if game.u_boat.depth != old_depth:
                    changes.append(f"->{game.u_boat.depth.name}")
                if game.u_boat.facing != old_facing:
                    changes.append(f"->{game.u_boat.facing.name}")
                
                if action_details:
                    print(f"{', '.join(action_details)} [{total_ap_used}AP used] {' '.join(changes)}")
                else:
                    print("No actions taken")
                
                if verbose:
                    for msg in messages:
                        print(f"  {msg}")
            
            except Exception as e:
                sys.stdout = old_stdout
                print(f"ERROR: {e}")
                raise
            
            stats['total_actions'] += len(game.action_queue.action_history) if hasattr(game.action_queue, 'action_history') else 0
            
            # Phase 2-7: Execute remaining phases
            # NOTE: _advance_to_next_phase() executes CURRENT phase logic then advances to NEXT phase
            # So when we're in UBOAT phase and call advance, it executes U-Boat cleanup, then advances to MERCHANT
            # Then when in MERCHANT and call advance, it executes Merchant logic, then advances to DETECTION
            # The label here should describe what EXECUTES (the current phase), not where we end up
            phases_to_execute = [
                # (current_phase_label, executing_phase_label, expected_next_phase)
                ("U-Boat cleanup", "U-Boat cleanup", GamePhase.MERCHANT_PHASE),
                ("Merchant", "Merchant", GamePhase.DETECTION_PHASE),
                ("Detection", "Detection", GamePhase.ESCORT_PHASE),
                ("Escort", "Escort", GamePhase.B24_PHASE),
                ("B-24", "B-24 Aircraft", GamePhase.END_TURN_EVENTS),
                ("Events", "End Turn Events", GamePhase.END_TURN_PHASE)
            ]
            
            phase_num = 2
            for current_phase_label, executing_phase_label, expected_next_phase in phases_to_execute:
                pygame.time.wait(delay_ms // 2)
                
                # Capture state BEFORE advancing
                # Note: _advance_to_next_phase() executes the CURRENT phase logic, then advances
                old_merchant_pos = game.ships[0].position if game.ships and game.ships[0].ship_type == 'merchant' else None
                old_dl = game.detection_level
                escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
                old_escort_pos = escorts[0].position if escorts else None
                
                # Suppress [EVENT] and [DEBUG] output and advance phase
                # This will execute the logic for the CURRENT phase, then advance to next
                suppressed_output = StringIO()
                old_stdout = sys.stdout
                sys.stdout = suppressed_output
                
                try:
                    game._advance_to_next_phase()
                    sys.stdout = old_stdout
                    
                    stats['phases_executed'] += 1
                    
                    # Now check what changed (get fresh references)
                    new_merchant_pos = game.ships[0].position if game.ships and game.ships[0].ship_type == 'merchant' else None
                    new_escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
                    new_escort_pos = new_escorts[0].position if new_escorts else None
                    
                    # Print results of the phase we just executed
                    # Skip U-Boat cleanup - it's not useful to show
                    if executing_phase_label == "U-Boat cleanup":
                        # Just cleanup, don't print anything
                        pass
                    
                    elif executing_phase_label == "Merchant":
                        print(f"Phase {phase_num} ({executing_phase_label}):", end=" ")
                        # Compare before/after the merchant phase execution
                        if new_merchant_pos and old_merchant_pos and new_merchant_pos != old_merchant_pos:
                            print(f"Merchant moved {old_merchant_pos} -> {new_merchant_pos}")
                        elif new_merchant_pos:
                            # Check if merchant AI message indicates why it didn't move
                            output_lines = suppressed_output.getvalue().split('\n')
                            merchant_msg = [line for line in output_lines if 'Merchant' in line and ('rolled' in line or 'cannot move' in line)]
                            if merchant_msg:
                                msg = merchant_msg[0].replace('[EVENT]', '').strip()
                                print(msg)
                            else:
                                print(f"Merchant stayed at {new_merchant_pos}")
                        else:
                            print("No merchants")
                        phase_num += 1
                    
                    elif executing_phase_label == "Detection":
                        print(f"Phase {phase_num} ({executing_phase_label}):", end=" ")
                        # Show detection calculation details from suppressed output
                        output_lines = suppressed_output.getvalue().split('\n')
                        # Look for dice rolls or detection results
                        detection_rolls = [line for line in output_lines if 'rolled' in line.lower() and ('detection' in line.lower() or 'corvette' in line.lower() or 'destroyer' in line.lower())]
                        
                        if game.detection_level != old_dl:
                            if detection_rolls:
                                roll_info = detection_rolls[0].replace('[EVENT]', '').strip()
                                print(f"DETECTED! ({roll_info}) DL: {old_dl}->{game.detection_level}")
                            else:
                                print(f"DETECTED! DL: {old_dl} -> {game.detection_level}")
                        elif detection_rolls:
                            # Show roll even if not detected
                            roll_info = detection_rolls[0].replace('[EVENT]', '').strip()
                            print(f"{roll_info} - Not detected (DL: {game.detection_level})")
                        else:
                            # Explain why no detection
                            escorts = [s for s in game.ships if s.ship_type in ['corvette', 'destroyer']]
                            if not escorts:
                                print(f"No escorts present (DL: {game.detection_level})")
                            else:
                                # Check if escorts are in range (within 3 hexes with LOS)
                                print(f"No detection attempts - escorts out of range/LOS (DL: {game.detection_level})")
                        phase_num += 1
                    
                    elif executing_phase_label == "Escort":
                        print(f"Phase {phase_num} ({executing_phase_label}):", end=" ")
                        # Show all escort actions from output
                        output_lines = suppressed_output.getvalue().split('\n')
                        # Look for dice roll and actions
                        dice_roll = [line for line in output_lines if 'Rolled' in line and 'dice' in line]
                        actions = [line for line in output_lines if any(x in line for x in ['MOVE:', 'TURN:', 'FIRE:', 'DEPTH CHARGE:'])]
                        
                        # Extract damage results (look for indented result lines after attacks)
                        damage_lines = []
                        for i, line in enumerate(output_lines):
                            stripped = line.replace('[EVENT]', '').strip()
                            # Look for result lines (indented, contain damage keywords)
                            if stripped and any(keyword in stripped.lower() for keyword in ['hull damage', 'crew casualty', 'no damage', 'miss', 'hit', 'damaged']):
                                # Exclude lines that are action declarations
                                if not any(x in stripped for x in ['DEPTH CHARGE:', 'FIRE:', 'MOVE:', 'TURN:', 'Rolled', 'Die']):
                                    damage_lines.append(stripped)
                        
                        if dice_roll:
                            # Show dice and summarize actions
                            print(dice_roll[0].replace('[EVENT]', '').strip(), end="")
                            if actions:
                                # Clean up actions - remove [EVENT] and extra whitespace, abbreviate
                                clean_actions = []
                                for a in actions[:5]:  # Show up to 5 actions
                                    action = a.replace('[EVENT]', '').split(':')[0].strip()
                                    # Abbreviate for readability
                                    if 'DEPTH CHARGE' in action:
                                        clean_actions.append('DC')
                                    elif 'FIRE' in action:
                                        clean_actions.append('FIRE!')  # Emphasize gunfire attacks
                                    else:
                                        clean_actions.append(action)
                                print(f" -> {', '.join(clean_actions)}", end="")
                            # Show final position and facing
                            if new_escorts:
                                escort = new_escorts[0]
                                print(f" @{escort.position} facing {escort.facing.name}")
                            else:
                                print()
                            
                            # Show damage results if any
                            if damage_lines:
                                for dmg_line in damage_lines[:2]:  # Show first 2 damage results
                                    clean_dmg = dmg_line.replace('[EVENT]', '').strip()
                                    if clean_dmg:
                                        print(f"         {clean_dmg}")
                        elif new_escort_pos and old_escort_pos and new_escort_pos != old_escort_pos:
                            escort_type = new_escorts[0].ship_type if new_escorts else "Escort"
                            facing = new_escorts[0].facing.name if new_escorts else "?"
                            print(f"{escort_type.capitalize()} moved {old_escort_pos} -> {new_escort_pos} facing {facing}")
                        else:
                            print("No escort activity")
                        phase_num += 1
                    
                    elif executing_phase_label == "B-24 Aircraft":
                        print(f"Phase {phase_num} ({executing_phase_label}):", end=" ")
                        # Check if B-24 is active
                        if hasattr(game, 'b24') and game.b24:
                            print("B-24 active")
                        else:
                            print("No B-24 present")
                        phase_num += 1
                    
                    elif executing_phase_label == "End Turn Events":
                        print(f"Phase {phase_num} ({executing_phase_label}):", end=" ")
                        # Look for event roll and descriptions
                        output_lines = suppressed_output.getvalue().split('\n')
                        event_rolls = [line for line in output_lines if 'Event Roll:' in line]
                        # Get event name/description - look for lines with "Event:" or "Effect:"
                        event_info = [line for line in output_lines if ('Event:' in line or 'Effect:' in line or 'Condition not met' in line)]
                        # Check for spawned aircraft
                        spawned_aircraft = [line for line in output_lines if 'Spawned' in line and 'aircraft' in line.lower()]
                        
                        # Check if DL changed from events
                        if game.detection_level != old_dl:
                            if event_rolls:
                                roll_value = event_rolls[0].replace('[EVENT]', '').split(':')[-1].strip().split()[0]  # Get just the number
                                event_desc = event_info[0].replace('[EVENT]', '').strip() if event_info else "Detection level change"
                                print(f"Roll {roll_value}: {event_desc} -> DL: {old_dl}->{game.detection_level}")
                            else:
                                print(f"DL: {old_dl} -> {game.detection_level}")
                        elif spawned_aircraft:
                            # Show spawned aircraft
                            roll_value = event_rolls[0].replace('[EVENT]', '').split(':')[-1].strip().split()[0] if event_rolls else "?"
                            aircraft_desc = spawned_aircraft[0].replace('[EVENT]', '').strip()
                            print(f"Roll {roll_value}: {aircraft_desc}")
                        elif event_rolls:
                            roll_value = event_rolls[0].replace('[EVENT]', '').split(':')[-1].strip().split()[0]  # Get just the number
                            event_desc = event_info[0].replace('[EVENT]', '').strip() if event_info else "No event"
                            # Check if this was a B-24 event that didn't meet condition
                            if 'B24' in event_desc or 'B-24' in event_desc:
                                event_desc += " (condition not met)"
                            print(f"Roll {roll_value}: {event_desc}")
                        else:
                            print("No events")
                        phase_num += 1
                    
                    # End Turn Phase doesn't have a separate label in phases_to_execute anymore
                    # It's handled at the end of turn below
                    
                except Exception as e:
                    sys.stdout = old_stdout
                    print(f"ERROR: {e}")
                    raise
                
                # Check for game-ending conditions
                if not game.ships:
                    sys.stdout = old_stdout
                    print("\n\n*** ALL SHIPS DESTROYED - MISSION SUCCESS! ***")
                    stats['mission_success'] = True
                    return stats
                
                if game.u_boat.hull_damage >= 3:
                    sys.stdout = old_stdout
                    print("\n\n*** U-BOAT DESTROYED - MISSION FAILED! ***")
                    stats['mission_failed'] = True
                    return stats
            
            # Wrap to next turn
            suppressed_output = StringIO()
            old_stdout = sys.stdout
            sys.stdout = suppressed_output
            game._advance_to_next_phase()
            sys.stdout = old_stdout
            
            # Show turn summary with prominent DL display
            merchant_pos = game.ships[0].position if game.ships and game.ships[0].ship_type == 'merchant' else None
            print(f"\n  Turn {turn} End: U-Boat at {game.u_boat.position} ({game.u_boat.depth.name}), Hull {game.u_boat.hull_damage}/3")
            print(f"              *** DETECTION LEVEL: {game.detection_level} ***")
            print(f"              Ships remaining: {len(game.ships)}")
            if merchant_pos:
                print(f"              Merchant at: {merchant_pos}")
            
            # Store DL for next turn (ensure persistence)
            old_dl = game.detection_level
            
            stats['turns_completed'] += 1
            
            # Pause between turns
            pygame.time.wait(delay_ms)
        
        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n*** EXCEPTION OCCURRED ***")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        stats['errors'].append(f"Exception: {str(e)}")
    
    finally:
        # Print statistics
        print(f"\n{'='*80}")
        print("STATISTICS")
        print(f"{'='*80}")
        print(f"Turns completed: {stats['turns_completed']}/{num_turns}")
        print(f"Total actions taken: {stats['total_actions']}")
        print(f"Phases executed: {stats['phases_executed']}")
        print(f"Current turn: {game.turn_manager.turn_number}")
        print(f"Current phase: {game.turn_manager.get_current_phase_name()}")
        print(f"Detection Level: {game.detection_level}")
        print(f"U-Boat status:")
        print(f"  Position: {game.u_boat.position}")
        print(f"  Depth: {game.u_boat.depth.name}")
        print(f"  Facing: {game.u_boat.facing.name}")
        print(f"  Hull Damage: {game.u_boat.hull_damage}/3")
        print(f"  Torpedoes: {sum(game.u_boat.torpedo_tubes)}/5 loaded")
        print(f"  Deck Gun: {'Damaged' if game.u_boat.deck_gun_damaged else 'Ready'}")
        print(f"Ships remaining: {len(game.ships)}")
        
        if stats['errors']:
            print(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        
        print(f"{'='*80}\n")
        
        pygame.quit()
    
    return stats


if __name__ == "__main__":
    import sys
    
    # Check for command line args
    verbose_mode = "--verbose" in sys.argv or "-v" in sys.argv
    
    # Run test with 10 turns, 200ms delay between phases
    run_ai_test(num_turns=10, delay_ms=200, verbose=verbose_mode)
