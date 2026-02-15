"""
Flak Defense Action - Interactive AI system.

Handles U-boat flak gun defense against B-24 attack.
"""

from typing import Tuple, Any, Optional, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import Aircraft, UBoat, Depth


class FlakDefenseAction(AIAction):
    """Action for U-boat flak gun defending against B-24."""
    
    def __init__(self, aircraft_index: int):
        """Initialize flak defense action.
        
        Args:
            aircraft_index: Index of attacking aircraft in game_state.aircraft
        """
        super().__init__(entity_index=aircraft_index)
        self._aircraft_index = aircraft_index
        self._flak_roll: Optional[int] = None
        self._threshold: Optional[int] = None
        self._b24_destroyed = False
        self._outcome: Optional[str] = None  # 'shot_down', 'scared_off', or None
    
    @property
    def triggers_animation(self) -> bool:
        """Flak defense triggers animation."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Flak requires dice roll."""
        return True
    
    def get_entity(self, game_state: Any) -> Optional[Aircraft]:
        """Get the B-24 aircraft being targeted."""
        if hasattr(game_state, 'aircraft') and 0 <= self._aircraft_index < len(game_state.aircraft):
            return game_state.aircraft[self._aircraft_index]
        return None
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        aircraft = self.get_entity(game_state)
        u_boat = getattr(game_state, 'u_boat', None)
        return {
            'type': 'flak_defense',
            'aircraft_index': self._aircraft_index,
            'aircraft_position': aircraft.position if aircraft else None,
            'uboat_position': u_boat.position if u_boat else None,
            'flak_roll': self._flak_roll,
            'threshold': self._threshold,
            'b24_destroyed': self._b24_destroyed,
            'outcome': self._outcome
        }
    
    @property
    def aircraft_index(self) -> int:
        """Get the aircraft index."""
        return self._aircraft_index
    
    @property
    def flak_roll(self) -> Optional[int]:
        """The 2d6 flak roll result."""
        return self._flak_roll
    
    @property
    def threshold(self) -> Optional[int]:
        """The threshold needed to hit (7 or 8)."""
        return self._threshold
    
    @property
    def b24_destroyed(self) -> bool:
        """Whether B-24 was destroyed/scared off."""
        return self._b24_destroyed
    
    @property
    def outcome(self) -> Optional[str]:
        """Outcome: 'shot_down', 'scared_off', or None."""
        return self._outcome
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate that U-boat can use flak gun.
        
        Requirements:
        - U-boat at Surfaced depth
        - Flak gun not damaged
        - Aircraft exists
        
        Args:
            game_state: Current game state
        
        Returns:
            Tuple of (can_fire_flak, reason)
        """
        # Check U-boat exists
        if not hasattr(game_state, 'u_boat'):
            return (False, "No U-boat in game state")
        
        u_boat: UBoat = game_state.u_boat
        
        # Check depth
        if u_boat.depth != Depth.SURFACED:
            return (False, f"U-boat not surfaced (depth={u_boat.depth.name})")
        
        # Check flak gun
        if u_boat.flak_gun_damaged:
            return (False, "Flak gun damaged")
        
        # Check aircraft exists
        if not hasattr(game_state, 'aircraft'):
            return (False, "No aircraft list in game state")
        
        if self._aircraft_index >= len(game_state.aircraft):
            return (False, f"Aircraft index {self._aircraft_index} out of range")
        
        return (True, "U-boat can fire flak gun")
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute flak gun defense.
        
        Roll 2d6:
        - 7+ (with lookout): Hit B-24
        - 8+ (without lookout): Hit B-24
        - Below threshold: Miss
        
        If hit, roll 1d6:
        - 1-3: Shot down
        - 4-6: Scared off
        
        Args:
            game_state: Current game state (modified in place)
        
        Returns:
            ActionResult with flak defense details
        """
        # Validate aircraft still exists (may have been removed by earlier action)
        if self._aircraft_index >= len(game_state.aircraft):
            return ActionResult(
                success=False,
                message=f"Aircraft no longer exists (removed earlier)",
                ap_spent=0,
                state_changes={}
            )
        
        u_boat: UBoat = game_state.u_boat
        aircraft: Aircraft = game_state.aircraft[self._aircraft_index]
        dice = getattr(game_state, 'dice_roller', None)
        
        # Determine threshold
        self._threshold = 7 if u_boat.lookout_alive else 8
        
        # Roll 2d6
        if dice:
            roll1 = dice.roll_1d6()
            roll2 = dice.roll_1d6()
            self._flak_roll = roll1 + roll2
        else:
            self._flak_roll = 6  # Default to miss if no dice
        
        threshold_text = "7+ (Lookout)" if u_boat.lookout_alive else "8+"
        
        assert self._flak_roll is not None
        if self._flak_roll >= self._threshold:
            # Hit! Determine outcome
            if dice:
                outcome_roll = dice.roll_1d6()
            else:
                outcome_roll = 4  # Default to scared off
            
            if outcome_roll <= 3:
                self._outcome = 'shot_down'
                self._b24_destroyed = True
                
                # Record destroyed B-24 for overlay
                if hasattr(game_state, 'record_destroyed_entity'):
                    game_state.record_destroyed_entity(
                        entity_type='b24',
                        position=aircraft.position,
                        name='B-24'
                    )
                
                return ActionResult(
                    success=True,
                    message=f"Flak rolled [{self._flak_roll}] vs {threshold_text}: B-24 SHOT DOWN!",
                    ap_spent=0,
                    state_changes={}
                )
            else:
                self._outcome = 'scared_off'
                self._b24_destroyed = True
                
                # Record destroyed B-24 for overlay (scared off still removed)
                if hasattr(game_state, 'record_destroyed_entity'):
                    game_state.record_destroyed_entity(
                        entity_type='b24',
                        position=aircraft.position,
                        name='B-24'
                    )
                
                return ActionResult(
                    success=True,
                    message=f"Flak rolled [{self._flak_roll}] vs {threshold_text}: B-24 SCARED OFF!",
                    ap_spent=0,
                    state_changes={}
                )
        else:
            # Miss
            self._outcome = None
            self._b24_destroyed = False
            return ActionResult(
                success=True,
                message=f"Flak rolled [{self._flak_roll}] vs {threshold_text}: B-24 survives",
                ap_spent=0,
                state_changes={}
            )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute with animation trigger.
        
        Future enhancement: Add flak animation
        
        Args:
            game_state: Current game state
        
        Returns:
            ActionResult from execute()
        """
        return self.execute(game_state)
