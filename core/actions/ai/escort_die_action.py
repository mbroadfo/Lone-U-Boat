"""
EscortDieAction - Executes one die result from escort activation.

Maps die value to available actions based on unified escort action table.
"""

from typing import List, Tuple, Dict, Any, Optional
from enum import Enum
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult
from core.models import Ship


class EscortActionType(Enum):
    """Actions an escort can take."""
    MOVE = "move"
    TURN = "turn"
    FIRE = "fire"
    DEPTH_CHARGE = "depth_charge"


class EscortDieAction(AIAction):
    """Execute actions for one die roll result."""
    
    def __init__(
        self,
        entity_index: int,
        die_value: int,
        detection_level: int = 0
    ):
        """
        Initialize escort die action.
        
        Args:
            entity_index: Index of escort ship in game_state.ships
            die_value: Die roll result (1-6)
            detection_level: Current detection level (0-3)
        """
        super().__init__(entity_index)
        self.die_value = die_value
        self.detection_level = detection_level
        self.actions_granted: List[EscortActionType] = []
    
    @property
    def triggers_animation(self) -> bool:
        """Die action itself doesn't trigger animations."""
        return False
    
    @property
    def requires_player_input(self) -> bool:
        """Die action is automated."""
        return False
    
    def get_entity(self, game_state: Any) -> Optional[Ship]:
        """Get the escort ship."""
        if 0 <= self.entity_index < len(game_state.ships):
            ship = game_state.ships[self.entity_index]
            if ship.ship_type in ['corvette', 'destroyer']:
                return ship
        return None
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate die action can be executed."""
        escort = self.get_entity(game_state)
        
        if escort is None:
            return False, f"Ship {self.entity_index} is not an escort"
        
        if not 1 <= self.die_value <= 6:
            return False, f"Invalid die value: {self.die_value}"
        
        # Map die value to actions
        self.actions_granted = self._map_die_to_actions()
        
        return True, f"Die {self.die_value}: {', '.join(a.value.upper() for a in self.actions_granted)}"
    
    def _map_die_to_actions(self) -> List[EscortActionType]:
        """
        Map die result to available actions.
        
        Unified action table (same for corvettes and destroyers):
        1: FIRE (if surfaced) or DEPTH_CHARGE (if submerged)
        2: MOVE -> (if blocked) TURN -> (if DL 1-3) DEPTH_CHARGE
        3: MOVE
        4: MOVE -> TURN
        5: TURN
        6: MOVE -> TURN
        """
        if self.die_value == 1:
            # Combat action - will choose FIRE or DEPTH_CHARGE based on U-boat state
            return [EscortActionType.FIRE, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 2:
            return [EscortActionType.MOVE, EscortActionType.TURN, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 3:
            return [EscortActionType.MOVE]
        elif self.die_value == 4 or self.die_value == 6:
            return [EscortActionType.MOVE, EscortActionType.TURN]
        elif self.die_value == 5:
            return [EscortActionType.TURN]
        else:
            return []
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Determine actions for this die roll.
        
        Returns:
            ActionResult with granted actions
        """
        escort = self.get_entity(game_state)
        if escort is None:
            return ActionResult(
                success=False,
                message=f"Cannot execute die action for ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )
        
        actions_str = ", ".join(a.value.upper() for a in self.actions_granted)
        
        return ActionResult(
            success=True,
            message=f"Die {self.die_value}: grants {actions_str}",
            ap_spent=0,
            state_changes={
                'escort_index': self.entity_index,
                'die_value': self.die_value,
                'actions_granted': [a.value for a in self.actions_granted],
                'detection_level': self.detection_level
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        escort = self.get_entity(game_state)
        
        return {
            'type': 'escort_die_action',
            'ship_index': self.entity_index,
            'die_value': self.die_value,
            'actions_granted': [a.value for a in self.actions_granted],
            'valid': escort is not None
        }
