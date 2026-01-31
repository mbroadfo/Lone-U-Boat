"""
Action History - Track executed actions for multi-level undo.

This replaces the ActionQueue preview system with immediate execution.
All actions in the current turn can be undone until a dice roll is committed.
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from copy import deepcopy
from .base_action import Action

if TYPE_CHECKING:
    from ..models import UBoat



class ActionHistory:
    """
    Track executed actions for undo functionality.
    Stores all actions in the current turn for multi-level undo.
    
    The immediate execution system:
    1. Player clicks action button
    2. Action executes immediately
    3. AP deducted immediately
    4. State snapshot saved for undo
    5. Can undo back to start of turn (until dice are rolled)
    """
    
    def __init__(self):
        """Initialize empty action history."""
        self.actions: List[Action] = []
        self.action_costs: List[int] = []
        self.state_snapshots: List[Dict[str, Any]] = []
    
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
        self.actions.append(action)
        self.action_costs.append(ap_cost)
        self.state_snapshots.append(deepcopy(state_snapshot))
    
    def can_undo(self) -> bool:
        """
        Check if there's an action available to undo.
        
        Returns:
            True if actions list is not empty, False otherwise
        """
        return len(self.actions) > 0
    
    def get_undo_action_name(self) -> str:
        """
        Get the name of the action that can be undone.
        
        Returns:
            Action type name or empty string if no undo available
        """
        if len(self.actions) == 0:
            return ""
        return self.actions[-1].action_type
    
    def undo_last_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the state snapshot for undoing the last action.
        
        Returns:
            State snapshot dict to restore, or None if no undo available
            Caller is responsible for applying the state restoration
        """
        if not self.can_undo():
            return None
        
        # Pop the last action from history
        action = self.actions.pop()
        ap_refund = self.action_costs.pop()
        snapshot = self.state_snapshots.pop()
        action_name = action.get_description() if action else "Action"
        
        # Return snapshot with AP refund info and action name
        return {
            'snapshot': snapshot,
            'ap_refund': ap_refund,
            'action_name': action_name
        }
    
    def clear(self) -> None:
        """
        Clear action history.
        Called when:
        - Phase advances (can't undo across phases)
        - Dice are rolled (can't undo after dice roll)
        - New turn starts
        """
        self.actions.clear()
        self.action_costs.clear()
        self.state_snapshots.clear()
    
    def get_last_action_cost(self) -> int:
        """
        Get the AP cost of the last action.
        
        Returns:
            AP cost, or 0 if no action recorded
        """
        return self.action_costs[-1] if len(self.action_costs) > 0 else 0
    
    def get_action_count(self) -> int:
        """
        Get the number of actions in history.
        
        Returns:
            Number of actions that can be undone
        """
        return len(self.actions)


def create_u_boat_snapshot(u_boat: 'UBoat') -> Dict[str, Any]:
    """
    Helper function to create a snapshot of U-boat state.
    
    Args:
        u_boat: UBoat instance to snapshot
        
    Returns:
        Dict with deep copies of mutable state
    """
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


def restore_u_boat_snapshot(u_boat: 'UBoat', snapshot: Dict[str, Any]) -> None:
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
