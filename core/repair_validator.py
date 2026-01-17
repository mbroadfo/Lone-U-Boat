"""
Repair action validation for Lone U-Boat.

Validates repair actions based on:
- Component type (Engine, Torpedo Tubes, Deck Gun, Flak Gun)
- Current depth (surface vs submerged)
- Crew status (Engineer alive/KIA)
- Component-specific restrictions

Rules from u_boat_ruleset_default.json -> REPAIR action
"""

from typing import Tuple, List
from .models import UBoat, Depth, TubeState


class RepairValidator:
    """
    Validate U-Boat repair actions.
    
    Checks all repair rules from JSON.
    """
    
    # Component types that can be repaired
    REPAIRABLE_COMPONENTS = ["Engine", "Torpedo Tubes", "Deck Gun", "Flak Gun"]
    
    # Components that require Surfaced depth
    SURFACE_ONLY_COMPONENTS = ["Deck Gun", "Flak Gun"]
    
    def __init__(self):
        """Initialize repair validator."""
        pass
    
    def can_repair_component(
        self,
        u_boat: UBoat,
        component: str
    ) -> Tuple[bool, str]:
        """
        Validate if a component can be repaired.
        
        Rules from u_boat_ruleset_default.json:
        1. Hull damage cannot be repaired
        2. Deck Gun and Flak Gun: Surfaced only
        3. Engine and Torpedo Tubes: 2 AP at Surface (always), 4 AP submerged (only if Engineer alive)
        4. If Engineer is KIA: Only Surface repairs possible
        
        Args:
            u_boat: The player's U-Boat
            component: Component name to repair
            
        Returns:
            (can_repair, reason_if_not)
            - can_repair: True if repair is valid
            - reason_if_not: String explaining why repair blocked
        """
        # Check if component is valid
        if component not in self.REPAIRABLE_COMPONENTS:
            return False, f"'{component}' cannot be repaired (invalid component)"
        
        # Check if component is actually damaged
        if not self._is_component_damaged(u_boat, component):
            return False, f"{component} is not damaged"
        
        # Rule 2: Deck Gun and Flak Gun must be at Surface
        if component in self.SURFACE_ONLY_COMPONENTS:
            if u_boat.depth != Depth.SURFACED:
                return False, f"{component} can only be repaired when Surfaced"
        
        # Rule 3 & 4: Submerged repairs require Engineer
        if u_boat.depth != Depth.SURFACED:
            if not u_boat.engineer_alive:
                return False, f"Submerged repair requires Engineer (currently KIA)"
        
        # All checks passed
        return True, ""
    
    def get_repair_ap_cost(
        self,
        component: str,
        depth: Depth,
        engineer_alive: bool
    ) -> int:
        """
        Calculate AP cost for repairing a component.
        
        Rules from u_boat_ruleset_default.json:
        - Surfaced: 2 AP (always)
        - Submerged: 4 AP (if Engineer alive)
        
        Args:
            component: Component name
            depth: Current U-Boat depth
            engineer_alive: Whether Engineer is alive
            
        Returns:
            AP cost (0 if repair not possible)
        """
        if component not in self.REPAIRABLE_COMPONENTS:
            return 0
        
        # Surface repairs always cost 2 AP
        if depth == Depth.SURFACED:
            return 2
        
        # Submerged repairs cost 4 AP (only if Engineer alive)
        if engineer_alive:
            return 4
        
        # Cannot repair submerged without Engineer
        return 0
    
    def get_repairable_components(self, u_boat: UBoat) -> List[str]:
        """
        Get list of components that can currently be repaired.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            List of component names that are damaged and repairable
        """
        repairable: List[str] = []
        
        for component in self.REPAIRABLE_COMPONENTS:
            can_repair, _ = self.can_repair_component(u_boat, component)
            if can_repair:
                repairable.append(component)
        
        return repairable
    
    def get_repair_info(
        self,
        u_boat: UBoat,
        component: str
    ) -> str:
        """
        Get detailed info about repairing a component.
        
        Args:
            u_boat: The player's U-Boat
            component: Component name
            
        Returns:
            Formatted string with repair info and validity
        """
        can_repair, reason = self.can_repair_component(u_boat, component)
        
        info_parts: List[str] = []
        
        # Component name
        info_parts.append(f"Repair: {component}")
        
        # Damage status
        if self._is_component_damaged(u_boat, component):
            info_parts.append("DAMAGED")
        else:
            info_parts.append("OK")
        
        # Depth requirement for surface-only components
        if component in self.SURFACE_ONLY_COMPONENTS:
            info_parts.append("Surfaced Only")
        
        # Engineer requirement
        if u_boat.depth != Depth.SURFACED:
            if u_boat.engineer_alive:
                info_parts.append("Engineer: Alive")
            else:
                info_parts.append("Engineer: KIA (need Surface)")
        
        # AP cost
        ap_cost = self.get_repair_ap_cost(component, u_boat.depth, u_boat.engineer_alive)
        if ap_cost > 0:
            info_parts.append(f"Cost: {ap_cost} AP")
        
        # Validity
        if can_repair:
            info_parts.append("✓ Can Repair")
        else:
            info_parts.append(f"✗ {reason}")
        
        return " | ".join(info_parts)
    
    def get_damaged_torpedo_tubes(self, u_boat: UBoat) -> List[int]:
        """
        Get list of damaged torpedo tube numbers.
        
        Tubes are numbered 1-5 (user-facing):
        - Tubes 1-4: Forward facing
        - Tube 5: Rearward facing
        
        Note: Only returns DAMAGED tubes, not empty tubes.
        Empty tubes can be loaded, damaged tubes must be repaired first.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            List of tube numbers (1-5) that are damaged
        """
        damaged_tubes: List[int] = []
        for i, tube_state in enumerate(u_boat.torpedo_tubes):
            if tube_state == TubeState.DAMAGED:
                damaged_tubes.append(i + 1)  # Convert to 1-based numbering
        return damaged_tubes
    
    def get_torpedo_tube_repair_options(self, u_boat: UBoat) -> str:
        """
        Get formatted info about torpedo tube repair.
        
        Note: Repair action can fix up to 2 torpedo tubes at once.
        Tubes 1-4 are forward facing, tube 5 is rearward facing.
        
        Args:
            u_boat: The player's U-Boat
            
        Returns:
            Formatted string with tube status (uses 1-based tube numbers)
        """
        damaged = self.get_damaged_torpedo_tubes(u_boat)
        
        if len(damaged) == 0:
            return "All torpedo tubes loaded (none need repair)"
        
        # Tubes 1-4 are forward, tube 5 is rear
        front_damaged = [t for t in damaged if t <= 4]
        rear_damaged = [t for t in damaged if t == 5]
        
        parts: List[str] = []
        parts.append(f"Damaged tubes: {damaged}")
        parts.append(f"{len(damaged)} total")
        
        if front_damaged:
            parts.append(f"Front (1-4): {front_damaged}")
        if rear_damaged:
            parts.append(f"Rear (5): {rear_damaged}")
        
        parts.append("Can repair: up to 2 tubes")
        
        return " | ".join(parts)
    
    def _is_component_damaged(self, u_boat: UBoat, component: str) -> bool:
        """
        Check if a component is damaged.
        
        Args:
            u_boat: The player's U-Boat
            component: Component name
            
        Returns:
            True if component is damaged
        """
        if component == "Engine":
            return u_boat.engine_damaged
        elif component == "Deck Gun":
            return u_boat.deck_gun_damaged
        elif component == "Flak Gun":
            return u_boat.flak_gun_damaged
        elif component == "Torpedo Tubes":
            # Check if any torpedo tubes are damaged
            # Repair action can fix up to 2 tubes at once
            damaged_count = sum(1 for tube_state in u_boat.torpedo_tubes 
                               if tube_state == TubeState.DAMAGED)
            return damaged_count > 0
        else:
            return False
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<RepairValidator: {len(self.REPAIRABLE_COMPONENTS)} repairable components>"
