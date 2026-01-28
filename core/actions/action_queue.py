"""
Action queue system for planning and executing player actions.

Allows players to plan multiple actions before committing the turn.
"""

from typing import List, Tuple, Optional, Any, Dict
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
        self.original_depth = None  # Track depth at start of turn for accurate cost calculation
    
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
        
        # Create preview state that simulates effects of queued actions
        from .depth_change_action import DepthChangeAction
        from .fire_torpedo_action import FireTorpedoAction
        from .load_torpedo_action import LoadTorpedoAction
        from copy import copy, deepcopy
        from ..models import TubeState
        
        # Create a preview u_boat that simulates queued action effects
        preview_uboat = deepcopy(game_state.u_boat)
        
        # Track if depth has been changed in queued actions
        depth_changed_in_queue = False
        
        # Simulate depth changes
        simulated_depth = self.original_depth if self.original_depth is not None else game_state.u_boat.depth
        for queued_action in self.actions:
            if isinstance(queued_action, DepthChangeAction):
                simulated_depth = queued_action.new_depth
                depth_changed_in_queue = True  # Mark that depth was changed in queue
            elif isinstance(queued_action, FireTorpedoAction):
                # Simulate firing torpedoes (empty those tubes)
                for tube_idx in queued_action.tube_indices:
                    preview_uboat.torpedo_tubes[tube_idx - 1] = TubeState.EMPTY
            elif isinstance(queued_action, LoadTorpedoAction):
                # Simulate loading torpedoes (load those tubes)
                for tube_idx in queued_action.tube_indices:
                    preview_uboat.torpedo_tubes[tube_idx - 1] = TubeState.LOADED
        
        preview_uboat.depth = simulated_depth
        
        # Create preview turn_manager with updated depth_changed flag
        preview_turn_manager = copy(game_state.turn_manager) if hasattr(game_state, 'turn_manager') and game_state.turn_manager else None
        if preview_turn_manager:
            # If depth was changed in queue OR already changed this turn, mark it
            original_depth_changed = getattr(game_state.turn_manager, 'depth_changed_this_turn', False)
            preview_turn_manager.depth_changed_this_turn = original_depth_changed or depth_changed_in_queue
        
        # Create preview game state with all necessary attributes
        from types import SimpleNamespace
        preview_game_state = SimpleNamespace(
            u_boat=preview_uboat,
            ships=getattr(game_state, 'ships', []),
            hex_grid=getattr(game_state, 'hex_grid', None),
            board_layout=getattr(game_state, 'board_layout', None),
            turn_manager=preview_turn_manager
        )
        
        # Validate action using preview state
        can_perform, reason = action.validate(preview_game_state)
        if not can_perform:
            return False, f"Invalid action: {reason}"
        
        # Calculate action cost using simulated depth (after queued depth changes)
        from copy import copy
        
        # Use temporary u_boat copy for cost calculation (don't modify game state)
        temp_uboat = copy(game_state.u_boat)
        temp_uboat.depth = simulated_depth
        
        # Get cost based on simulated depth
        action_cost = action.get_cost(temp_uboat)
        
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
        from copy import copy
        
        total_cost = 0
        # Use saved original depth, fallback to current if not set
        simulated_depth = self.original_depth if self.original_depth is not None else game_state.u_boat.depth
        
        # Create temporary u_boat for cost calculations
        temp_uboat = copy(game_state.u_boat)
        
        for action in self.actions:
            # Set simulated depth
            temp_uboat.depth = simulated_depth
            
            # Get cost based on simulated depth
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
    
    def clear(self, game_state: Any = None):
        """Clear all queued actions without marking as committed."""
        self.actions.clear()
        # Save original depth at start of turn if provided
        if game_state and hasattr(game_state, 'u_boat'):
            self.original_depth = game_state.u_boat.depth
    
    def reset_for_new_turn(self, new_max_ap: int, game_state: Any = None):
        """Reset queue for a new turn with new AP allocation.
        
        Args:
            new_max_ap: Action points for the new turn
            game_state: Game state to capture original depth
        """
        self.actions.clear()
        self.action_history.clear()  # Clear history for new turn
        self.max_ap = new_max_ap
        self.spent_ap = 0
        self._committed = False
        # Save original depth at start of turn
        if game_state and hasattr(game_state, 'u_boat'):
            self.original_depth = game_state.u_boat.depth
    
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
    
    def get_preview_torpedo_tubes(self, u_boat: Any) -> List[Any]:
        """
        Get preview of torpedo tube states after all queued actions execute.
        
        Simulates fire/load/repair actions to show what tubes will look like after commit.
        
        Args:
            u_boat: Current u-boat state
            
        Returns:
            List of TubeState values representing simulated tube states
        """
        from .fire_torpedo_action import FireTorpedoAction
        from .load_torpedo_action import LoadTorpedoAction
        from .repair_action import RepairAction
        from ..models import TubeState
        from copy import deepcopy
        
        # Start with current tube states
        preview_tubes = deepcopy(u_boat.torpedo_tubes)
        
        # Simulate all queued fire/load/repair actions
        for action in self.actions:
            if isinstance(action, FireTorpedoAction):
                # Firing empties tubes
                for tube_idx in action.tube_indices:
                    preview_tubes[tube_idx - 1] = TubeState.EMPTY
            elif isinstance(action, LoadTorpedoAction):
                # Loading fills tubes
                for tube_idx in action.tube_indices:
                    preview_tubes[tube_idx - 1] = TubeState.LOADED
            elif isinstance(action, RepairAction):
                # Repairing damaged tubes makes them empty
                if action.repair_target == "Torpedo Tubes" and action.tube_number is not None:
                    tube_idx = action.tube_number - 1
                    if preview_tubes[tube_idx] == TubeState.DAMAGED:
                        preview_tubes[tube_idx] = TubeState.EMPTY
        
        return preview_tubes
    
    def get_preview_damage_state(self, u_boat: Any) -> Dict[str, bool]:
        """
        Get preview of damage states after all queued repair actions.
        
        Simulates repair actions to show what will be fixed after commit.
        
        Args:
            u_boat: Current u-boat state
            
        Returns:
            Dict with keys: 'engine_damaged', 'deck_gun_damaged', 'flak_gun_damaged'
        """
        from .repair_action import RepairAction
        
        # Start with current damage states
        preview_damage = {
            'engine_damaged': u_boat.engine_damaged,
            'deck_gun_damaged': u_boat.deck_gun_damaged,
            'flak_gun_damaged': u_boat.flak_gun_damaged
        }
        
        # Simulate all queued repair actions
        for action in self.actions:
            if isinstance(action, RepairAction):
                if action.repair_target == "Engine":
                    preview_damage['engine_damaged'] = False
                elif action.repair_target == "Deck Gun":
                    preview_damage['deck_gun_damaged'] = False
                elif action.repair_target == "Flak Gun":
                    preview_damage['flak_gun_damaged'] = False
        
        return preview_damage
    
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
