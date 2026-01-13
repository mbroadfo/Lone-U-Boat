"""
Ship damage resolution - Allied Ship Damage Chart.

Handles damage to merchant and escort ships from deck gun and torpedoes.
"""

from typing import Tuple, Optional, Any, Dict
from dataclasses import dataclass
from ..models import Ship
from ..dice import DiceRoller


@dataclass
class ShipDamageResult:
    """Result of ship damage roll."""
    ship: Ship
    weapon_type: str  # "deck_gun" or "torpedo"
    roll: int
    effect: str  # "no_effect", "damaged", "catastrophic", "sunk"
    description: str
    was_already_damaged: bool
    is_now_sunk: bool
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.ship.ship_type.title()}: {self.description}"


class ShipDamageResolver:
    """
    Resolve damage to Allied ships using damage charts.
    
    Allied Ship Damage Chart (from damage_tables.json):
    - Merchant Ships (roll 1d6):
      1-2: No Effect (if already Damaged = Sunk)
      3-4: Damaged (if already Damaged = Catastrophic = Sunk)
      5-6: Catastrophic (immediate Sunk)
    
    - Escort Ships (Destroyer, Corvette):
      Deck Gun: -2 to roll (harder to damage)
      Torpedo: Normal roll
      Same effects as merchant
    """
    
    def __init__(self, dice: DiceRoller, mission_rules: Optional[Any] = None):
        """
        Initialize ship damage resolver.
        
        Args:
            dice: Dice roller for damage rolls
            mission_rules: Optional mission rules for loading damage tables from JSON
        """
        self.dice = dice
        self.mission_rules = mission_rules
        
        # Default damage table (used if mission_rules not provided or parsing fails)
        self.escort_deck_gun_modifier: int = -2
        self.escort_torpedo_modifier: int = 0
        self.damage_table: Dict[str, Dict[str, Any]] = {
            "1-2": {"roll_range": [1, 2], "effect": "no_effect", "if_damaged": "sunk"},
            "3-4": {"roll_range": [3, 4], "effect": "damaged", "if_damaged": "sunk"},
            "5-6": {"roll_range": [5, 6], "effect": "catastrophic", "if_damaged": "sunk"}
        }
        
        # Load from JSON if mission rules provided
        if mission_rules:
            self._load_damage_tables()
        
        # Load from JSON if mission rules provided
        if mission_rules:
            self._load_damage_tables()
    
    def _load_damage_tables(self) -> None:
        """Load ship damage tables from mission_rules JSON."""
        try:
            # Get allied ship damage section
            ship_damage = self.mission_rules.get_section_by_id("allied_ship_damage")
            
            if not ship_damage:
                return
            
            # Load modifiers
            if "modifiers" in ship_damage:
                modifiers = ship_damage["modifiers"]
                if "escort_vs_deck_gun" in modifiers:
                    self.escort_deck_gun_modifier = modifiers["escort_vs_deck_gun"].get("modifier", -2)
                if "escort_vs_torpedo" in modifiers:
                    self.escort_torpedo_modifier = modifiers["escort_vs_torpedo"].get("modifier", 0)
            
            # Load damage table
            if "damage_table" in ship_damage:
                self.damage_table = ship_damage["damage_table"]
        
        except Exception:
            # Keep defaults if parsing fails
            pass
    
    def apply_damage(self, ship: Ship, weapon_type: str) -> ShipDamageResult:
        """
        Apply damage to a ship and return result.
        
        Args:
            ship: Ship taking damage
            weapon_type: "deck_gun" or "torpedo"
            
        Returns:
            ShipDamageResult with damage effects
        """
        was_damaged = ship.damaged
        
        # Roll damage
        base_roll = self.dice.roll(1)
        
        # Apply modifiers
        if ship.ship_type in ["destroyer", "corvette", "escort"]:
            # Escorts are tougher against deck guns
            if weapon_type == "deck_gun":
                modified_roll = max(1, base_roll + self.escort_deck_gun_modifier)  # modifier from JSON (default -2), min 1
            else:
                modified_roll = max(1, base_roll + self.escort_torpedo_modifier)  # modifier from JSON (default 0)
        else:
            # Merchant ships - no modifier
            modified_roll = base_roll
        
        # Determine effect
        effect, description = self._resolve_damage_effect(
            modified_roll, 
            was_damaged,
            ship.ship_type,
            weapon_type
        )
        
        # Apply effect to ship
        is_sunk = False
        if effect == "damaged":
            ship.damaged = True
        elif effect in ["catastrophic", "sunk"]:
            ship.damaged = True
            is_sunk = True
        
        return ShipDamageResult(
            ship=ship,
            weapon_type=weapon_type,
            roll=modified_roll,
            effect=effect,
            description=description,
            was_already_damaged=was_damaged,
            is_now_sunk=is_sunk
        )
    
    def _resolve_damage_effect(
        self, 
        roll: int, 
        already_damaged: bool,
        ship_type: str,
        weapon_type: str
    ) -> Tuple[str, str]:
        """
        Resolve damage effect from roll.
        
        Args:
            roll: Modified damage roll (1-6)
            already_damaged: Whether ship was already damaged
            ship_type: Type of ship (for description)
            weapon_type: Weapon type (for description)
            
        Returns:
            (effect, description)
        """
        weapon_name = "Deck gun" if weapon_type == "deck_gun" else "Torpedo"
        
        # Find matching entry in damage table
        for key, entry in self.damage_table.items():
            roll_range = entry.get("roll_range", [])
            if len(roll_range) == 2 and roll_range[0] <= roll <= roll_range[1]:
                # Found matching range
                if already_damaged:
                    # Use if_already_damaged effect
                    if_damaged = entry.get("if_already_damaged", {})
                    if isinstance(if_damaged, dict):
                        effect = if_damaged.get("effect", "sunk")
                        desc_suffix = if_damaged.get("description", "Already Damaged → SUNK!")
                    else:
                        # Simple string format (backward compatible)
                        effect = if_damaged if isinstance(if_damaged, str) else "sunk"
                        desc_suffix = "Already Damaged → SUNK!"
                    return effect, f"{weapon_name} hit already-damaged {ship_type} - {desc_suffix} (Roll: {roll})"
                else:
                    # Use normal effect
                    effect = entry.get("effect", "no_effect")
                    desc_text = entry.get("description", effect.replace("_", " ").title())
                    if effect == "catastrophic":
                        return effect, f"{weapon_name} hit {ship_type} - {desc_text} (Roll: {roll})"
                    elif effect == "damaged":
                        return effect, f"{weapon_name} hit {ship_type} - {desc_text} (Roll: {roll})"
                    else:
                        return effect, f"{weapon_name} hit {ship_type} - {desc_text} (Roll: {roll})"
        
        # Fallback if no match found (shouldn't happen with valid tables)
        if already_damaged:
            return "sunk", f"{weapon_name} hit already-damaged {ship_type} - SUNK! (Roll: {roll})"
        return "no_effect", f"{weapon_name} hit {ship_type} - No effect (Roll: {roll})"
    
    def check_if_sunk(self, ship: Ship) -> bool:
        """
        Check if a ship is sunk (for removing from game).
        
        Args:
            ship: Ship to check
            
        Returns:
            True if ship should be removed from game
        """
        # In this implementation, we track sinking via the damage result
        # This is a helper for game state management
        return ship.damaged and hasattr(ship, '_is_sunk')
