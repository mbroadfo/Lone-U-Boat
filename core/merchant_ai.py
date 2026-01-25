"""
Merchant ship AI - handles movement along predefined paths.
"""

from typing import List, Tuple, Optional, Dict, Any
from .models import Ship, HexCoord, Facing
from .dice import DiceRoller


class MerchantPath:
    """Represents a merchant ship's predefined path through the mission."""
    
    def __init__(self, waypoints: List[Tuple[int, int]], exit_hex: Optional[Tuple[int, int]] = None):
        """
        Initialize a merchant path.
        
        Args:
            waypoints: List of (q, r) hex coordinates defining the path
            exit_hex: Optional hex coordinate where merchant exits the map
        """
        self.waypoints = [HexCoord(q, r) for q, r in waypoints]
        self.exit_hex = HexCoord(*exit_hex) if exit_hex else None
    
    def get_next_waypoint(self, current_position: HexCoord) -> Optional[HexCoord]:
        """
        Get the next waypoint after the current position.
        
        Args:
            current_position: Current hex coordinate of the ship
            
        Returns:
            Next waypoint or None if at end of path
        """
        try:
            current_index = self.waypoints.index(current_position)
            if current_index < len(self.waypoints) - 1:
                return self.waypoints[current_index + 1]
            else:
                return None  # At end of path
        except ValueError:
            # Current position not in waypoints, return first waypoint
            if self.waypoints:
                return self.waypoints[0]
        return None
    
    def get_facing_for_next_waypoint(self, current_position: HexCoord, next_waypoint: HexCoord) -> Facing:
        """
        Calculate the facing direction needed to move toward the next waypoint.
        
        Args:
            current_position: Current hex coordinate
            next_waypoint: Target hex coordinate
            
        Returns:
            Facing direction toward the waypoint
        """
        # Calculate direction vector
        dq = next_waypoint.q - current_position.q
        dr = next_waypoint.r - current_position.r
        
        # Map direction to Facing
        # Axial directions for flat-top hexes
        if dq == 0 and dr == -1:
            return Facing.NORTH
        elif dq == 1 and dr == -1:
            return Facing.NORTHEAST
        elif dq == 1 and dr == 0:
            return Facing.SOUTHEAST
        elif dq == 0 and dr == 1:
            return Facing.SOUTH
        elif dq == -1 and dr == 1:
            return Facing.SOUTHWEST
        elif dq == -1 and dr == 0:
            return Facing.NORTHWEST
        else:
            # Shouldn't happen if waypoints are adjacent hexes
            # Default to current facing or make a best guess
            return Facing.SOUTH
    
    def is_at_exit(self, position: HexCoord) -> bool:
        """Check if ship has reached the exit hex."""
        return self.exit_hex is not None and position == self.exit_hex


