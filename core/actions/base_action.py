"""
Base action classes for Lone U-Boat gameplay.

All player actions inherit from Action and provide validation, execution, and preview.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from dataclasses import dataclass
from ..models import UBoat


@dataclass
class ActionResult:
    """Result of executing an action."""
    success: bool
    message: str
    ap_spent: int
    state_changes: Dict[str, Any]  # Track what changed for undo
    
    def __str__(self) -> str:
        """String representation for logging."""
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.message} (AP: {self.ap_spent})"


class Action(ABC):
    """
    Abstract base class for all player actions.
    
    Each action must:
    1. Calculate its AP cost
    2. Validate it can be performed
    3. Execute and modify game state
    4. Provide preview data for UI
    """
    
    def __init__(self):
        """Initialize action."""
        self.action_type: str = self.__class__.__name__
    
    @abstractmethod
    def get_cost(self, u_boat: UBoat) -> int:
        """
        Calculate AP cost for this action.
        
        Args:
            u_boat: Current U-boat state (depth affects costs)
            
        Returns:
            Action point cost
        """
        pass
    
    @abstractmethod
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate action can be performed in current game state.
        
        Args:
            game_state: Current game state
            
        Returns:
            (can_perform, reason_if_not)
        """
        pass
    
    @abstractmethod
    def execute(self, game_state: Any) -> ActionResult:
        """
        Execute the action and modify game state.
        
        Args:
            game_state: Current game state (will be modified)
            
        Returns:
            ActionResult with success status and details
        """
        pass
    
    @abstractmethod
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """
        Get data for visual preview before execution.
        
        Examples:
        - Movement: highlighted hexes
        - Combat: targeting lines, range indicators
        - Repair: list of affected systems
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary with preview data for renderer
        """
        pass
    
    def get_description(self) -> str:
        """
        Get human-readable description of action.
        
        Returns:
            Description string for UI display
        """
        return self.action_type
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.action_type}>"
