"""
B-24 Bomb Action - Interactive AI system.

Handles B-24 bombing attack on U-boat with dice-based damage resolution.
"""

from typing import Tuple, Any, Optional, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import Aircraft, UBoat, Depth


class B24BombAction(AIAction):
    """Action for B-24 bombing U-boat."""
    
    def __init__(self, aircraft_index: int):
        """Initialize B-24 bomb action.
        
        Args:
            aircraft_index: Index of aircraft in game_state.aircraft
        """
        super().__init__(entity_index=aircraft_index)
        self._aircraft_index = aircraft_index
        self._attack_roll: Optional[int] = None
        self._damage_applied = False
        self._attack_succeeded = False
    
    @property
    def triggers_animation(self) -> bool:
        """Bombing triggers animation."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Bombing requires dice roll."""
        return True
    
    def get_entity(self, game_state: Any) -> Optional[Aircraft]:
        """Get the B-24 aircraft."""
        if hasattr(game_state, 'aircraft') and 0 <= self._aircraft_index < len(game_state.aircraft):
            return game_state.aircraft[self._aircraft_index]
        return None
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        aircraft = self.get_entity(game_state)
        u_boat = getattr(game_state, 'u_boat', None)
        hex_grid = getattr(game_state, 'hex_grid', None)
        distance = hex_grid.hex_distance(aircraft.position, u_boat.position) if (aircraft and u_boat and hex_grid) else None
        return {
            'type': 'b24_bomb',
            'aircraft_index': self._aircraft_index,
            'aircraft_position': aircraft.position if aircraft else None,
            'target_position': u_boat.position if u_boat else None,
            'range': distance,
            'attack_roll': self._attack_roll,
            'damage_applied': self._damage_applied
        }
    
    @property
    def aircraft_index(self) -> int:
        """Get the aircraft index."""
        return self._aircraft_index
    
    @property
    def attack_roll(self) -> Optional[int]:
        """The 1d6 attack roll result."""
        return self._attack_roll
    
    @property
    def damage_applied(self) -> bool:
        """Whether damage was applied to U-boat."""
        return self._damage_applied
    
    @property
    def attack_succeeded(self) -> bool:
        """Whether attack dealt any damage."""
        return self._attack_succeeded
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate that B-24 can attack.
        
        Requirements:
        - Aircraft exists
        - U-boat exists
        - Range 0-1
        - U-boat at Surfaced or Periscope depth
        
        Args:
            game_state: Current game state
        
        Returns:
            Tuple of (can_attack, reason)
        """
        # Check aircraft exists
        if not hasattr(game_state, 'aircraft'):
            return (False, "No aircraft list in game state")
        
        if self._aircraft_index >= len(game_state.aircraft):
            return (False, f"Aircraft index {self._aircraft_index} out of range")
        
        aircraft = game_state.aircraft[self._aircraft_index]
        
        # Check U-boat exists
        if not hasattr(game_state, 'u_boat'):
            return (False, "No U-boat in game state")
        
        u_boat: UBoat = game_state.u_boat
        
        # Check hex grid
        if not hasattr(game_state, 'hex_grid'):
            return (False, "No hex grid in game state")
        
        hex_grid = game_state.hex_grid
        
        # Check range (0-1)
        distance = hex_grid.hex_distance(aircraft.position, u_boat.position)
        if distance > 1:
            return (False, f"Range {distance} > 1, cannot attack")
        
        # Check U-boat depth
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return (False, f"U-boat at {u_boat.depth.name}, must be SURFACED or PERISCOPE")
        
        return (True, f"B-24 can bomb U-boat at range {distance}")
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute B-24 bombing attack.
        
        Damage table (1d6):
        - 1: Critical Hit (roll 2d6 on U-Boat Critical Hit sub-table)
        - 2-3: General Damage (roll 1d6 on U-Boat General Damage sub-table)
        - 4-6: Miss (no damage)
        
        Args:
            game_state: Current game state (modified in place)
        
        Returns:
            ActionResult with attack details
        """
        # Validate aircraft still exists (may have been removed by earlier action)
        if self._aircraft_index >= len(game_state.aircraft):
            return ActionResult(
                success=True,
                message="B-24 bomb skipped — aircraft no longer exists",
                ap_spent=0,
                state_changes={}
            )
        
        aircraft: Aircraft = game_state.aircraft[self._aircraft_index]
        u_boat: UBoat = game_state.u_boat
        hex_grid = game_state.hex_grid
        dice = getattr(game_state, 'dice_roller', None)
        
        distance = hex_grid.hex_distance(aircraft.position, u_boat.position)
        
        # Roll for attack
        if dice:
            self._attack_roll = dice.roll_1d6()
        else:
            self._attack_roll = 4  # Default to miss if no dice
        
        # Check if U-boat has damage resolver
        if not hasattr(game_state, 'damage_resolver'):
            return ActionResult(
                success=False,
                message="No damage resolver available",
                ap_spent=0,
                state_changes={}
            )
        
        damage_resolver = game_state.damage_resolver
        
        if self._attack_roll == 1:
            # Critical Hit
            self._damage_applied = True
            self._attack_succeeded = True
            damage_result = damage_resolver.apply_critical_damage(u_boat)
            
            if damage_result.is_destroyed:
                return ActionResult(
                    success=True,
                    message=f"B-24 CRITICAL HIT at range {distance}! {damage_result.description} U-BOAT DESTROYED!",
                    ap_spent=0,
                    state_changes={}
                )
            else:
                return ActionResult(
                    success=True,
                    message=f"B-24 CRITICAL HIT at range {distance}! {damage_result.description}",
                    ap_spent=0,
                    state_changes={}
                )
        
        # Type guard for attack_roll
        if self._attack_roll is None:
            return ActionResult(
                success=False,
                message="Attack roll not performed",
                ap_spent=0,
                state_changes={}
            )
        
        if self._attack_roll <= 3:
            # General Damage
            self._damage_applied = True
            self._attack_succeeded = True
            damage_result = damage_resolver.apply_general_damage(u_boat)
            
            if damage_result.is_destroyed:
                return ActionResult(
                    success=True,
                    message=f"B-24 general damage at range {distance}! {damage_result.description} U-BOAT DESTROYED!",
                    ap_spent=0,
                    state_changes={}
                )
            else:
                return ActionResult(
                    success=True,
                    message=f"B-24 general damage at range {distance}! {damage_result.description}",
                    ap_spent=0,
                    state_changes={}
                )
        
        else:
            # Miss
            self._damage_applied = False
            self._attack_succeeded = False
            return ActionResult(
                success=True,
                message=f"B-24 attack at range {distance} missed (rolled {self._attack_roll})",
                ap_spent=0,
                state_changes={}
            )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute with animation trigger.
        
        Future enhancement: Add bombing animation
        
        Args:
            game_state: Current game state
        
        Returns:
            ActionResult from execute()
        """
        return self.execute(game_state)