class MerchantAI:
    """AI controller for merchant ships following predefined paths."""
    
    def __init__(self, mission_config: Any, mission_rules: Any, dice_roller: Optional[DiceRoller] = None):
        """
        Initialize merchant AI.
        
        Args:
            mission_config: Mission configuration module with MERCHANT_PATHS
            mission_rules: Mission rules loaded from JSON
            dice_roller: Optional dice roller (defaults to new instance)
        """
        self.mission_config: Any = mission_config
        self.mission_rules: Any = mission_rules
        self.dice = dice_roller or DiceRoller()
        
        # Load merchant paths from mission config
        self.paths: Dict[int, MerchantPath] = {}
        if hasattr(mission_config, 'MERCHANT_PATHS'):
            for path_data in mission_config.MERCHANT_PATHS:
                ship_index = path_data['ship_index']
                self.paths[ship_index] = MerchantPath(
                    waypoints=path_data['waypoints'],
                    exit_hex=path_data.get('exit_hex')
                )
        
        # Load movement rules from JSON
        self.movement_rules: Dict[str, Dict[str, Any]] = {}
        self._load_movement_rules()
    
    def _load_movement_rules(self) -> None:
        """Load merchant movement rules from mission_rules JSON."""
        try:
            # Get merchant movement rules from mission JSON
            merchant_rules = self.mission_rules.get_section_by_id("merchant_movement")
            
            if merchant_rules and "rules" in merchant_rules:
                for rule in merchant_rules["rules"]:
                    condition = rule.get("condition", "UNDAMAGED")
                    self.movement_rules[condition] = rule
        
        except Exception:
            # Fallback to hardcoded defaults if JSON parsing fails
            self.movement_rules = {
                "UNDAMAGED": {
                    "condition": "UNDAMAGED",
                    "action": "MOVE",
                    "distance": 1
                },
                "DAMAGED": {
                    "condition": "DAMAGED",
                    "action": "ROLL_TO_MOVE",
                    "dice": "1d6",
                    "success": "4+",
                    "on_success": {"action": "MOVE", "distance": 1},
                    "on_fail": {"action": "NO_MOVE"}
                }
            }
    
    def get_merchant_movement(
        self,
        ship: Ship,
        ship_index: int
    ) -> Tuple[Optional[HexCoord], Optional[Facing], str]:
        """
        Determine merchant ship movement for this phase.
        
        Args:
            ship: The merchant ship
            ship_index: Index of ship in ships list
            
        Returns:
            Tuple of (new_position, new_facing, message)
            - new_position: Target hex or None if no movement
            - new_facing: New facing direction or None if no change
            - message: Description of what happened
        """
        # Check if this ship has a path
        if ship_index not in self.paths:
            return None, None, f"Merchant ship {ship_index} has no defined path"
        
        path = self.paths[ship_index]
        
        # Check if already at exit
        if path.is_at_exit(ship.position):
            return None, None, f"Merchant has exited the map"
        
        # Get next waypoint
        next_waypoint = path.get_next_waypoint(ship.position)
        if next_waypoint is None:
            return None, None, f"Merchant has reached end of path"
        
        # Calculate facing for the OUTBOUND direction (from next_waypoint to the waypoint after that)
        # This way, when the ship arrives at next_waypoint, it's already facing the right direction
        waypoint_after_next = path.get_next_waypoint(next_waypoint)
        if waypoint_after_next:
            # Face the direction for the next move
            new_facing = path.get_facing_for_next_waypoint(next_waypoint, waypoint_after_next)
        else:
            # This is the last waypoint, face the direction we're moving
            new_facing = path.get_facing_for_next_waypoint(ship.position, next_waypoint)
        
        # Determine movement rules based on damage status
        condition = "DAMAGED" if ship.damaged else "UNDAMAGED"
        rule = self.movement_rules.get(condition)
        
        if not rule:
            # Fallback if no rule found
            return next_waypoint, new_facing, f"Merchant moves to {next_waypoint.q},{next_waypoint.r}"
        
        action = rule.get("action", "MOVE")
        
        if action == "MOVE":
            # Undamaged: Always move
            return next_waypoint, new_facing, f"Merchant moves to {next_waypoint.q},{next_waypoint.r}"
        
        elif action == "ROLL_TO_MOVE":
            # Damaged: Roll to see if can move
            success_str = rule.get("success", "4+")
            success_threshold = int(success_str.replace("+", ""))
            
            roll = self.dice.roll_1d6()
            if roll >= success_threshold:
                return next_waypoint, new_facing, f"Merchant (damaged) rolled {roll}, moves to {next_waypoint.q},{next_waypoint.r}"
            else:
                return None, new_facing, f"Merchant (damaged) rolled {roll}, cannot move but faces {new_facing.name}"
        
        else:
            # Unknown action, default to move
            return next_waypoint, new_facing, f"Merchant moves to {next_waypoint.q},{next_waypoint.r}"
    
    def execute_merchant_phase(self, ships: List[Ship]) -> List[str]:
        """
        Execute the merchant phase for all merchant ships.
        
        Args:
            ships: List of all ships in game
            
        Returns:
            List of messages describing what happened
        """
        messages: List[str] = []
        
        for ship_index, ship in enumerate(ships):
            if ship.ship_type != 'merchant':
                continue
            
            new_position, new_facing, message = self.get_merchant_movement(ship, ship_index)
            
            # Check if destination is blocked by another ship
            if new_position:
                blocked = False
                for other_ship in ships:
                    if other_ship is not ship and other_ship.position == new_position:
                        blocked = True
                        messages.append(f"Merchant cannot move to {new_position.q},{new_position.r} - blocked by {other_ship.ship_type}")
                        break
                
                if not blocked:
                    messages.append(message)
                    # Apply movement
                    ship.position = new_position
                    if new_facing:
                        ship.facing = new_facing
                else:
                    # Can't move but can still turn
                    if new_facing:
                        ship.facing = new_facing
                        messages.append(f"Merchant turns to face {new_facing.name}")
            else:
                messages.append(message)
                # Apply facing change even if not moving
                if new_facing:
                    ship.facing = new_facing
        
        return messages
    
    def check_merchant_exit(self, ships: List[Ship]) -> List[Tuple[int, Ship]]:
        """
        Check if any merchants have reached their exit hex.
        
        Args:
            ships: List of all ships
            
        Returns:
            List of (ship_index, ship) tuples for merchants that have exited
        """
        exited: List[Tuple[int, Ship]] = []
        for ship_index, ship in enumerate(ships):
            if ship.ship_type == 'merchant' and ship_index in self.paths:
                path = self.paths[ship_index]
                if path.is_at_exit(ship.position):
                    exited.append((ship_index, ship))
        return exited
