"""
Merchant Visual Detection Action - Player checks merchant visual sighting.

Implements merchant automatic visual detection of U-boat at close range.
Merchants at DL 3 can visually spot U-boat at range 1 (adjacent hex).
"""

from typing import Tuple, Any, Optional, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import Ship, UBoat, Depth, HexCoord


class MerchantVisualAction(AIAction):
    """
    Player-executed action for merchant visual detection check.
    
    At Detection Level 3, merchants can spot U-boat visually if adjacent (range 1).
    This is an automatic check (no dice roll) - proximity determines success.
    
    Follows solitaire board game pattern:
    1. Present merchant visual detection check
    2. Player confirms check
    3. Show result (spotted or not spotted)
    """
    
    def __init__(
        self,
        ship_index: int,
        current_detection_level: int,
        visual_range: int = 1
    ):
        """
        Initialize merchant visual detection action.
        
        Args:
            ship_index: Index of merchant in ships list
            current_detection_level: Current DL (must be 3 for visual detection)
            visual_range: Visual detection range in hexes (default 1 = adjacent)
        """
        super().__init__(entity_index=ship_index)
        self._ship_index = ship_index
        self._current_detection_level = current_detection_level
        self._visual_range = visual_range
        
        # Action results (properties)
        self._spotted: bool = False
        self._range_to_uboat: Optional[int] = None
    
    @property
    def ship_index(self) -> int:
        """Index of merchant checking for visual."""
        return self._ship_index
    
    @property
    def spotted(self) -> bool:
        """Whether merchant spotted U-boat."""
        return self._spotted
    
    @property
    def range_to_uboat(self) -> Optional[int]:
        """Range from merchant to U-boat in hexes."""
        return self._range_to_uboat
    
    def get_entity(self, game_state: Any) -> Any:
        """Get the merchant ship checking visual."""
        ships = getattr(game_state, 'ships', [])
        if 0 <= self._ship_index < len(ships):
            return ships[self._ship_index]
        return None
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI display."""
        merchant = self.get_entity(game_state)
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        
        if not merchant or not u_boat:
            return {"action": "Merchant Visual", "status": "Invalid"}
        
        # Get range
        hex_grid = getattr(game_state, 'hex_grid', None)
        if hex_grid:
            range_hex = hex_grid.hex_distance(merchant.position, u_boat.position)
        else:
            range_hex = 0
        
        return {
            "action": "Merchant Visual Detection",
            "merchant": merchant.ship_type.capitalize(),
            "range": range_hex,
            "visual_range": self._visual_range,
            "current_dl": self._current_detection_level,
            "depth": u_boat.depth.name
        }
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate merchant visual check can be made.
        
        Args:
            game_state: Current game state
            
        Returns:
            Tuple of (can_check, reason)
        """
        # Get merchant
        ships = getattr(game_state, 'ships', [])
        if self._ship_index < 0 or self._ship_index >= len(ships):
            return False, "Invalid ship index"
        
        merchant = ships[self._ship_index]
        
        # Only merchants check visual
        if merchant.ship_type not in ['tanker', 'freighter']:
            return False, f"{merchant.ship_type.capitalize()} is not a merchant"
        
        # Must be at DL 3 for visual detection
        if self._current_detection_level < 3:
            return False, f"Visual detection requires DL 3 (current: {self._current_detection_level})"
        
        # Get U-boat
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        if not u_boat:
            return False, "No U-boat in game state"
        
        # U-boat must be surfaced or at periscope depth to be seen
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, f"U-boat at {u_boat.depth.name} cannot be visually detected"
        
        # Get hex grid for range calculation
        hex_grid = getattr(game_state, 'hex_grid', None)
        if not hex_grid:
            return False, "No hex grid in game state"
        
        # Check range (visual is short range - adjacent only)
        range_to_uboat = hex_grid.hex_distance(merchant.position, u_boat.position)
        if range_to_uboat > self._visual_range:
            return False, f"Out of visual range (R{range_to_uboat} > {self._visual_range})"
        
        return True, f"Can check visual at range {range_to_uboat}"
    
    def execute(self, game_state: Any) -> ActionResult:
        """
        Execute merchant visual detection check.
        
        Automatic check - no dice roll. Merchant spots U-boat if within visual range
        and U-boat is at correct depth.
        
        Args:
            game_state: Current game state
            
        Returns:
            ActionResult with visual detection outcome
        """
        # Get merchant
        ships = getattr(game_state, 'ships', [])
        merchant = ships[self._ship_index]
        
        # Get U-boat
        u_boat = getattr(game_state, 'u_boat', None) or getattr(game_state, 'uboat', None)
        
        # Get hex grid
        hex_grid = getattr(game_state, 'hex_grid', None)
        
        # Calculate range
        self._range_to_uboat = hex_grid.hex_distance(merchant.position, u_boat.position)
        
        # Automatic check - if within range and at correct depth, spotted
        in_range = self._range_to_uboat <= self._visual_range
        visible_depth = u_boat.depth in [Depth.SURFACED, Depth.PERISCOPE]
        
        self._spotted = in_range and visible_depth
        
        if self._spotted:
            return ActionResult(
                success=True,
                message=(
                    f"{merchant.ship_type.capitalize()} at R{self._range_to_uboat} "
                    f"VISUALLY SPOTS U-boat at {u_boat.depth.name}!"
                ),
                ap_spent=0,
                state_changes={}
            )
        else:
            # Determine reason for not spotting
            if not in_range:
                reason = f"out of visual range (R{self._range_to_uboat})"
            elif not visible_depth:
                reason = f"U-boat too deep ({u_boat.depth.name})"
            else:
                reason = "unknown"
            
            return ActionResult(
                success=True,
                message=(
                    f"{merchant.ship_type.capitalize()} at R{self._range_to_uboat} "
                    f"checks visual: No U-boat spotted ({reason})"
                ),
                ap_spent=0,
                state_changes={}
            )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute visual check with animation support (calls execute)."""
        return self.execute(game_state)
