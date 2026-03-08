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
        3: MOVE -> (if DL 1-3) DEPTH_CHARGE
        4: MOVE -> (if blocked) TURN -> (if DL 1-3) DEPTH_CHARGE
        5: MOVE -> (if DL 1-3) DEPTH_CHARGE
        6: MOVE -> TURN -> (if DL 1-3) DEPTH_CHARGE
        """
        if self.die_value == 1:
            # Combat action - will choose FIRE or DEPTH_CHARGE based on U-boat state
            return [EscortActionType.FIRE, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 2:
            return [EscortActionType.MOVE, EscortActionType.TURN, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 3:
            return [EscortActionType.MOVE, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 4:
            return [EscortActionType.MOVE, EscortActionType.TURN, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 5:
            return [EscortActionType.MOVE, EscortActionType.DEPTH_CHARGE]
        elif self.die_value == 6:
            return [EscortActionType.MOVE, EscortActionType.TURN, EscortActionType.DEPTH_CHARGE]
        else:
            return []
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute all actions granted by this die value.

        Sub-actions are resolved inline (validate → execute); results are
        combined into a single result message returned to the UI.

        Die table (same for all escort types):
          1  → Fire (surfaced) OR Depth Charge (submerged) — whichever is valid
          2  → Move; if blocked → Turn; also Depth Charge (DL ≥ 1)
          3  → Move; also Depth Charge (DL ≥ 1)
          4  → Move; if blocked → Turn; also Depth Charge (DL ≥ 1)
          5  → Move; also Depth Charge (DL ≥ 1)
          6  → Move; then Turn; also Depth Charge (DL ≥ 1)
        """
        # Local imports avoid circular dependencies
        from core.actions.ai.escort_move_action import EscortMoveAction
        from core.actions.ai.escort_turn_action import EscortTurnAction
        from core.actions.ai.escort_fire_action import EscortFireAction
        from core.actions.ai.escort_depth_charge_action import EscortDepthChargeAction

        escort = self.get_entity(game_state)
        if escort is None:
            return ActionResult(
                success=False,
                message=f"Cannot execute die {self.die_value} for ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )

        # Use the latest detection_level from game_state if available
        detection_level = getattr(game_state, 'detection_level', self.detection_level)
        idx = self.entity_index
        result_parts: List[str] = []

        def try_action(action: Any) -> Optional[str]:
            """Validate then execute action; return result message or None if invalid."""
            is_valid, _reason = action.validate(game_state)
            if not is_valid:
                return None
            res = action.execute_with_animation(game_state)
            return res.message if res.success else None

        if self.die_value == 1:
            # Combat: try gunfire first, then depth charge
            fire_msg = try_action(EscortFireAction(idx, detection_level))
            if fire_msg:
                result_parts.append(fire_msg)
            else:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)
                else:
                    result_parts.append("No valid combat target")

        elif self.die_value == 2:
            # Move; if blocked turn; also depth charge if DL ≥ 1
            move_msg = try_action(EscortMoveAction(idx))
            if move_msg:
                result_parts.append(move_msg)
            else:
                turn_msg = try_action(EscortTurnAction(idx, detection_level=detection_level))
                if turn_msg:
                    result_parts.append(turn_msg)
                else:
                    result_parts.append("MOVE: blocked, no turn needed")
            if detection_level >= 1:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)

        elif self.die_value == 3:
            move_msg = try_action(EscortMoveAction(idx))
            result_parts.append(move_msg if move_msg else "MOVE: blocked")
            if detection_level >= 1:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)

        elif self.die_value == 4:
            # Move; if blocked, turn; also depth charge if DL >= 1
            move_msg = try_action(EscortMoveAction(idx))
            if move_msg:
                result_parts.append(move_msg)
            else:
                turn_msg = try_action(EscortTurnAction(idx, detection_level=detection_level))
                if turn_msg:
                    result_parts.append(turn_msg)
                else:
                    result_parts.append("MOVE: blocked, no turn needed")
            if detection_level >= 1:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)

        elif self.die_value == 5:
            move_msg = try_action(EscortMoveAction(idx))
            result_parts.append(move_msg if move_msg else "MOVE: blocked")
            if detection_level >= 1:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)

        elif self.die_value == 6:
            move_msg = try_action(EscortMoveAction(idx))
            result_parts.append(move_msg if move_msg else "MOVE: blocked")
            turn_msg = try_action(EscortTurnAction(idx, detection_level=detection_level))
            if turn_msg:
                result_parts.append(turn_msg)
            if detection_level >= 1:
                dc_msg = try_action(EscortDepthChargeAction(idx, detection_level))
                if dc_msg:
                    result_parts.append(dc_msg)

        q, r = escort.position.q, escort.position.r
        ship_label = f"{escort.ship_type.capitalize()} at [{q},{r}]"
        summary = "; ".join(result_parts) if result_parts else "No actions"
        return ActionResult(
            success=True,
            message=f"{ship_label}: Die {self.die_value} → {summary}",
            ap_spent=0,
            state_changes={
                'escort_index': self.entity_index,
                'die_value': self.die_value,
                'detection_level': detection_level
            }
        )

    def get_description(self) -> str:
        """Return human-readable description for the UI preview."""
        action_map = {
            1: "Fire / Depth Charge",
            2: "Move / Turn + DC (DL≥1)",
            3: "Move + DC (DL≥1)",
            4: "Move / Turn + DC (DL≥1)",
            5: "Move + DC (DL≥1)",
            6: "Move + Turn + DC (DL≥1)",
        }
        return f"Die {self.die_value}: {action_map.get(self.die_value, '?')}"

    def get_entity_description(self, game_state: Any) -> str:
        """Return entity label for the UI preview."""
        escort = self.get_entity(game_state)
        if escort is None:
            return f"Ship {self.entity_index}"
        q, r = escort.position.q, escort.position.r
        return f"{escort.ship_type.capitalize()} at [{q},{r}]"
    
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
