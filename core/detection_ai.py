"""
Detection Phase AI - handles escort detection rolls against U-boat.
"""

from typing import List, Tuple, Set, Any
from .models import Ship, UBoat, HexCoord, Depth
from .hex_grid import HexGrid
from .dice import DiceRoller


class DetectionAI:
    """AI controller for escort detection during Detection Phase."""
    
    def __init__(self, mission_rules: Any, dice_roller: DiceRoller):
        """
        Initialize detection AI.
        
        Args:
            mission_rules: Mission rules loaded from JSON (includes escort_ai_baseline)
            dice_roller: Dice roller for detection rolls
        """
        self.mission_rules: Any = mission_rules
        self.dice = dice_roller
        
        # Load detection rules from mission_rules (escort_ai_baseline.json -> detection_system)
        self.detection_range: int = 3
        self.requires_los: bool = True
        self.base_thresholds: dict[Depth, int] = {}
        self.modifier_sonar_operator: int = 1
        self.modifier_engine_damaged: int = -1
        
        self._load_detection_rules()
    
    def _load_detection_rules(self) -> None:
        """Load detection rules from mission_rules JSON."""
        try:
            # Get detection rules from escort_ai_baseline.json
            detection_rules = self.mission_rules.get_section_by_id("detection_rules")
            
            if detection_rules:
                # Parse range and LOS requirements
                self.detection_range = detection_rules.get("range", 3)
                self.requires_los = detection_rules.get("requires_los", True)
                
                # Parse base detection thresholds by depth
                base_thresholds_data = detection_rules.get("base_detection_thresholds", [])
                for threshold_entry in base_thresholds_data:
                    depth_str = threshold_entry.get("depth", "")
                    roll_required = threshold_entry.get("roll_required", 4)
                    
                    try:
                        depth_enum = Depth[depth_str]
                        self.base_thresholds[depth_enum] = roll_required
                    except KeyError:
                        # Unknown depth, skip
                        pass
                
                # Parse modifiers
                modifiers_data = detection_rules.get("modifiers", [])
                for modifier in modifiers_data:
                    condition = modifier.get("condition", "")
                    effect = modifier.get("effect", 0)
                    
                    if condition == "sonar_operator_alive":
                        self.modifier_sonar_operator = effect
                    elif condition == "engine_damaged":
                        self.modifier_engine_damaged = effect
        
        except Exception:
            # Fallback to hardcoded defaults if JSON parsing fails
            self.detection_range = 3
            self.requires_los = True
            self.base_thresholds = {
                Depth.SURFACED: 1,
                Depth.PERISCOPE: 2,
                Depth.MEDIUM: 4,
                Depth.DEEP: 5,
            }
            self.modifier_sonar_operator = 1
            self.modifier_engine_damaged = -1
    
    def calculate_detection_threshold(
        self,
        u_boat: UBoat
    ) -> int:
        """
        Calculate the detection roll threshold based on U-boat depth and modifiers.
        
        Args:
            u_boat: The U-boat being detected
            
        Returns:
            Roll required for detection (1d6 must meet or exceed this)
        """
        # Start with base threshold for current depth
        threshold = self.base_thresholds.get(u_boat.depth, 4)
        
        # Modifier 1: Sonar Operator alive increases threshold (harder to detect)
        if u_boat.sonar_operator_alive:
            threshold += self.modifier_sonar_operator
        
        # Modifier 2: Engine damaged decreases threshold (easier to detect - noisy)
        if u_boat.engine_damaged:
            threshold += self.modifier_engine_damaged  # Note: modifier is negative
        
        # Threshold can never be less than 1 (automatic) or more than 6 (impossible)
        threshold = max(1, min(6, threshold))
        
        return threshold
    
    def check_escort_can_detect(
        self,
        escort: Ship,
        u_boat: UBoat,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid
    ) -> Tuple[bool, str]:
        """
        Check if an escort can attempt detection.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            land_hexes: Set of land hexes that block LOS
            hex_grid: Hex grid for range calculation
            
        Returns:
            Tuple of (can_detect, reason)
        """
        # Only corvettes and destroyers can detect
        if escort.ship_type not in ['corvette', 'destroyer']:
            return False, f"{escort.ship_type.capitalize()} cannot detect"
        
        # Calculate range
        range_to_uboat = hex_grid.hex_distance(escort.position, u_boat.position)
        
        # Check range requirement (3 hexes or less)
        if range_to_uboat > self.detection_range:
            return False, f"Out of range (R{range_to_uboat} > 3)"
        
        # Check line of sight if required
        if self.requires_los:
            has_los = self._check_line_of_sight(
                escort.position,
                u_boat.position,
                land_hexes,
                hex_grid
            )
            if not has_los:
                return False, f"No line of sight"
        
        return True, f"In range (R{range_to_uboat}), has LOS"
    
    def _check_line_of_sight(
        self,
        from_hex: HexCoord,
        to_hex: HexCoord,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid
    ) -> bool:
        """
        Check if LOS exists between two hexes.
        
        Args:
            from_hex: Starting hex
            to_hex: Target hex
            land_hexes: Set of land hexes that block LOS
            hex_grid: Hex grid for path calculation
            
        Returns:
            True if LOS exists, False if blocked
        """
        # Adjacent hexes or same hex always have LOS
        distance = hex_grid.hex_distance(from_hex, to_hex)
        if distance <= 1:
            return True
        
        # Get path between hexes (simplified - straight line check)
        # For more complex LOS, could use hex_grid.get_line_hexes or similar
        # For now, check if any land hex is directly between
        
        # Simple check: if path crosses land, LOS is blocked
        # This is simplified - a full implementation would trace the line
        # For detection purposes, we'll use a conservative approach
        
        # Calculate direction vector
        dq = to_hex.q - from_hex.q
        dr = to_hex.r - from_hex.r
        
        # Check intermediate hexes along the line
        steps = max(abs(dq), abs(dr))
        if steps == 0:
            return True
        
        for i in range(1, steps):
            # Interpolate position
            t = i / steps
            check_q = round(from_hex.q + t * dq)
            check_r = round(from_hex.r + t * dr)
            check_hex = HexCoord(check_q, check_r)
            
            # If land hex blocks LOS
            if check_hex in land_hexes:
                return False
        
        return True
    
    def execute_detection_phase(
        self,
        ships: List[Ship],
        u_boat: UBoat,
        current_detection_level: int,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid
    ) -> Tuple[int, List[str]]:
        """
        Execute the detection phase for all escorts.
        
        Args:
            ships: List of all ships in game
            u_boat: The U-boat
            current_detection_level: Current DL (0-3)
            land_hexes: Set of land hexes for LOS
            hex_grid: Hex grid for distance calculations
            
        Returns:
            Tuple of (new_detection_level, messages)
        """
        messages: List[str] = []
        
        # Skip if already at max detection
        if current_detection_level >= 3:
            messages.append("Detection Level already at maximum (3), skipping detection rolls")
            return current_detection_level, messages
        
        # Calculate detection threshold
        threshold = self.calculate_detection_threshold(u_boat)
        
        # Build concise threshold calculation message
        base_threshold = self.base_thresholds.get(u_boat.depth, 4)
        modifiers = []
        if u_boat.sonar_operator_alive:
            modifiers.append(f"+{self.modifier_sonar_operator} Sonar")
        if u_boat.engine_damaged:
            modifiers.append(f"{self.modifier_engine_damaged} Engine")
        
        if modifiers:
            mod_str = ", ".join(modifiers)
            messages.append(f"U-boat at {u_boat.depth.name}, need {threshold}+ [base {base_threshold}, {mod_str}]")
        else:
            messages.append(f"U-boat at {u_boat.depth.name}, need {threshold}+")
        
        # Find escorts that can attempt detection
        detecting_escorts: List[Tuple[Ship, str]] = []
        for ship in ships:
            can_detect, reason = self.check_escort_can_detect(
                ship, u_boat, land_hexes, hex_grid
            )
            if can_detect:
                detecting_escorts.append((ship, reason))
            else:
                # Log why escort cannot detect
                if ship.ship_type in ['corvette', 'destroyer']:
                    messages.append(f"  {ship.ship_type.capitalize()}: {reason}")
        
        if not detecting_escorts:
            messages.append("No escorts can attempt detection this phase")
            return current_detection_level, messages
        
        # Roll detection for each escort
        detection_successes = 0
        for escort, reason in detecting_escorts:
            roll = self.dice.roll_1d6(context=f"{escort.ship_type}_detection")
            success = roll >= threshold
            
            if success:
                detection_successes += 1
                messages.append(
                    f"  {escort.ship_type.capitalize()} ({reason}): "
                    f"rolled 1d6 [{roll}] - SUCCESS! (+1 DL)"
                )
            else:
                messages.append(
                    f"  {escort.ship_type.capitalize()} ({reason}): "
                    f"rolled 1d6 [{roll}] - failed (need {threshold}+)"
                )
        
        # Calculate new detection level
        new_detection_level = min(3, current_detection_level + detection_successes)
        
        if detection_successes > 0:
            dl_change = new_detection_level - current_detection_level
            print(f"[DL] Detection phase: {detection_successes} success(es), DL {current_detection_level} -> {new_detection_level}")
            messages.append(
                f"Detection Level increased by {dl_change}: "
                f"{current_detection_level} -> {new_detection_level}"
            )
        else:
            messages.append("No successful detections this phase")
        
        return new_detection_level, messages
