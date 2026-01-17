"""
Torpedo loading and firing validation for Lone U-Boat.

Validates torpedo actions based on:
- Loading: 2 tubes (1 if Weapons Officer KIA), cannot load damaged tubes
- Firing: Front 4 OR rear 1 (not both), 1-3 torpedoes, Surfaced/Periscope only
- Tube selection with 1-5 numbering (1-4 front, 5 rear)

Rules from u_boat_ruleset_default.json -> LOAD TORPS and FIRE TORPS actions
"""

from typing import Tuple, List, Dict
from .models import UBoat, Depth, TubeState


class TorpedoValidator:
    """
    Validate torpedo loading and firing actions.
    
    Checks all torpedo rules from JSON.
    """
    
    def __init__(self):
        """Initialize torpedo validator."""
        pass
    
    # ========== LOADING VALIDATION ==========
    
    def can_load_torpedo(
        self,
        u_boat: UBoat,
        tube_number: int
    ) -> Tuple[bool, str]:
        """
        Validate if a specific torpedo tube can be loaded.
        
        Rules from u_boat_ruleset_default.json:
        1. Can only load at Surfaced or Periscope depth
        2. Cannot load damaged (already loaded) tubes
        3. Tube must be valid (1-5)
        
        Args:
            u_boat: The player's U-Boat
            tube_number: Tube to load (1-5, user-facing)
            
        Returns:
            (can_load, reason_if_not)
        """
        # Check tube number validity
        if tube_number < 1 or tube_number > 5:
            return False, f"Invalid tube number: {tube_number} (must be 1-5)"
        
        # Check depth restriction
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, f"Can only load torpedoes at Surfaced or Periscope (currently {u_boat.depth.name})"
        
        # Check if tube is already loaded or damaged
        tube_index = tube_number - 1  # Convert to 0-based index
        tube_state = u_boat.torpedo_tubes[tube_index]
        
        if tube_state == TubeState.LOADED:
            return False, f"Tube {tube_number} is already loaded"
        
        if tube_state == TubeState.DAMAGED:
            return False, f"Tube {tube_number} is damaged (must repair first)"
        
        # All checks passed
        return True, ""
    
    def get_loadable_tubes(self, u_boat: UBoat) -> List[int]:
        """
        Get list of tubes that can be loaded.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            List of tube numbers (1-5) that can be loaded
        """
        loadable: List[int] = []
        
        for tube_num in range(1, 6):
            can_load, _ = self.can_load_torpedo(u_boat, tube_num)
            if can_load:
                loadable.append(tube_num)
        
        return loadable
    
    def can_load_tubes(
        self,
        u_boat: UBoat,
        tube_numbers: List[int]
    ) -> Tuple[bool, str]:
        """
        Validate if multiple tubes can be loaded in one action.
        
        Rules:
        - Weapons Officer alive: Can load up to 2 tubes
        - Weapons Officer KIA: Can load only 1 tube
        
        Args:
            u_boat: The player's U-Boat
            tube_numbers: List of tube numbers to load (1-5)
            
        Returns:
            (can_load, reason_if_not)
        """
        if len(tube_numbers) == 0:
            return False, "No tubes specified"
        
        # Check tube limit based on Weapons Officer status
        max_tubes = 2 if u_boat.weapons_officer_alive else 1
        if len(tube_numbers) > max_tubes:
            wo_status = "alive" if u_boat.weapons_officer_alive else "KIA"
            return False, f"Can load max {max_tubes} tube(s) per action (Weapons Officer {wo_status})"
        
        # Validate each tube individually
        for tube_num in tube_numbers:
            can_load, reason = self.can_load_torpedo(u_boat, tube_num)
            if not can_load:
                return False, f"Tube {tube_num}: {reason}"
        
        # Check for duplicates
        if len(tube_numbers) != len(set(tube_numbers)):
            return False, "Cannot load same tube multiple times"
        
        return True, ""
    
    # ========== FIRING VALIDATION ==========
    
    def can_fire_torpedo(
        self,
        u_boat: UBoat,
        tube_number: int
    ) -> Tuple[bool, str]:
        """
        Validate if a specific torpedo tube can be fired.
        
        Rules:
        1. Can only fire at Surfaced or Periscope depth
        2. Tube must be loaded
        3. Tube must be valid (1-5)
        
        Args:
            u_boat: The player's U-Boat
            tube_number: Tube to fire (1-5, user-facing)
            
        Returns:
            (can_fire, reason_if_not)
        """
        # Check tube number validity
        if tube_number < 1 or tube_number > 5:
            return False, f"Invalid tube number: {tube_number} (must be 1-5)"
        
        # Check depth restriction
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, f"Can only fire torpedoes at Surfaced or Periscope (currently {u_boat.depth.name})"
        
        # Check if tube is loaded
        tube_index = tube_number - 1  # Convert to 0-based index
        tube_state = u_boat.torpedo_tubes[tube_index]
        
        if tube_state != TubeState.LOADED:
            if tube_state == TubeState.DAMAGED:
                return False, f"Tube {tube_number} is damaged"
            else:
                return False, f"Tube {tube_number} is not loaded"
        
        # All checks passed
        return True, ""
    
    def can_fire_tubes(
        self,
        u_boat: UBoat,
        tube_numbers: List[int]
    ) -> Tuple[bool, str]:
        """
        Validate if multiple tubes can be fired in one action.
        
        Rules:
        - Can fire 1, 2, or 3 torpedoes
        - Front 4 tubes (1-4) OR rear 1 tube (5), not both
        
        Args:
            u_boat: The player's U-Boat
            tube_numbers: List of tube numbers to fire (1-5)
            
        Returns:
            (can_fire, reason_if_not)
        """
        if len(tube_numbers) == 0:
            return False, "No tubes specified"
        
        # Check tube count limit (1-3)
        if len(tube_numbers) > 3:
            return False, "Can fire maximum 3 torpedoes per action"
        
        # Validate each tube individually
        for tube_num in tube_numbers:
            can_fire, reason = self.can_fire_torpedo(u_boat, tube_num)
            if not can_fire:
                return False, f"Tube {tube_num}: {reason}"
        
        # Check for duplicates
        if len(tube_numbers) != len(set(tube_numbers)):
            return False, "Cannot fire same tube multiple times"
        
        # Check front/rear restriction
        has_front = any(t <= 4 for t in tube_numbers)
        has_rear = any(t == 5 for t in tube_numbers)
        
        if has_front and has_rear:
            return False, "Cannot fire front and rear tubes in same action (choose front 1-4 OR rear 5)"
        
        return True, ""
    
    def get_fireable_tubes(self, u_boat: UBoat) -> Dict[str, List[int]]:
        """
        Get tubes that can be fired, separated by front/rear.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            Dict with 'front' and 'rear' lists of tube numbers
        """
        front: List[int] = []
        rear: List[int] = []
        
        for tube_num in range(1, 6):
            can_fire, _ = self.can_fire_torpedo(u_boat, tube_num)
            if can_fire:
                if tube_num <= 4:
                    front.append(tube_num)
                else:
                    rear.append(tube_num)
        
        return {"front": front, "rear": rear}
    
    # ========== INFO METHODS ==========
    
    def get_tube_status(self, u_boat: UBoat) -> str:
        """
        Get formatted status of all torpedo tubes.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            Formatted string with tube status
        """
        front_status: List[str] = []
        for i in range(4):
            state = u_boat.torpedo_tubes[i]
            if state == TubeState.LOADED:
                status = "●"
            elif state == TubeState.DAMAGED:
                status = "✕"
            else:  # EMPTY
                status = "○"
            front_status.append(f"{i+1}:{status}")
        
        rear_state = u_boat.torpedo_tubes[4]
        if rear_state == TubeState.LOADED:
            rear_status = "●"
        elif rear_state == TubeState.DAMAGED:
            rear_status = "✕"
        else:  # EMPTY
            rear_status = "○"
        
        parts = [
            f"Front (1-4): {' '.join(front_status)}",
            f"Rear (5): {rear_status}",
            "● = loaded, ○ = empty, ✕ = damaged"
        ]
        
        return " | ".join(parts)
    
    def get_load_info(self, u_boat: UBoat) -> str:
        """
        Get formatted info about loading capabilities.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            Formatted string with loading info
        """
        loadable = self.get_loadable_tubes(u_boat)
        max_tubes = 2 if u_boat.weapons_officer_alive else 1
        wo_status = "Alive" if u_boat.weapons_officer_alive else "KIA"
        
        parts = [
            f"Depth: {u_boat.depth.name}",
            f"Weapons Officer: {wo_status}",
            f"Can load: {max_tubes} tube(s) per action",
            f"Available: {loadable if loadable else 'None'}"
        ]
        
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            parts.append("✗ Must be at Surfaced or Periscope")
        elif len(loadable) == 0:
            parts.append("✗ All tubes loaded")
        else:
            parts.append("✓ Can load")
        
        return " | ".join(parts)
    
    def get_fire_info(self, u_boat: UBoat) -> str:
        """
        Get formatted info about firing capabilities.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            Formatted string with firing info
        """
        fireable = self.get_fireable_tubes(u_boat)
        
        parts = [
            f"Depth: {u_boat.depth.name}",
            f"Can fire: 1-3 torpedoes",
            f"Front ready: {fireable['front'] if fireable['front'] else 'None'}",
            f"Rear ready: {fireable['rear'] if fireable['rear'] else 'None'}"
        ]
        
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            parts.append("✗ Must be at Surfaced or Periscope")
        elif not fireable['front'] and not fireable['rear']:
            parts.append("✗ No loaded tubes")
        else:
            parts.append("✓ Can fire (choose front OR rear)")
        
        return " | ".join(parts)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return "<TorpedoValidator: 5 tubes (1-4 front, 5 rear)>"
