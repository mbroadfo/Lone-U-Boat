"""
Test script to simulate deck gun gameplay scenario.
Simulates: Turn 1 (setup) -> Turn 2 (deck gun, move, deck gun again)
Captures UI state for inspection.
"""

import pygame
from typing import Optional
from core.screens.unified_game import UnifiedGameScreen
from core.models import Depth, Facing
from core.dice import DiceRoller


def capture_ui_state(screen: UnifiedGameScreen, label: str):
    """Capture and print the current UI state."""
    import sys
    
    # Ensure UTF-8 encoding for console output
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "="*80)
    print(f"UI STATE: {label}")
    print("="*80)
    
    # Dice Rolls
    print("\n[DICE ROLLS]")
    if hasattr(screen.game.turn_manager, 'last_ap_roll') and screen.game.turn_manager.last_ap_roll:
        roll_info = screen.game.turn_manager.last_ap_roll
        print(f"  Turn: {screen.game.turn_manager.turn_number}")
        print(f"  Rolls: {roll_info['rolls']}")
        print(f"  Highest: {roll_info['highest']}")
        print(f"  Captain Bonus: {roll_info.get('captain_bonus', 0)}")
        print(f"  Total AP: {roll_info['total_ap']}")
    else:
        print("  No dice rolled yet")
    
    # Action Queue
    print("\n[ACTION QUEUE]")
    print(f"  AP: {screen.game.u_boat.action_points}/{screen.game.action_queue.max_ap}")
    if screen.game.action_queue.actions:
        for i, action in enumerate(screen.game.action_queue.actions, 1):
            action_type = type(action).__name__.replace('Action', '')
            print(f"  {i}. {action_type}")
    else:
        print("  No actions queued")
    
    # U-Boat State
    print("\n[U-BOAT STATE]")
    print(f"  Position: {screen.game.u_boat.position}")
    print(f"  Facing: {screen.game.u_boat.facing.name}")
    print(f"  Depth: {screen.game.u_boat.depth.name}")
    
    # Ships in Range
    print("\n[SHIPS IN RANGE FOR DECK GUN]")
    from core.hex_grid import HexGrid
    from core.los import LOSCalculator
    
    los_calc = LOSCalculator(screen.game.land_hexes)
    for ship in screen.game.ships:
        distance = HexGrid.hex_distance(screen.game.u_boat.position, ship.position)
        if 1 <= distance <= 3:  # Deck gun range is 1-3
            has_los, _ = los_calc.has_line_of_sight(
                screen.game.u_boat.position,
                ship.position
            )
            status = "IN RANGE + LOS" if has_los else "IN RANGE (no LOS)"
            damaged_status = " [DAMAGED]" if ship.damaged else ""
            print(f"  {ship.ship_type} at {ship.position}: {status} (distance {distance}){damaged_status}")
    
    # Deck Gun Resolution State
    print("\n[DECK GUN RESOLUTION]")
    if screen.deck_gun_resolution_state:
        state = screen.deck_gun_resolution_state
        print(f"  Active: YES")
        print(f"  Current Target: {state['current_idx'] + 1}/{len(state['targets'])}")
        print(f"  Waiting For: {state['waiting_for']}")
        if state.get('last_hit_roll'):
            roll = state['last_hit_roll']
            print(f"  Last Hit Roll: Rolled {roll['total']} - {roll['description']} - {'HIT' if roll['hit'] else 'MISS'}")
        if state.get('last_damage_roll'):
            dmg = state['last_damage_roll']
            print(f"  Last Damage Roll: {dmg['description']}")
        # Show all results so far
        if state.get('results'):
            print(f"  Results So Far: {len(state['results'])} targets resolved")
            for ship, dist, hit, dmg in state['results']:
                if hit:
                    print(f"    - {ship.ship_type} at range {dist}: HIT (damage die: {dmg})")
                else:
                    print(f"    - {ship.ship_type} at range {dist}: MISS")
    else:
        print("  Active: NO")
    
    # Event Log (last 20 events to see full combat narrative)
    print("\n[EVENT LOG - Last 20 events]")
    for event in screen.event_log[-20:]:
        print(f"  {event}")
    
    print("\n" + "="*80 + "\n")


