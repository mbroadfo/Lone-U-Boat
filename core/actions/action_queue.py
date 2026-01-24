"""
Action queue system for planning and executing player actions.

Allows players to plan multiple actions before committing the turn.
"""

from typing import List, Tuple, Optional, Any
from .base_action import Action, ActionResult


class ActionQueue:
    """
    Manage queued actions before committing turn.
    
    Players can:
    - Add actions to queue
    - Preview total AP cost
    - Undo last action
    - Commit all actions at once
    """
    
    def __init__(self, max_ap: int = 10):
        """
        Initialize action queue.
        
        Args:
            max_ap: Maximum action points available this turn
        """
        self.actions: List[Action] = []
        self.max_ap = max_ap
        self.spent_ap: int = 0  # Track total AP spent this turn
        self._committed = False
        self.action_history: List[Action] = []  # Track executed actions for statistics
    
    @property
    def is_committed(self) -> bool:
        """Check if actions have been committed."""
        return self._committed
    
    def add_action(self, action: Action, game_state: Any) -> Tuple[bool, str]:
        """
        Add action to queue if valid and affordable.
        
        Args:
            action: Action to add
            game_state: Current game state for validation
            
        Returns:
            (success, message)
        """
        if self._committed:
            return False, "Turn already committed"
        
        # Validate action
        can_perform, reason = action.validate(game_state)
        if not can_perform:
            return False, f"Invalid action: {reason}"
        
        # Check if we can afford it
        action_cost = action.get_cost(game_state.u_boat)
        total_cost = self.get_total_cost(game_state) + action_cost
        
        if total_cost > self.max_ap:
            return False, f"Not enough AP: need {action_cost}, have {self.max_ap - self.get_total_cost(game_state)} remaining"
        
        self.actions.append(action)
        return True, f"Added {action.get_description()} (AP: {action_cost})"
    
    def remove_last(self) -> Optional[Action]:
        """
        Remove and return last action from queue (undo).
        
        Returns:
            Removed action, or None if queue empty
        """
        if not self.actions:
            return None
        
        return self.actions.pop()
    
    def get_total_cost(self, game_state: Any) -> int:
        """
        Calculate total AP cost of all queued actions.
        Simulates depth changes to calculate accurate costs.
        
        Args:
            game_state: Current game state (depth affects costs)
            
        Returns:
            Total AP cost
        """
        from .depth_change_action import DepthChangeAction
        from ..models import UBoat
        
        total_cost = 0
        simulated_depth = game_state.u_boat.depth
        
        for action in self.actions:
            # Create temporary u_boat with simulated depth for cost calculation
            temp_uboat = UBoat(
                position=game_state.u_boat.position,
                facing=game_state.u_boat.facing,
                depth=simulated_depth,
                action_points=game_state.u_boat.action_points
            )
            
            # Get cost based on simulated state
            cost = action.get_cost(temp_uboat)
            total_cost += cost
            
            # Update simulated depth if this is a depth change action
            if isinstance(action, DepthChangeAction):
                simulated_depth = action.new_depth
        
        return total_cost
    
    def get_remaining_ap(self, game_state: Any) -> int:
        """
        Get remaining AP after queued actions.
        
        Args:
            game_state: Current game state
            
        Returns:
            Remaining action points
        """
        return self.max_ap - self.get_total_cost(game_state)
    
    def can_afford(self, game_state: Any) -> bool:
        """
        Check if queued actions are affordable.
        
        Args:
            game_state: Current game state
            
        Returns:
            True if total cost <= max_ap
        """
        return self.get_total_cost(game_state) <= self.max_ap
    
    def clear(self):
        """Clear all queued actions without marking as committed."""
        self.actions.clear()
    
    def reset_for_new_turn(self, new_max_ap: int):
        """Reset queue for a new turn with new AP allocation.
        
        Args:
            new_max_ap: Action points for the new turn
        """
        self.actions.clear()
        self.action_history.clear()  # Clear history for new turn
        self.max_ap = new_max_ap
        self.spent_ap = 0
        self._committed = False
    
    def commit_all(self, game_state: Any) -> List[ActionResult]:
        """
        Execute all queued actions in order.
        
        Args:
            game_state: Current game state (will be modified)
            
        Returns:
            List of action results
        """
        if self._committed:
            return [ActionResult(
                success=False,
                message="Turn already committed",
                ap_spent=0,
                state_changes={}
            )]
        
        if not self.can_afford(game_state):
            return [ActionResult(
                success=False,
                message=f"Cannot afford queued actions: {self.get_total_cost(game_state)} AP needed, {self.max_ap} available",
                ap_spent=0,
                state_changes={}
            )]
        
        results: List[ActionResult] = []
        total_cost = self.get_total_cost(game_state)
        
        for action in self.actions:
            result = action.execute(game_state)
            results.append(result)
            
            # Track executed action in history
            if result.success:
                self.action_history.append(action)
            
            # Stop executing if an action fails
            if not result.success:
                break
        
        # Deduct AP from available pool
        self.spent_ap += total_cost
        self.max_ap -= total_cost
        
        # Mark as committed and clear the queue
        self._committed = True
        self.actions.clear()
        
        return results
    
    def get_action_summary(self, game_state: Any) -> List[str]:
        """
        Get list of action descriptions for display.
        
        Args:
            game_state: Current game state
            
        Returns:
            List of action descriptions with costs
        """
        summaries: List[str] = []
        for action in self.actions:
            cost = action.get_cost(game_state.u_boat)
            summaries.append(f"{action.get_description()} ({cost} AP)")
        return summaries
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.actions) == 0
    
    @property
    def is_committed(self) -> bool:
        """Check if actions have been committed."""
        return self._committed
    
    def __len__(self) -> int:
        """Get number of queued actions."""
        return len(self.actions)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<ActionQueue: {len(self.actions)} actions, {self.max_ap} AP max>"
