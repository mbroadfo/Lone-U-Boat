"""
Combat resolution for Lone U-Boat.

Resolves deck gun and torpedo attacks using JSON-defined hit tables and DiceRoller.

Rules from u_boat_ruleset_default.json -> FIRE DECK GUN and FIRE TORPS actions
"""

from typing import Tuple, List, Optional, TypedDict, Any, Dict
from .dice import DiceRoller
import re


class TorpedoAttackResult(TypedDict):
    """Result of a torpedo attack."""
    hits: int
    rolls: List[int]
    target: int
    description: str


class CombatResolver:
    """
    Resolve combat actions with hit tables from JSON.
    
    Uses DiceRoller for all combat rolls.
    """
    
    def __init__(self, dice_roller: DiceRoller, mission_rules: Optional[Any] = None):
        """
        Initialize combat resolver.
        
        Args:
            dice_roller: DiceRoller instance for combat rolls
            mission_rules: Optional mission rules for loading hit tables from JSON
        """
        self.dice = dice_roller
        self.mission_rules = mission_rules
        
        # Default hit tables (used if mission_rules not provided or parsing fails)
        self.deck_gun_hit_table: Dict[str, int] = {
            "range_1_2": 7,
            "range_3": 8
        }
        
        self.torpedo_hit_table: Dict[str, Dict[str, int]] = {
            "range_1_2": {"side": 3, "front_rear": 4},
            "range_3_4": {"side": 4, "front_rear": 5},
            "range_5_6": {"side": 5, "front_rear": 6},
            "range_7_9": {"side": 6, "front_rear": 6}
        }
        
        # Load from JSON if mission rules provided
        if mission_rules:
            self._load_combat_tables()
    
    def _parse_dice_requirement(self, requirement_str: str) -> int:
        """
        Parse dice requirement string to extract target number.
        
        Examples:
            "7+ on 2d6" -> 7
            "3+ on 1d6 per torpedo" -> 3
            "4+" -> 4
        
        Args:
            requirement_str: String like "7+ on 2d6"
            
        Returns:
            Target number needed to succeed
        """
        # Extract number before '+'
        match = re.search(r'(\d+)\+', requirement_str)
        if match:
            return int(match.group(1))
        return 0
    
    def _load_combat_tables(self) -> None:
        """Load combat hit tables from mission_rules JSON."""
        try:
            # Get action costs section
            action_costs = self.mission_rules.get_section_by_id("u_boat_action_costs")
            
            if not action_costs or "actions" not in action_costs:
                return
            
            # Find FIRE DECK GUN action
            for action_data in action_costs["actions"]:
                if action_data.get("action") == "FIRE DECK GUN":
                    to_hit = action_data.get("to_hit", {})
                    for range_key, requirement_str in to_hit.items():
                        target_num = self._parse_dice_requirement(requirement_str)
                        if target_num > 0:
                            self.deck_gun_hit_table[range_key] = target_num
                
                elif action_data.get("action") == "FIRE TORPS":
                    to_hit_table = action_data.get("to_hit_table", {})
                    for range_key, aspects in to_hit_table.items():
                        if range_key not in self.torpedo_hit_table:
                            self.torpedo_hit_table[range_key] = {}
                        
                        for aspect, requirement_str in aspects.items():
                            target_num = self._parse_dice_requirement(requirement_str)
                            if target_num > 0:
                                self.torpedo_hit_table[range_key][aspect] = target_num
        
        except Exception:
            # Keep defaults if parsing fails
            pass
    
    # ========== DECK GUN COMBAT ==========
    
    def resolve_deck_gun_attack(
        self,
        range_to_target: int
    ) -> Tuple[bool, int, str]:
        """
        Resolve deck gun attack with 2d6 roll.
        
        Rules from JSON:
        - Range 1-2: 7+ on 2d6
        - Range 3: 8+ on 2d6
        
        Args:
            range_to_target: Hex distance to target (1-3)
            
        Returns:
            (hit, roll_result, description)
            - hit: True if attack hits
            - roll_result: The 2d6 roll result
            - description: Formatted attack description
        """
        # Determine target number based on range
        if range_to_target <= 0:
            return False, 0, "Invalid range (must be 1-3)"
        elif range_to_target <= 2:
            target = self.deck_gun_hit_table["range_1_2"]
            range_desc = "1-2"
        elif range_to_target == 3:
            target = self.deck_gun_hit_table["range_3"]
            range_desc = "3"
        else:
            return False, 0, f"Out of range (max 3, target at {range_to_target})"
        
        # Roll 2d6
        roll = self.dice.roll_2d6()
        hit = roll >= target
        
        # Format description
        desc = f"Range {range_desc}: rolled {roll} (need {target}+) = {'HIT' if hit else 'MISS'}"
        
        return hit, roll, desc
    
    def roll_deck_gun_damage(self) -> Tuple[int, str]:
        """
        Roll damage for deck gun hit on Allied Ship Damage Chart.
        
        Returns:
            (damage_roll, description)
        """
        roll = self.dice.roll_1d6()
        return roll, f"Damage roll: {roll} on Allied Ship Damage Chart"
    
    # ========== TORPEDO COMBAT ==========
    
    def resolve_torpedo_attack(
        self,
        range_to_target: int,
        aspect: str,
        num_torpedoes: int = 1
    ) -> TorpedoAttackResult:
        """
        Resolve torpedo attack with 1d6 per torpedo.
        
        Rules from JSON:
        - Range and aspect determine target number on 1d6
        - Side aspect is easier to hit than front/rear
        - Each torpedo rolls separately
        
        Args:
            range_to_target: Hex distance to target (1-9)
            aspect: Target aspect ("side" or "front_rear")
            num_torpedoes: Number of torpedoes fired (1-3)
            
        Returns:
            Dict with:
            - hits: Number of hits
            - rolls: List of individual roll results
            - target: Target number needed
            - description: Formatted attack description
        """
        # Validate inputs
        if range_to_target <= 0 or range_to_target > 9:
            return {
                "hits": 0,
                "rolls": [],
                "target": 0,
                "description": f"Invalid range: {range_to_target} (must be 1-9)"
            }
        
        if aspect not in ["side", "front_rear"]:
            return {
                "hits": 0,
                "rolls": [],
                "target": 0,
                "description": f"Invalid aspect: {aspect} (must be 'side' or 'front_rear')"
            }
        
        if num_torpedoes < 1 or num_torpedoes > 3:
            return {
                "hits": 0,
                "rolls": [],
                "target": 0,
                "description": f"Invalid torpedo count: {num_torpedoes} (must be 1-3)"
            }
        
        # Determine target number based on range
        if range_to_target <= 2:
            range_key = "range_1_2"
            range_desc = "1-2"
        elif range_to_target <= 4:
            range_key = "range_3_4"
            range_desc = "3-4"
        elif range_to_target <= 6:
            range_key = "range_5_6"
            range_desc = "5-6"
        else:  # 7-9
            range_key = "range_7_9"
            range_desc = "7-9"
        
        target = self.torpedo_hit_table[range_key][aspect]
        
        # Roll 1d6 for each torpedo
        rolls: List[int] = []
        hits = 0
        for _ in range(num_torpedoes):
            roll = self.dice.roll_1d6()
            rolls.append(roll)
            if roll >= target:
                hits += 1
        
        # Format description
        aspect_desc = "Side" if aspect == "side" else "Front/Rear"
        desc = f"Range {range_desc}, {aspect_desc}: {num_torpedoes} torpedo(es), need {target}+ on 1d6"
        desc += f"\nRolls: {rolls} = {hits} HIT(S)"
        
        return {
            "hits": hits,
            "rolls": rolls,
            "target": target,
            "description": desc
        }
    
    def roll_torpedo_damage(self, num_hits: int) -> List[Tuple[int, str]]:
        """
        Roll damage for each torpedo hit on Allied Ship Damage Chart.
        
        Args:
            num_hits: Number of torpedoes that hit
            
        Returns:
            List of (damage_roll, description) for each hit
        """
        damage_rolls: List[Tuple[int, str]] = []
        for i in range(num_hits):
            roll = self.dice.roll_1d6()
            desc = f"Hit {i+1} damage: {roll} on Allied Ship Damage Chart"
            damage_rolls.append((roll, desc))
        return damage_rolls
    
    # ========== INFO METHODS ==========
    
    def get_deck_gun_hit_chances(self) -> str:
        """
        Get formatted deck gun hit probability info.
        
        Returns:
            Formatted string with hit chances
        """
        # Probability calculations for 2d6
        # 7+ on 2d6 = 21/36 = 58.3%
        # 8+ on 2d6 = 15/36 = 41.7%
        
        return (
            "Deck Gun Hit Chances:\n"
            "  Range 1-2: Need 7+ on 2d6 (58.3% chance)\n"
            "  Range 3:   Need 8+ on 2d6 (41.7% chance)\n"
            "On Hit: Roll 1d6 on Allied Ship Damage Chart"
        )
    
    def get_torpedo_hit_chances(self) -> str:
        """
        Get formatted torpedo hit probability info.
        
        Returns:
            Formatted string with hit chances
        """
        lines = ["Torpedo Hit Chances (per torpedo on 1d6):"]
        
        for range_key, targets in self.torpedo_hit_table.items():
            range_desc = range_key.replace("range_", "Range ").replace("_", "-")
            side_target = targets["side"]
            fr_target = targets["front_rear"]
            
            side_pct = ((7 - side_target) / 6) * 100
            fr_pct = ((7 - fr_target) / 6) * 100
            
            lines.append(f"  {range_desc}:")
            lines.append(f"    Side: {side_target}+ ({side_pct:.1f}%)")
            lines.append(f"    Front/Rear: {fr_target}+ ({fr_pct:.1f}%)")
        
        lines.append("On Hit: Roll 1d6 on Allied Ship Damage Chart per hit")
        
        return "\n".join(lines)
    
    def get_combat_summary(
        self,
        attack_type: str,
        range_to_target: int,
        aspect: Optional[str] = None
    ) -> str:
        """
        Get summary of attack parameters.
        
        Args:
            attack_type: "deck_gun" or "torpedo"
            range_to_target: Distance to target
            aspect: Target aspect (for torpedoes)
            
        Returns:
            Formatted string with attack info
        """
        if attack_type == "deck_gun":
            if range_to_target <= 2:
                target = self.deck_gun_hit_table["range_1_2"]
                return f"Deck Gun at range {range_to_target}: Need {target}+ on 2d6"
            elif range_to_target == 3:
                target = self.deck_gun_hit_table["range_3"]
                return f"Deck Gun at range {range_to_target}: Need {target}+ on 2d6"
            else:
                return f"Deck Gun: Range {range_to_target} out of range (max 3)"
        
        elif attack_type == "torpedo":
            if range_to_target <= 2:
                range_key = "range_1_2"
            elif range_to_target <= 4:
                range_key = "range_3_4"
            elif range_to_target <= 6:
                range_key = "range_5_6"
            elif range_to_target <= 9:
                range_key = "range_7_9"
            else:
                return f"Torpedo: Range {range_to_target} out of range (max 9)"
            
            if aspect and aspect in ["side", "front_rear"]:
                target = self.torpedo_hit_table[range_key][aspect]
                aspect_name = "Side" if aspect == "side" else "Front/Rear"
                return f"Torpedo at range {range_to_target} ({aspect_name}): Need {target}+ on 1d6"
            else:
                side_t = self.torpedo_hit_table[range_key]["side"]
                fr_t = self.torpedo_hit_table[range_key]["front_rear"]
                return f"Torpedo at range {range_to_target}: Need {side_t}+ (side) or {fr_t}+ (front/rear) on 1d6"
        
        return "Unknown attack type"
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return "<CombatResolver: Deck Gun (2d6) + Torpedoes (1d6)>"
