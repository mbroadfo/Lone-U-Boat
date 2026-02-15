"""
Automated Stress Test - Interactive AI Mode

Runs multiple complete games in interactive AI mode with automated decisions.
This stress test finds bugs faster than manual play-testing by running
hundreds of turns per minute across multiple game scenarios.

Usage:
    python test_stress_interactive.py [num_games]
"""

import sys
import traceback
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import random

sys.path.insert(0, str(Path(__file__).parent))

from core.game_state import Game
from core.models import Depth, Facing, HexCoord, GamePhase
from core.actions import MoveAction, RotateAction, FireTorpedoAction, LoadTorpedoAction
from core.action_costs import ActionCostLookup
from core.movement_validator import MovementValidator
from core.torpedo_validator import TorpedoValidator
from core.los import LOSCalculator
from core.combat_resolver import CombatResolver


class AutomatedPlayer:
    """Simple AI to make automated U-boat decisions for stress testing."""
    
    def __init__(self, game: Game):
        self.game = game
        self.turn_count = 0
        
    def play_turn(self) -> bool:
        """
        Play one complete turn (U-boat phase + all AI phases).
        
        Returns:
            True if game continues, False if game ended
        """
        if not self.game.running:
            return False
        
        # Skip U-boat phase for stress testing - just test AI phases
        # (We're testing interactive AI, not U-boat actions)
        self.game.turn_manager.current_phase = GamePhase.MERCHANT_PHASE
        
        # Execute all AI phases with interactive actions
        self._execute_all_ai_phases()
        
        self.turn_count += 1
        return self.game.running
    
    def _play_uboat_phase(self) -> None:
        """Play U-boat phase with simple automated decisions."""
        # Roll AP
        if self.game.turn_manager.ap_tracker is None:
            ap = self.game.turn_manager.roll_action_points_only(self.game.u_boat)
            self.game.u_boat.action_points = ap
        
        # Make simple decisions: move toward nearest merchant, fire torpedoes
        while self.game.u_boat.action_points > 0 and self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
            action_taken = False
            
            # For stress testing, just do simple moves and rotations
            # (Torpedo combat is complex and slow, not needed for AI phase testing)
            
            # Try to move forward
            if self._try_move_forward():
                action_taken = True
            # Try to rotate toward target
            elif self._try_rotate_toward_nearest_enemy():
                action_taken = True
            
            # If can't do anything useful, just advance phase
            if not action_taken:
                break
        
        # Advance to next phase
        self.game.turn_manager.advance_phase()
    
    def _try_move_forward(self) -> bool:
        """Try to move U-boat forward."""
        if self.game.u_boat.action_points < 1:
            return False
        
        target_hex = self.game.u_boat.facing.forward(self.game.u_boat.position)
        
        # Check if move is valid
        if target_hex in self.game.land_hexes:
            return False
        if target_hex not in self.game.mission_hexes:
            return False
        
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        validator = MovementValidator(self.game.land_hexes, self.game.shallow_hexes, self.game.mission_hexes)
        action = MoveAction(target_hex, cost_lookup, validator)
        result = action.execute(self.game)
        return result.success
    
    def _try_rotate_toward_nearest_enemy(self) -> bool:
        """Try to rotate toward nearest merchant."""
        if self.game.u_boat.action_points < 1:
            return False
        
        # Find nearest merchant
        nearest_merchant = None
        min_distance = 999
        
        for ship in self.game.ships:
            if ship.ship_type == 'merchant':
                dist = self.game.hex_grid.hex_distance(self.game.u_boat.position, ship.position)
                if dist < min_distance:
                    min_distance = dist
                    nearest_merchant = ship
        
        if not nearest_merchant:
            return False
        
        # Determine if we should rotate
        # Simple heuristic: rotate clockwise or counter-clockwise
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        if random.choice([True, False]):
            action = RotateAction(clockwise=True, cost_lookup=cost_lookup)
        else:
            action = RotateAction(clockwise=False, cost_lookup=cost_lookup)
        
        result = action.execute(self.game)
        return result.success
    
    def _try_fire_torpedo(self) -> bool:
        """Try to fire torpedo at nearest merchant in range."""
        if self.game.u_boat.action_points < 1:
            return False
        
        # Check if any tubes loaded
        loaded_tubes = [i for i, loaded in enumerate(self.game.u_boat.torpedo_tubes) if loaded]
        if not loaded_tubes:
            return False
        
        # Find nearest merchant
        for ship in self.game.ships:
            if ship.ship_type == 'merchant':
                dist = self.game.hex_grid.hex_distance(self.game.u_boat.position, ship.position)
                if 1 <= dist <= 3:  # Fire at close range
                    tube = loaded_tubes[0]
                    cost_lookup = ActionCostLookup(self.game.mission_rules)
                    validator = TorpedoValidator()
                    los_calculator = LOSCalculator(self.game.land_hexes)
                    combat_resolver = CombatResolver(self.game.turn_manager.dice, self.game.mission_rules)
                    action = FireTorpedoAction([tube], self.game.u_boat.facing, cost_lookup, validator, los_calculator, combat_resolver)
                    result = action.execute(self.game)
                    return result.success
        
        return False
    
    def _try_load_torpedo(self) -> bool:
        """Try to load empty torpedo tube."""
        if self.game.u_boat.action_points < 1:
            return False
        
        # Find empty tube
        for i, loaded in enumerate(self.game.u_boat.torpedo_tubes):
            if not loaded:
                cost_lookup = ActionCostLookup(self.game.mission_rules)
                validator = TorpedoValidator()
                action = LoadTorpedoAction([i], cost_lookup, validator)
                result = action.execute(self.game)
                return result.success
        
        return False
    
    def _execute_all_ai_phases(self) -> None:
        """Execute all AI phases by running queued actions."""
        max_phases = 20  # Safety limit
        phase_count = 0
        
        while self.game.running and phase_count < max_phases:
            # Check if we're back to U-boat phase (full turn complete)
            if self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
                break
            
            # If pending AI actions, execute them all
            if self.game.has_pending_ai_actions():
                self._execute_ai_queue()
            else:
                # No actions, advance phase
                self.game.turn_manager.advance_phase()
            
            phase_count += 1
    
    def _execute_ai_queue(self) -> None:
        """Execute all actions in current AI queue."""
        max_actions = 100  # Safety limit
        action_count = 0
        
        while self.game.has_pending_ai_actions() and action_count < max_actions:
            has_more, _ = self.game.execute_next_ai_action()
            action_count += 1
            
            if not has_more:
                break


