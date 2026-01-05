"""
Ship damage resolution - Allied Ship Damage Chart.

Handles damage to merchant and escort ships from deck gun and torpedoes.
"""

from typing import Tuple
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
    
    Allied Ship Damage Chart (from rules):
    - Merchant Ships (roll 1d6):
      1-2: No Effect (if already Damaged = Sunk)
      3-4: Damaged (if already Damaged = Catastrophic = Sunk)
      5-6: Catastrophic (immediate Sunk)
    
    - Escort Ships (Destroyer, Corvette):
      Deck Gun: -2 to roll (harder to damage)
      Torpedo: Normal roll
      Same effects as merchant
    """
    
    def __init__(self, dice: DiceRoller):
        """
        Initialize ship damage resolver.
        
        Args:
            dice: Dice roller for damage rolls
        """
        self.dice = dice
    
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
                modified_roll = max(1, base_roll - 2)  # -2 modifier, min 1
            else:
                modified_roll = base_roll
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
        
        if roll <= 2:
            # No effect (or Sunk if already damaged)
            if already_damaged:
                return "sunk", f"{weapon_name} hit already-damaged {ship_type} - SUNK! (Roll: {roll})"
            else:
                return "no_effect", f"{weapon_name} hit {ship_type} - No effect (Roll: {roll})"
        
        elif roll <= 4:
            # Damaged (or Catastrophic = Sunk if already damaged)
            if already_damaged:
                return "sunk", f"{weapon_name} hit already-damaged {ship_type} - Catastrophic damage - SUNK! (Roll: {roll})"
            else:
                return "damaged", f"{weapon_name} hit {ship_type} - DAMAGED (Roll: {roll})"
        
        else:  # roll >= 5
            # Catastrophic - immediate Sunk
            return "catastrophic", f"{weapon_name} hit {ship_type} - Catastrophic damage - SUNK! (Roll: {roll})"
    
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
