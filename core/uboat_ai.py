"""
AI U-Boat Captain for automated testing and gameplay.

Makes random tactical decisions to test game systems.
Uses ActionCatalog to query available actions from centralized rule logic.
"""

from typing import List, Tuple, Optional, Any
import random
from .models import UBoat, Ship, Depth, Facing
from .action_catalog import ActionCatalog
from .action_costs import ActionCostLookup
from .movement_validator import MovementValidator
from .depth_validator import DepthValidator
from .torpedo_validator import TorpedoValidator
from .repair_validator import RepairValidator


class UBoatAI:
    """AI controller for U-boat during testing/automated gameplay."""
    
    def __init__(self, game_state: Any):
        """
        Initialize AI captain.
        
        Args:
            game_state: Reference to main Game instance
        """
        self.game = game_state
        self.turn_count = 0
    
    def execute_turn(self) -> Tuple[bool, List[str]]:
        """
        Execute a full AI turn in Phase 1 (U-Boat Phase).
        
        Returns:
            Tuple of (success, messages)
        """
        messages: List[str] = []
        
        # Roll for AP if not already rolled
        if self.game.turn_manager.ap_tracker is None:
            ap = self.game.turn_manager.roll_action_points_only(self.game.u_boat)
            self.game.u_boat.action_points = ap
            self.game.action_queue.reset_for_new_turn(ap)
            messages.append(f"AI rolled {ap} AP")
        
        # Plan and queue actions
        actions_queued = self._plan_actions()
        messages.extend(actions_queued)
        
        # Commit all queued actions
        if self.game.action_queue.actions:
            results = self.game.action_queue.commit_all(self.game)
            for result in results:
                if result.success:
                    messages.append(f"[OK] {result.message}")
                else:
                    messages.append(f"[FAIL] {result.message}")
            
            remaining = self.game.action_queue.get_remaining_ap(self.game)
            messages.append(f"Turn complete: {remaining} AP remaining")
        else:
            messages.append("No actions taken this turn")
        
        self.turn_count += 1
        return True, messages
    
    def _plan_actions(self) -> List[str]:
        """
        Plan and queue a set of random actions using ActionCatalog.
        
        Returns:
            List of messages about queued actions
        """
        messages: List[str] = []
        max_attempts = 50
        attempts = 0
        actions_added = 0
        
        # Try to use most of our AP (aim for 50%+ utilization)
        target_actions = max(3, self.game.action_queue.get_remaining_ap(self.game) // 2)
        
        # Create action cost lookup and validators
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        movement_validator = MovementValidator(
            land_hexes=self.game.land_hexes,
            shallow_hexes=self.game.shallow_hexes,
            mission_hexes=self.game.mission_hexes
        )
        depth_validator = DepthValidator(shallow_hexes=self.game.shallow_hexes)
        torpedo_validator = TorpedoValidator()
        repair_validator = RepairValidator()
        
        # Create action catalog
        catalog = ActionCatalog(
            cost_lookup=cost_lookup,
            movement_validator=movement_validator,
            depth_validator=depth_validator,
            torpedo_validator=torpedo_validator,
            repair_validator=repair_validator,
            mission_rules=self.game.mission_rules,
            land_hexes=self.game.land_hexes,
            shallow_hexes=self.game.shallow_hexes,
            hex_grid=self.game.hex_grid,
            dice_roller=self.game.turn_manager.dice,
            mission_hexes=self.game.mission_hexes
        )
        
        # Keep trying to add actions until we can't afford any more
        while attempts < max_attempts and actions_added < target_actions:
            attempts += 1
            
            # Get remaining AP
            remaining_ap = self.game.action_queue.get_remaining_ap(self.game)
            if remaining_ap <= 0:
                break
            
            # Get all available actions from catalog
            available_actions = catalog.get_available_actions(self.game)
            
            if not available_actions:
                # No valid actions available
                continue
            
            # Randomly choose one available action
            chosen = random.choice(available_actions)
            
            # Try to add it to queue
            success, message = self.game.action_queue.add_action(chosen.action, self.game)
            if success:
                actions_added += 1
            else:
                # Action failed, try a different one
                continue
        
        return messages
