"""
Action History - Track executed actions for single-level undo.

This replaces the ActionQueue preview system with immediate execution.
Only the most recent action can be undone.
"""

from typing import Optional, Dict, Any
from copy import deepcopy
from .base_action import Action


class ActionHistory:
    """
    Track executed actions for undo functionality.
    Only stores the most recent action for single-level undo.
    
    The immediate execution system:
    1. Player clicks action button
    2. Action executes immediately
    3. AP deducted immediately
    4. State snapshot saved for undo
    5. Only most recent action can be undone
    """
    
    def __init__(self):
        """Initialize empty action history."""
        self.last_action: Optional[Action] = None
        self.last_action_cost: int = 0
        self.last_state_snapshot: Optional[Dict[str, Any]] = None
    
    def record_action(self, action: Action, ap_cost: int, state_snapshot: Dict[str, Any]) -> None:
        """
        Record an executed action with its state snapshot.
        
        Args:
            action: The action that was executed
            ap_cost: AP cost of the action (for refund on undo)
            state_snapshot: State data to restore on undo
                Expected keys:
                - 'u_boat_state': Relevant U-boat state (torpedoes, damage, etc.)
                - 'remaining_ap': AP before action
                - Any action-specific state needed for undo
        """
        self.last_action = action
        self.last_action_cost = ap_cost
        self.last_state_snapshot = deepcopy(state_snapshot)
    
    def can_undo(self) -> bool:
        """
        Check if there's an action available to undo.
        
        Returns:
            True if last_action exists, False otherwise
        """
        return self.last_action is not None
    
    def get_undo_action_name(self) -> str:
        """
        Get the name of the action that can be undone.
        
        Returns:
            Action type name or empty string if no undo available
        """
        if self.last_action is None:
            return ""
        return self.last_action.action_type
    
    def undo_last_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the state snapshot for undoing the last action.
        
        Returns:
            State snapshot dict to restore, or None if no undo available
            Caller is responsible for applying the state restoration
        """
        if not self.can_undo():
            return None
        
        snapshot = self.last_state_snapshot
        ap_refund = self.last_action_cost
        
        # Clear history after undo (can't undo twice)
        self.clear()
        
        # Return snapshot with AP refund info
        if snapshot is not None:
            snapshot['ap_refund'] = ap_refund
        
        return snapshot
    
    def clear(self) -> None:
        """
        Clear action history.
        Called when:
        - Phase advances (can't undo across phases)
        - After undo (can't undo twice)
        - New turn starts
        """
        self.last_action = None
        self.last_action_cost = 0
        self.last_state_snapshot = None
    
    def get_last_action_cost(self) -> int:
        """
        Get the AP cost of the last action.
        
        Returns:
            AP cost, or 0 if no action recorded
        """
        return self.last_action_cost if self.last_action is not None else 0


def create_u_boat_snapshot(u_boat) -> Dict[str, Any]:
    """
    Helper function to create a snapshot of U-boat state.
    
    Args:
        u_boat: UBoat instance to snapshot
        
    Returns:
        Dict with deep copies of mutable state
    """
    from ..models import TubeState
    
    return {
        'position': (u_boat.position.q, u_boat.position.r),
        'facing': u_boat.facing.value,
        'depth': u_boat.depth.value,
        'torpedo_tubes': [tube.value for tube in u_boat.torpedo_tubes],
        'engine_damaged': u_boat.engine_damaged,
        'deck_gun_damaged': u_boat.deck_gun_damaged,
        'flak_gun_damaged': u_boat.flak_gun_damaged,
        'hull_damage': u_boat.hull_damage,
    }


def restore_u_boat_snapshot(u_boat, snapshot: Dict[str, Any]) -> None:
    """
    Helper function to restore U-boat state from snapshot.
    
    Args:
        u_boat: UBoat instance to restore
        snapshot: State snapshot from create_u_boat_snapshot()
    """
    from ..models import HexCoord, Facing, Depth, TubeState
    
    u_boat.position = HexCoord(snapshot['position'][0], snapshot['position'][1])
    u_boat.facing = Facing(snapshot['facing'])
    u_boat.depth = Depth(snapshot['depth'])
    u_boat.torpedo_tubes = [TubeState(tube) for tube in snapshot['torpedo_tubes']]
    u_boat.engine_damaged = snapshot['engine_damaged']
    u_boat.deck_gun_damaged = snapshot['deck_gun_damaged']
    u_boat.flak_gun_damaged = snapshot['flak_gun_damaged']
    u_boat.hull_damage = snapshot['hull_damage']
