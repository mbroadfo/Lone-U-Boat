"""
EscortActivationAction - Rolls dice for escort activation.

This action handles rolling the dice pool for an escort ship during
its activation. The number of dice is calculated based on ship type,
damage status, and detection level.
"""

from typing import List, Tuple, Dict, Any, Optional
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult
from core.models import Ship


class EscortActivationAction(AIAction):
    """Roll dice to activate an escort ship."""
    
    def __init__(
        self,
        entity_index: int,
        detection_level: int = 0
    ):
        """
        Initialize escort activation action.
        
        Args:
            entity_index: Index of escort ship in game_state.ships
            detection_level: Current detection level (0-3)
        """
        super().__init__(entity_index)
        self.detection_level = detection_level
        self.dice_count: int = 0
        self.rolls: List[int] = []
        self._requires_player_input = True  # Player rolls dice
    
    @property
    def triggers_animation(self) -> bool:
        """Activation doesn't trigger animations."""
        return False
    
    @property
    def requires_player_input(self) -> bool:
        """Requires player to roll dice."""
        return self._requires_player_input
    
    def get_entity(self, game_state: Any) -> Optional[Ship]:
        """Get the escort ship being activated."""
        if 0 <= self.entity_index < len(game_state.ships):
            ship = game_state.ships[self.entity_index]
            if ship.ship_type in ['corvette', 'destroyer']:
                return ship
        return None
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate escort can be activated."""
        escort = self.get_entity(game_state)
        
        if escort is None:
            return False, f"Ship {self.entity_index} is not an escort"
        
        if escort.ship_type not in ['corvette', 'destroyer']:
            return False, f"Ship {self.entity_index} is not an escort (type: {escort.ship_type})"
        
        # Calculate dice count
        self.dice_count = self._calculate_dice_count(escort, game_state)
        
        if self.dice_count == 0:
            return False, f"{escort.ship_type.capitalize()} has 0 dice (damaged at DL 0)"
        
        return True, f"{escort.ship_type.capitalize()} can activate with {self.dice_count} dice"
    
    def _calculate_dice_count(self, escort: Ship, game_state: Any) -> int:
        """
        Calculate number of dice for this escort.
        
        Corvettes: 2 base dice
        Destroyers: 3 base dice
        +DL bonus if undamaged
        """
        # Get base dice from escort AI
        if hasattr(game_state, 'escort_ai'):
            if escort.ship_type == 'corvette':
                base_dice = game_state.escort_ai.corvette_base_dice
            else:
                base_dice = game_state.escort_ai.destroyer_base_dice
        else:
            # Fallback defaults
            base_dice = 2 if escort.ship_type == 'corvette' else 3
        
        # Add DL bonus if undamaged
        if not escort.damaged and self.detection_level >= 1:
            return base_dice + self.detection_level
        else:
            return base_dice
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Roll dice for escort activation.
        
        Returns:
            ActionResult with dice rolls in state_changes
        """
        escort = self.get_entity(game_state)
        if escort is None:
            return ActionResult(
                success=False,
                message=f"Cannot activate ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )
        
        # Roll dice using escort AI's dice roller
        if hasattr(game_state, 'escort_ai') and hasattr(game_state.escort_ai, 'dice'):
            dice_roller = game_state.escort_ai.dice
            self.rolls = sorted([dice_roller.roll_1d6() for _ in range(self.dice_count)])
        else:
            # Fallback - shouldn't happen in real game
            self.rolls = [3] * self.dice_count
        
        rolls_str = ", ".join(str(r) for r in self.rolls)
        
        return ActionResult(
            success=True,
            message=f"{escort.ship_type.capitalize()} activated: rolled {rolls_str}",
            ap_spent=0,
            state_changes={
                'escort_index': self.entity_index,
                'dice_count': self.dice_count,
                'rolls': self.rolls,
                'detection_level': self.detection_level
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        escort = self.get_entity(game_state)
        
        return {
            'type': 'escort_activation',
            'ship_index': self.entity_index,
            'ship_type': escort.ship_type if escort else 'unknown',
            'detection_level': self.detection_level,
            'dice_count': self.dice_count,
            'damaged': escort.damaged if escort else False,
            'valid': escort is not None
        }