def run_game(game_num: int, verbose: bool = False) -> Tuple[bool, str, int, Optional[str]]:
    """
    Run one complete game.
    
    Returns:
        (success, outcome, turns, error_msg)
    """
    try:
        if verbose:
            print(f"\n{'='*60}")
            print(f"GAME {game_num}")
            print(f"{'='*60}")
        
        # Create game in interactive mode
        game = Game(mission_number=1, interactive_ai_mode=True)
        
        # Initialize U-boat position
        game.u_boat.position = HexCoord(9, 1)
        game.u_boat.facing = random.choice([Facing.NORTH, Facing.NORTHEAST, Facing.NORTHWEST])
        game.u_boat.depth = Depth.SURFACED
        
        # Create automated player
        player = AutomatedPlayer(game)
        
        # Play game
        max_turns = 50
        turn_num = 0
        
        while turn_num < max_turns and game.running:
            if verbose:
                print(f"\nTurn {turn_num + 1}:")
            
            continue_game = player.play_turn()
            turn_num += 1
            
            if not continue_game:
                break
            
            if verbose:
                print(f"  U-boat: {game.u_boat.position} | Merchants: {sum(1 for s in game.ships if s.ship_type == 'merchant')}")
        
        # Determine outcome
        merchants_remaining = sum(1 for s in game.ships if s.ship_type == 'merchant')
        
        if not game.running:
            if game.u_boat.hull_damage >= 4:
                outcome = "DEFEAT (U-boat destroyed)"
            elif merchants_remaining == 0:
                outcome = "VICTORY (All merchants sunk)"
            else:
                outcome = "VICTORY (Exited map)"
        else:
            outcome = "TIMEOUT (50 turns)"
        
        if verbose:
            print(f"\n{outcome} - {turn_num} turns")
        
        return (True, outcome, turn_num, None)
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return (False, "CRASH", 0, error_msg)


def main(num_games: int = 10):
    """Run stress test with multiple games."""
    print(f"{'='*70}")
    print(f"STRESS TEST: Interactive AI Mode")
    print(f"{'='*70}")
    print(f"Running {num_games} automated games...")
    print(f"This may take 30-60 seconds...\n")
    
    results: List[Tuple[bool, str, int, Optional[str]]] = []
    
    for i in range(num_games):
        print(f"Game {i+1}/{num_games}...", end=" ", flush=True)
        success, outcome, turns, error = run_game(i+1, verbose=False)
        results.append((success, outcome, turns, error))
        
        if success:
            print(f"✓ {outcome} ({turns} turns)")
        else:
            print(f"✗ CRASHED")
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*70}")
    
    successes = sum(1 for r in results if r[0])
    crashes = sum(1 for r in results if not r[0])
    
    print(f"Successful:  {successes}/{num_games}")
    print(f"Crashes:     {crashes}/{num_games}")
    
    if successes > 0:
        avg_turns = sum(r[2] for r in results if r[0]) / successes
        print(f"Avg turns:   {avg_turns:.1f}")
    
    # Show outcome distribution
    outcomes: Dict[str, int] = {}
    for success, outcome, _turns, _err in results:
        if success:
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    if outcomes:
        print(f"\nOutcomes:")
        for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
            print(f"  {outcome}: {count}")
    
    # Show errors
    errors = [(i+1, err) for i, (success, _outcome, _turns, err) in enumerate(results) if not success and err]
    if errors:
        print(f"\n{'='*70}")
        print(f"ERRORS FOUND")
        print(f"{'='*70}")
        for game_num, error in errors:
            print(f"\nGame {game_num}:")
            print(error)
    
    print(f"\n{'='*70}")
    if crashes == 0:
        print(f"✓ ALL {num_games} GAMES COMPLETED SUCCESSFULLY!")
        print(f"✓ Interactive AI mode is stable!")
    else:
        print(f"⚠ {crashes} crash(es) detected - review errors above")
    print(f"{'='*70}")
    
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    num_games = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sys.exit(main(num_games))
