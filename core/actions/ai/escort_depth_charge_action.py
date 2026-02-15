"""
EscortDepthChargeAction - Escort drops depth charges on submerged U-boat.

Checks range (same hex), U-boat submerged, rolls damage, checks destruction.
Used when escort is in same hex as submerged U-boat.
"""

from typing import Tuple, Dict, Any, Optional
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult
from core.models import Ship, Depth


class EscortDepthChargeAction(AIAction):
    """Escort drops depth charges on U-boat."""
    
    def __init__(
        self,
        entity_index: int,
        detection_level: int = 0
    ):
        """
        Initialize escort depth charge action.
        
        Args:
            entity_index: Index of escort ship in game_state.ships
            detection_level: Current detection level (0-3)
        """
        super().__init__(entity_index)
        self.detection_level = detection_level
        self.damage_applied: bool = False
        self.uboat_destroyed: bool = False
        self.forced_ascent: bool = False
        self._range: int = 0
    
    @property
    def triggers_animation(self) -> bool:
        """Depth charge could trigger combat animations."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Depth charge is automated."""
        return False
    
    def get_entity(self, game_state: Any) -> Optional[Ship]:
        """Get the escort ship."""
        if 0 <= self.entity_index < len(game_state.ships):
            ship = game_state.ships[self.entity_index]
            if ship.ship_type in ['corvette', 'destroyer']:
                return ship
        return None
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate escort can drop depth charges."""
        escort = self.get_entity(game_state)
        
        if escort is None:
            return False, f"Ship {self.entity_index} is not an escort"
        
        if not hasattr(game_state, 'u_boat'):
            return False, "No U-boat in game"
        
        u_boat = game_state.u_boat
        
        # Check U-boat is submerged
        if u_boat.depth == Depth.SURFACED:
            return False, f"DEPTH CHARGE not possible: U-boat is SURFACED (must be submerged)"
        
        # Check DL requirement
        if self.detection_level < 1 or self.detection_level > 3:
            return False, f"DEPTH CHARGE not possible: DL must be 1-3 (current: {self.detection_level})"
        
        # Check range (must be in same hex)
        if not hasattr(game_state, 'hex_grid'):
            return False, "No hex grid in game"
        
        self._range = game_state.hex_grid.hex_distance(escort.position, u_boat.position)
        
        if self._range > 1:
            return False, f"DEPTH CHARGE not possible: Range {self._range} > 1 (must be in same hex)"
        
        return True, f"Can drop depth charges (Range: {self._range}, Depth: {u_boat.depth.name}, DL: {self.detection_level})"
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute escort depth charge attack.
        
        Returns:
            ActionResult with damage details
        """
        escort = self.get_entity(game_state)
        if escort is None:
            return ActionResult(
                success=False,
                message=f"Cannot drop depth charges from ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )
        
        u_boat = game_state.u_boat
        
        state_changes: Dict[str, Any] = {
            'range': self._range,
            'depth': u_boat.depth.name,
            'detection_level': self.detection_level
        }
        
        # Apply damage
        if hasattr(game_state, 'escort_ai') and hasattr(game_state.escort_ai, 'damage_resolver'):
            damage_result = game_state.escort_ai.damage_resolver.apply_escort_attack_damage(
                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=game_state.ships
            )
            
            self.damage_applied = True
            state_changes['damage_description'] = damage_result.description
            
            # Check destruction
            is_destroyed, _ = game_state.escort_ai.damage_resolver.check_destruction(u_boat)
            if is_destroyed:
                self.uboat_destroyed = True
                state_changes['uboat_destroyed'] = True
                return ActionResult(
                    success=True,
                    message=f"DEPTH CHARGE: Attack on U-boat (Range {self._range}) - U-boat DESTROYED!",
                    ap_spent=0,
                    state_changes=state_changes
                )
            
            # Check forced ascent
            if hasattr(game_state.escort_ai, 'check_forced_ascent'):
                forced, ascent_msg, destroyed_by_ascent = game_state.escort_ai.check_forced_ascent(
                    u_boat, game_state.ships
                )
                if forced:
                    self.forced_ascent = True
                    state_changes['forced_ascent'] = True
                    state_changes['ascent_message'] = ascent_msg
                    if destroyed_by_ascent:
                        self.uboat_destroyed = True
                        u_boat.hull_damage = 4
                        state_changes['uboat_destroyed'] = True
        
        # Build message with damage description
        message = f"DEPTH CHARGE: Attack on U-boat (Range {self._range})"
        if 'damage_description' in state_changes:
            message += f" - {state_changes['damage_description']}"
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=0,
            state_changes=state_changes
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        escort = self.get_entity(game_state)
        
        return {
            'type': 'escort_depth_charge',
            'ship_index': self.entity_index,
            'range': self._range,
            'detection_level': self.detection_level,
            'valid': escort is not None
        }
