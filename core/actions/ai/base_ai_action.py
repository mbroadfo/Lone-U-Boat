"""
Base class for Interactive AI Actions.

AI actions inherit from the standard Action class but add special handling
for animations and AI-specific state management.
"""

from abc import abstractmethod
from typing import Any
from ..base_action import Action, ActionResult


class AIAction(Action):
    """
    Base class for all Interactive AI actions.
    
    AI actions differ from player actions in that they:
    1. Are generated automatically by AI logic
    2. Trigger animations immediately upon execution
    3. May require player input (e.g., rolling dice for AI)
    4. Represent AI entity behavior (merchants, escorts, B-24s)
    
    Key Concepts:
    - entity_index: Which ship/aircraft this action affects (0-based index in game.ships or game.aircraft)
    - triggers_animation: Whether this action should trigger visual animations
    - requires_player_input: Whether player needs to interact (e.g., roll dice)
    """
    
    def __init__(self, entity_index: int):
        """
        Initialize AI action.
        
        Args:
            entity_index: Index of the entity (ship/aircraft) in game state list
        """
        super().__init__()
        self.entity_index = entity_index
        # Note: triggers_animation and requires_player_input are properties
        # defined by subclasses, not instance attributes
    
    def get_cost(self, u_boat: Any) -> int:
        """
        AI actions don't cost AP (AI doesn't have action points).
        
        Returns:
            0 (AI actions are free)
        """
        return 0
    
    @abstractmethod
    def get_entity(self, game_state: Any) -> Any:
        """
        Get the entity (ship/aircraft) this action affects.
        
        Args:
            game_state: Current game state
            
        Returns:
            The ship or aircraft object
        """
        pass
    
    @abstractmethod
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute the action AND trigger animations.
        
        This is different from standard execute() because it integrates
        with the animation system directly, ensuring smooth visual feedback.
        
        Args:
            game_state: Current game state (will be modified)
            
        Returns:
            ActionResult with success status and details
        """
        pass
    
    def execute(self, game_state: Any) -> ActionResult:
        """
        Standard execute method (delegates to execute_with_animation).
        
        Args:
            game_state: Current game state
            
        Returns:
            ActionResult from execute_with_animation
        """
        return self.execute_with_animation(game_state)
    
    def get_entity_description(self, game_state: Any) -> str:
        """
        Get human-readable description of the entity.
        
        Args:
            game_state: Current game state
            
        Returns:
            Description like "Merchant at [3,4]" or "Destroyer #1"
        """
        entity = self.get_entity(game_state)
        if hasattr(entity, 'ship_type'):
            return f"{entity.ship_type.title()} at [{entity.position.q},{entity.position.r}]"
        elif hasattr(entity, 'aircraft_type'):
            return f"{entity.aircraft_type.upper()} at [{entity.position.q},{entity.position.r}]"
        else:
            return f"Entity #{self.entity_index}"