def capture_combat_step(label: str, screen: UnifiedGameScreen):
    """Capture just the combat resolution step without full UI dump."""
    print(f"\n  {label}")
    if screen.deck_gun_resolution_state:
        state = screen.deck_gun_resolution_state
        print(f"    Target {state['current_idx'] + 1}/{len(state['targets'])} | Waiting: {state['waiting_for']}")
        if state.get('last_hit_roll'):
            roll = state['last_hit_roll']
            print(f"    → {'HIT' if roll['hit'] else 'MISS'} (rolled {roll['total']})")
        if state.get('last_damage_roll'):
            dmg = state['last_damage_roll']
            print(f"    → {dmg['description']}")


def simulate_scenario():
    """Simulate the full gameplay scenario."""
    print("Starting deck gun test scenario...")
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    
    # Create a mock screen manager
    class MockScreenManager:
        def __init__(self, screen: pygame.Surface) -> None:
            self.screen = screen
            self.fullscreen = False
    
    screen_manager = MockScreenManager(screen)
    
    # Mock dice roller for guaranteed hits on second deck gun
    class MockDice:
        def __init__(self, real_dice: DiceRoller) -> None:
            self.real_dice = real_dice
            self.combat_roll_count = 0
            self.hit_rolls = [8, 9]  # Guaranteed hits: 8 for range 2, 9 for range 3
            # Damage rolls: 5 = catastrophic (sunk), 6 = catastrophic (sunk), 4 = damaged
            self.damage_rolls = [5, 6, 4]  # First two should sink ships, third damages
        
        def roll_highest(self, num_dice: int, sides: int = 6, context: Optional[str] = None) -> tuple[int, list[int]]:
            """Delegate to real dice for AP rolls."""
            return self.real_dice.roll_highest(num_dice, sides, context or "")
        
        def roll_2d6(self) -> int:
            """Return guaranteed hit values for second deck gun attack."""
            if self.combat_roll_count < len(self.hit_rolls):
                result = self.hit_rolls[self.combat_roll_count]
                self.combat_roll_count += 1
                return result
            return 8  # Default to hit
        
        def roll_1d6(self) -> int:
            """Return damage rolls."""
            damage_idx = self.combat_roll_count - len(self.hit_rolls)
            if 0 <= damage_idx < len(self.damage_rolls):
                return self.damage_rolls[damage_idx]
            return 5  # Default to catastrophic damage
        
        def roll(self, num_dice: int) -> int:
            """Called by ShipDamageResolver - delegate to roll_1d6."""
            return self.roll_1d6()
    
    # Create unified game screen for mission 1
    from core.game_state import Game
    from config import board_config
    
    game = Game(mission_number=1, screen=screen)
    unified_screen = UnifiedGameScreen(
        screen_manager=screen_manager,
        config=board_config,
        mission_number=1,
        game_instance=game
    )
    
    # Replace the dice roller with our mock for guaranteed hits
    real_dice = unified_screen.game.turn_manager.dice
    mock_dice = MockDice(real_dice)
    unified_screen.game.turn_manager.dice = mock_dice  # type: ignore
    
    print("\n### INITIAL SETUP ###")
    
    # Setup: Rotate left once, then start at SURFACED, NORTHWEST
    unified_screen.selected_facing = Facing.NORTHWEST
    unified_screen.selected_depth = Depth.SURFACED
    unified_screen.awaiting_initial_setup = False
    unified_screen.game.u_boat.facing = Facing.NORTHWEST
    unified_screen.game.u_boat.depth = Depth.SURFACED
    
    capture_ui_state(unified_screen, "After Initial Setup")
    
    # Turn 1: Roll dice - need 5 AP for 4 moves + 1 rotate
    print("\n### TURN 1: ROLL DICE ###")
    unified_screen.game.turn_manager.start_new_turn(unified_screen.game.u_boat)
    # Override to ensure we have 5 AP for the scenario
    assert unified_screen.game.turn_manager.last_ap_roll is not None
    unified_screen.game.turn_manager.last_ap_roll['total_ap'] = 5
    unified_screen.game.u_boat.action_points = 5
    unified_screen.game.action_queue.max_ap = 5
    
    capture_ui_state(unified_screen, "After Rolling Dice")
    
    # Turn 1: Queue 4 moves + 1 rotate left
    print("\n### TURN 1: QUEUE ACTIONS (4x MOVE + 1x ROTATE LEFT to face SOUTHWEST) ###")
    for i in range(4):
        unified_screen._queue_action("move")  # type: ignore[attr-defined]
    unified_screen._queue_action("rotate_l")  # type: ignore[attr-defined]
    
    capture_ui_state(unified_screen, "After Queuing Turn 1 Actions")
    
    # Turn 1: Commit
    print("\n### TURN 1: COMMIT ACTIONS ###")
    _ = unified_screen.game.action_queue.commit_all(unified_screen.game)
    unified_screen.game.action_queue.clear()
    
    # Clear event log to avoid clutter in Turn 2
    unified_screen.event_log = ["Turn 1 completed - U-boat moved and rotated to SOUTHWEST", "Starting Turn 2..."]
    
    capture_ui_state(unified_screen, "After Committing Turn 1")
    
    # Turn 2: Roll dice
    print("\n### TURN 2: ROLL DICE ###")
    from core.models import GamePhase
    from core.actions import ActionQueue
    
    unified_screen.game.turn_manager.turn_number += 1
    unified_screen.game.turn_manager.current_phase = GamePhase.UBOAT_PHASE
    unified_screen.game.turn_manager.start_new_turn(unified_screen.game.u_boat)
    assert unified_screen.game.turn_manager.last_ap_roll is not None
    unified_screen.game.u_boat.action_points = unified_screen.game.turn_manager.last_ap_roll['total_ap']
    unified_screen.game.action_queue = ActionQueue(
        max_ap=unified_screen.game.u_boat.action_points
    )
    
    capture_ui_state(unified_screen, "Turn 2 - After Rolling Dice")
    
    # Turn 2: Queue deck gun, move, deck gun
    print("\n### TURN 2: QUEUE ACTIONS (DECK GUN -> MOVE -> DECK GUN) ###")
    unified_screen._queue_action("deck_gun")  # type: ignore[attr-defined]
    unified_screen._queue_action("move")  # type: ignore[attr-defined]
    unified_screen._queue_action("deck_gun")  # type: ignore[attr-defined]
    
    capture_ui_state(unified_screen, "Turn 2 - After Queuing Actions")
    
    # Turn 2: Commit (triggers first deck gun interactive resolution)
    print("\n### TURN 2: COMMIT - FIRST DECK GUN RESOLUTION STARTS ###")
    # Simulate clicking commit button
    from core.actions.deck_gun_action import DeckGunAction
    has_deck_gun = any(isinstance(action, DeckGunAction) for action in unified_screen.game.action_queue.actions)
    
    if has_deck_gun:
        for i, action in enumerate(unified_screen.game.action_queue.actions):
            if isinstance(action, DeckGunAction):
                from core.los import LOSCalculator
                from core.hex_grid import HexGrid
                from typing import List, Tuple
                from core.models import Ship
                
                los_calc = LOSCalculator(unified_screen.game.land_hexes)
                current_targets: List[Tuple[Ship, int]] = []
                for ship in unified_screen.game.ships:
                    distance = HexGrid.hex_distance(unified_screen.game.u_boat.position, ship.position)
                    if 1 <= distance <= 3:
                        has_los, _ = los_calc.has_line_of_sight(
                            unified_screen.game.u_boat.position,
                            ship.position
                        )
                        if has_los:
                            current_targets.append((ship, distance))
                
                import random
                current_targets.sort(key=lambda x: (x[1], random.random()))
                
                unified_screen.deck_gun_resolution_state = {
                    'action': action,
                    'action_index': i,
                    'targets': current_targets,
                    'current_idx': 0,
                    'waiting_for': 'hit',
                    'last_hit_roll': None,
                    'last_damage_roll': None,
                    'results': []
                }
                unified_screen.add_event("=== DECK GUN ATTACK ===")
                break
    
    capture_ui_state(unified_screen, "Turn 2 - First Deck Gun Resolution Started")
    
    # Simulate resolution for FIRST deck gun (before move) - should only have 1 target
    print("\n### TURN 2: FIRST DECK GUN - RESOLVE ALL TARGETS ###")
    while unified_screen.deck_gun_resolution_state:
        state = unified_screen.deck_gun_resolution_state
        waiting_for = state['waiting_for']
        current_idx = state['current_idx']
        total_targets = len(state['targets'])
        
        if waiting_for == 'hit':
            unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
            capture_combat_step(f"Target {current_idx + 1}/{total_targets}: Hit roll", unified_screen)
        elif waiting_for == 'damage':
            unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
            capture_combat_step(f"Target {current_idx + 1}/{total_targets}: Damage roll", unified_screen)
        elif waiting_for == 'continue':
            unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
            print(f"  Target {current_idx + 1}/{total_targets}: Continuing to next target...")
        else:
            break
    
    print("\n### TURN 2: FIRST DECK GUN RESOLUTION COMPLETE ###")
    capture_ui_state(unified_screen, "Turn 2 - After First Deck Gun Complete")
    
    # Now the MOVE should have executed and we're on the SECOND deck gun
    # The second deck gun should have 2 targets (merchant and corvette both in range after move)
    if unified_screen.deck_gun_resolution_state:
        print("\n### TURN 2: SECOND DECK GUN - RESOLVE ALL TARGETS ###")
        while unified_screen.deck_gun_resolution_state:
            state = unified_screen.deck_gun_resolution_state
            waiting_for = state['waiting_for']
            current_idx = state['current_idx']
            total_targets = len(state['targets'])
            
            if waiting_for == 'hit':
                unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
                capture_combat_step(f"Target {current_idx + 1}/{total_targets}: Hit roll", unified_screen)
            elif waiting_for == 'damage':
                unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
                capture_combat_step(f"Target {current_idx + 1}/{total_targets}: Damage roll", unified_screen)
            elif waiting_for == 'continue':
                unified_screen._handle_deck_gun_roll()  # type: ignore[attr-defined]
                print(f"  Target {current_idx + 1}/{total_targets}: Continuing to next target...")
            else:
                break
        
        print("\n### TURN 2: SECOND DECK GUN RESOLUTION COMPLETE ###")
        capture_ui_state(unified_screen, "Turn 2 - After Second Deck Gun Complete")
    
    print("\n### TEST SCENARIO COMPLETE ###")
    print("\n[FINAL SHIP STATUS]")
    if not unified_screen.game.ships:
        print("  All ships SUNK!")
    else:
        for ship in unified_screen.game.ships:
            damaged_text = "DAMAGED" if ship.damaged else "intact"
            print(f"  {ship.ship_type} at {ship.position}: {damaged_text}")
    
    print("\nYou can now inspect the captured UI states above.")
    print("Look for:")
    print("  - Ships in range before/after move")
    print("  - Action queue state")
    print("  - Deck gun resolution state (hit/miss/damage rolls)")
    print("  - Event log progression showing hit/miss/damage results")
    print("  - Final ship damage/sunk status")
    print("  - Ship removal from map when sunk")
    
    pygame.quit()


if __name__ == "__main__":
    try:
        simulate_scenario()
    except Exception as e:
        import traceback
        print(f"\nERROR: {e}")
        print(traceback.format_exc())
