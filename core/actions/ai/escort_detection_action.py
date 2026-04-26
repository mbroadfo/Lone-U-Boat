"""
Escort Detection Action - Player executes escort detection roll.

Implements solitaire-style detection where player rolls dice for escort
attempting to detect U-boat during Detection Phase.
"""

from typing import Tuple, Any, Optional, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import UBoat, Depth, HexCoord


class EscortDetectionAction(AIAction):
    """
    Player-executed action for escort detection attempt.
    
    The player rolls 1d6 for an escort attempting to detect the U-boat.
    Detection threshold depends on U-boat depth, sonar operator status, and engine damage.
    Successful detection increases Detection Level by 1.
    
    Follows solitaire board game pattern:
    1. Present escort detection attempt with calculated threshold
    2. Player rolls 1d6
    3. Compare roll to threshold
    4. Update Detection Level if successful
    """
    
    def __init__(
        self,
        ship_index: int,
        current_detection_level: int,
        detection_range: int = 3,
        requires_los: bool = True
    ):
        """
        Initialize escort detection action.
        
        Args:
            ship_index: Index of escort in ships list
            current_detection_level: Current DL (0-3)
            detection_range: Maximum detection range in hexes (default 3)
            requires_los: Whether line-of-sight is required (default True)
        """
        super().__init__(entity_index=ship_index)
        self._ship_index = ship_index
        self._current_detection_level = current_detection_level
        self._detection_range = detection_range
        self._requires_los = requires_los
        
        # Action results (properties)
        self._threshold: Optional[int] = None
        self._roll: Optional[int] = None
        self._success: bool = False
        self._new_detection_level: Optional[int] = None
        self._range_to_uboat: Optional[int] = None
    
    @property
    def ship_index(self) -> int:
        """Index of detecting escort."""
        return self._ship_index
    
    @property
    def threshold(self) -> Optional[int]:
        """Detection threshold (1d6 must equal or exceed this)."""
        return self._threshold
    
    @property
    def roll(self) -> Optional[int]:
        """Player's 1d6 roll result."""
        return self._roll
    
    @property
    def success(self) -> bool:
        """Whether detection succeeded."""
        return self._success
    
    @property
    def new_detection_level(self) -> Optional[int]:
        """New detection level after this action."""
        return self._new_detection_level
    
    @property
    def range_to_uboat(self) -> Optional[int]:
        """Range from escort to U-boat in hexes."""
        return self._range_to_uboat
    
    def get_entity(self, game_state: Any) -> Any:
        """Get the escort ship performing detection."""
        ships = getattr(game_state, 'ships', [])
        if 0 <= self._ship_index < len(ships):
            return ships[self._ship_index]
        return None
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI display."""
        escort = self.get_entity(game_state)
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        
        if not escort or not u_boat:
            return {"action": "Escort Detection", "status": "Invalid"}
        
        # Calculate threshold
        threshold = self._calculate_threshold(u_boat)
        
        # Get range
        hex_grid = getattr(game_state, 'hex_grid', None)
        if hex_grid:
            range_hex = hex_grid.hex_distance(escort.position, u_boat.position)
        else:
            range_hex = 0
        
        return {
            "action": "Escort Detection",
            "escort": escort.ship_type.capitalize(),
            "range": range_hex,
            "threshold": f"{threshold}+",
            "current_dl": self._current_detection_level,
            "depth": u_boat.depth.name
        }
    
    def _calculate_threshold(self, u_boat: UBoat) -> int:
        """
        Calculate detection threshold based on U-boat depth and modifiers.
        
        Base thresholds by depth:
        - SURFACED: 1 (auto-detect)
        - PERISCOPE: 2
        - MEDIUM: 4
        - DEEP: 5
        
        Modifiers:
        - Sonar Operator alive: +1 (harder to detect)
        - Engine damaged: -1 (easier to detect - noisy)
        
        Args:
            u_boat: The U-boat being detected
            
        Returns:
            Threshold value (1-6)
        """
        # Base threshold by depth
        base_thresholds = {
            Depth.SURFACED: 1,
            Depth.PERISCOPE: 2,
            Depth.MEDIUM: 4,
            Depth.DEEP: 5,
        }
        threshold = base_thresholds.get(u_boat.depth, 4)
        
        # Modifier: Sonar operator makes U-boat harder to detect
        if u_boat.sonar_operator_alive:
            threshold += 1
        
        # Modifier: Engine damage makes U-boat easier to detect (noisy)
        if u_boat.engine_damaged:
            threshold -= 1
        
        # Clamp to valid range
        threshold = max(1, min(6, threshold))
        
        return threshold
    
    def _check_line_of_sight(
        self,
        from_hex: HexCoord,
        to_hex: HexCoord,
        land_hexes: set[HexCoord],
        hex_grid: Any
    ) -> bool:
        """
        Check if line of sight exists between escort and U-boat.
        
        Args:
            from_hex: Escort position
            to_hex: U-boat position
            land_hexes: Set of land hexes that block LOS
            hex_grid: Hex grid for calculations
            
        Returns:
            True if LOS exists, False if blocked by land
        """
        # Adjacent hexes always have LOS
        distance = hex_grid.hex_distance(from_hex, to_hex)
        if distance <= 1:
            return True
        
        # Check intermediate hexes for land
        dq = to_hex.q - from_hex.q
        dr = to_hex.r - from_hex.r
        steps = max(abs(dq), abs(dr))
        
        if steps == 0:
            return True
        
        for i in range(1, steps):
            t = i / steps
            check_q = round(from_hex.q + t * dq)
            check_r = round(from_hex.r + t * dr)
            check_hex = HexCoord(check_q, check_r)
            
            if check_hex in land_hexes:
                return False
        
        return True
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate detection attempt can be made.
        
        Args:
            game_state: Current game state
            
        Returns:
            Tuple of (can_detect, reason)
        """
        # Get escort
        ships = getattr(game_state, 'ships', [])
        if self._ship_index < 0 or self._ship_index >= len(ships):
            return False, "Invalid ship index"
        
        escort = ships[self._ship_index]
        
        # Only corvettes and destroyers can detect
        if escort.ship_type not in ['corvette', 'destroyer']:
            return False, f"{escort.ship_type.capitalize()} cannot detect"
        
        # Check if already at max DL
        if self._current_detection_level >= 3:
            return False, "Detection Level already at maximum (3)"
        
        # Get U-boat
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        if not u_boat:
            return False, "No U-boat in game state"
        
        # Get hex grid for range calculation
        hex_grid = getattr(game_state, 'hex_grid', None)
        if not hex_grid:
            return False, "No hex grid in game state"
        
        # Check range
        range_to_uboat = hex_grid.hex_distance(escort.position, u_boat.position)
        if range_to_uboat > self._detection_range:
            return False, f"Out of range (R{range_to_uboat} > {self._detection_range})"
        
        # Check line of sight if required
        if self._requires_los:
            land_hexes: set[HexCoord] = getattr(game_state, 'land_hexes', set())
            has_los = self._check_line_of_sight(
                escort.position,
                u_boat.position,
                land_hexes,
                hex_grid
            )
            if not has_los:
                return False, "No line of sight (blocked by land)"
        
        return True, f"Can detect at range {range_to_uboat}"
    
    def execute(self, game_state: Any) -> ActionResult:
        """
        Execute detection roll.
        
        Player rolls 1d6 and compares to threshold. Success increases DL by 1.
        
        Args:
            game_state: Current game state
            
        Returns:
            ActionResult with detection outcome
        """
        # Get escort
        ships = getattr(game_state, 'ships', [])
        escort = ships[self._ship_index]
        
        # Get U-boat
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        
        # Get hex grid
        hex_grid = getattr(game_state, 'hex_grid', None)
        
        # Type narrowing - validation ensures these are not None
        assert u_boat is not None, "U-boat must exist for detection"
        assert hex_grid is not None, "Hex grid must exist"
        
        # Calculate range
        self._range_to_uboat = hex_grid.hex_distance(escort.position, u_boat.position)
        
        # Calculate threshold
        self._threshold = self._calculate_threshold(u_boat)
        
        # Type narrowing for Optional fields that are now assigned
        assert self._threshold is not None
        
        # Get dice roller
        dice = getattr(game_state, 'dice_roller', None)
        if not dice:
            return ActionResult(
                success=False,
                message="No dice roller available",
                ap_spent=0,
                state_changes={}
            )
        
        # Player rolls 1d6
        self._roll = dice.roll_1d6(context=f"{escort.ship_type}_detection")
        
        # Type narrowing - roll and threshold are now assigned
        assert self._roll is not None
        assert self._threshold is not None
        
        # Check success
        self._success = self._roll >= self._threshold
        
        # Calculate new DL — read live state so sequential successes each add +1
        if self._success:
            current_live_dl = getattr(game_state, 'detection_level', self._current_detection_level)
            self._new_detection_level = min(3, current_live_dl + 1)

            # Update game state DL
            if hasattr(game_state, 'detection_level'):
                game_state.detection_level = self._new_detection_level

            return ActionResult(
                success=True,
                message=(
                    f"{escort.ship_type.capitalize()} at R{self._range_to_uboat} "
                    f"rolled [{self._roll}] vs {self._threshold}+: SUCCESS! "
                    f"DL {current_live_dl} -> {self._new_detection_level}"
                ),
                ap_spent=0,
                state_changes={"detection_level": self._new_detection_level}
            )
        else:
            self._new_detection_level = self._current_detection_level
            
            return ActionResult(
                success=True,
                message=(
                    f"{escort.ship_type.capitalize()} at R{self._range_to_uboat} "
                    f"rolled [{self._roll}] vs {self._threshold}+: Failed (no DL change)"
                ),
                ap_spent=0,
                state_changes={}
            )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute detection with animation support (calls execute)."""
        return self.execute(game_state)
