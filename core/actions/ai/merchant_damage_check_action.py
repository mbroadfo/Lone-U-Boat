"""
Merchant Damage Check Action - Roll to see if damaged merchant can move.

In the interactive AI mode, this action represents the player rolling 1d6
for a damaged merchant ship to determine if it can move this turn (4+ succeeds).
"""

from typing import Any, Dict, Tuple
from .base_ai_action import AIAction, ActionResult
from ...models import Ship


class MerchantDamageCheckAction(AIAction):
    """
    Roll 1d6 to determine if a damaged merchant can move.
    
    This action represents the interactive moment where the player
    rolls dice on behalf of the damaged merchant AI. On a roll of
    4+, the merchant will be allowed to move. Otherwise, it stays put.
    
    Attributes:
        entity_index: Index of the merchant ship in game.ships
        required_roll: Minimum roll needed to move (default 4)
    """
    
    def __init__(self, entity_index: int, required_roll: int = 4):
        """
        Initialize damage check action.
        
        Args:
            entity_index: Index of merchant in ships list
            required_roll: Minimum 1d6 roll to allow movement (default 4)
        """
        super().__init__(entity_index)
        self.required_roll = required_roll
        self.requires_player_input = True  # Player rolls the die
        self.triggers_animation = False  # Just a die roll, no movement yet
        self.roll_result = None  # Will be set during execution
        self.can_move = False  # Result of the check
    
    def get_entity(self, game_state: Any) -> Ship:
        """Get the merchant ship this action affects."""
        return game_state.ships[self.entity_index]
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate that this ship is a damaged merchant.
        
        Args:
            game_state: Current game state
            
        Returns:
            (can_perform, reason_if_not)
        """
        if self.entity_index >= len(game_state.ships):
            return False, f"Ship index {self.entity_index} out of range"
        
        ship = game_state.ships[self.entity_index]
        
        if ship.ship_type != 'merchant':
            return False, f"Ship is not a merchant (is {ship.ship_type})"
        
        if not ship.damaged:
            return False, "Ship is not damaged (no damage check needed)"
        
        return True, "Damaged merchant can make damage check"
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute the damage check roll.
        
        Rolls 1d6 using the game's dice roller. On success (4+),
        the merchant will be allowed to attempt movement.
        
        Args:
            game_state: Current game state
            
        Returns:
            ActionResult with roll outcome
        """
        # Get dice roller from merchant AI
        if hasattr(game_state, 'merchant_ai') and hasattr(game_state.merchant_ai, 'dice'):
            dice = game_state.merchant_ai.dice
        else:
            # Fallback to turn_manager dice
            dice = game_state.turn_manager.dice if hasattr(game_state, 'turn_manager') else None
            if dice is None:
                return ActionResult(
                    success=False,
                    message="No dice roller available",
                    ap_spent=0,
                    state_changes={}
                )
        
        # Roll 1d6
        self.roll_result = dice.roll_1d6("Merchant damage check")
        self.can_move = self.roll_result >= self.required_roll
        
        if self.can_move:
            message = f"Merchant (damaged) rolled 1d6 [{self.roll_result}] - CAN move!"
            success = True
        else:
            message = f"Merchant (damaged) rolled 1d6 [{self.roll_result}] - cannot move"
            success = True  # Action succeeded (roll was made), even though merchant can't move
        
        return ActionResult(
            success=success,
            message=message,
            ap_spent=0,
            state_changes={
                'roll_result': self.roll_result,
                'can_move': self.can_move,
                'ship_index': self.entity_index
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """
        Get preview data for UI.
        
        Shows that player needs to roll 1d6 for this merchant.
        """
        ship = self.get_entity(game_state)
        
        return {
            "type": "damage_check",
            "ship_index": self.entity_index,
            "ship_position": ship.position,
            "required_roll": self.required_roll,
            "prompt": f"Roll 1d6 for damaged Merchant at [{ship.position.q},{ship.position.r}] (need {self.required_roll}+)"
        }
    
    def get_description(self) -> str:
        """Get human-readable description."""
        if self.roll_result is not None:
            return f"Merchant damage check: rolled {self.roll_result} ({'PASS' if self.can_move else 'FAIL'})"
        return f"Merchant damage check (need {self.required_roll}+)"
