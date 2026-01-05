"""
Dice rolling system for Lone U-Boat.

Provides general-purpose dice rolling with logging and deterministic testing support.
Used for: AP rolls, combat resolution, damage charts, and all random events.
"""

import random
from typing import List, Tuple, Optional, TypeVar
from dataclasses import dataclass
from datetime import datetime

T = TypeVar('T')


@dataclass
class RollRecord:
    """Record of a single dice roll for logging/history."""
    timestamp: str
    roll_type: str
    dice: str  # e.g., "3d6", "2d6", "1d6"
    rolls: List[int]
    result: int
    context: str = ""


class DiceRoller:
    """
    General-purpose dice roller with logging and deterministic testing.
    
    Supports:
    - Standard rolls (1d6, 2d6, 3d6, etc.)
    - Take highest/lowest die
    - Roll history for replay/debugging
    - Seeded RNG for deterministic testing
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize dice roller.
        
        Args:
            seed: Optional seed for deterministic rolls (testing only)
        """
        self.rng = random.Random(seed)
        self.roll_history: List[RollRecord] = []
        self.enable_logging = True
    
    def roll_dice(
        self,
        count: int,
        sides: int = 6,
        context: str = ""
    ) -> Tuple[List[int], int]:
        """
        Roll multiple dice and return all results.
        
        Args:
            count: Number of dice to roll
            sides: Number of sides per die (default 6)
            context: Description of why rolling (for logs)
            
        Returns:
            (individual_rolls, sum_of_rolls)
        """
        rolls = [self.rng.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="standard",
                dice=f"{count}d{sides}",
                rolls=rolls,
                result=total,
                context=context
            )
        
        return rolls, total
    
    def roll_1d6(self, context: str = "") -> int:
        """
        Roll a single d6.
        
        Args:
            context: Description of roll
            
        Returns:
            Result (1-6)
        """
        roll = self.rng.randint(1, 6)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="1d6",
                dice="1d6",
                rolls=[roll],
                result=roll,
                context=context
            )
        
        return roll
    
    def roll_2d6(self, context: str = "") -> int:
        """
        Roll 2d6 and return sum.
        
        Args:
            context: Description of roll
            
        Returns:
            Sum (2-12)
        """
        rolls = [self.rng.randint(1, 6), self.rng.randint(1, 6)]
        total = sum(rolls)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="2d6",
                dice="2d6",
                rolls=rolls,
                result=total,
                context=context
            )
        
        return total
    
    def roll_3d6(self, context: str = "") -> Tuple[List[int], int]:
        """
        Roll 3d6 and return all rolls plus sum.
        
        Args:
            context: Description of roll
            
        Returns:
            (individual_rolls, sum)
        """
        rolls = [self.rng.randint(1, 6) for _ in range(3)]
        total = sum(rolls)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="3d6",
                dice="3d6",
                rolls=rolls,
                result=total,
                context=context
            )
        
        return rolls, total
    
    def roll_highest(
        self,
        count: int,
        sides: int = 6,
        context: str = ""
    ) -> Tuple[int, List[int]]:
        """
        Roll multiple dice and take the highest.
        
        Used for: Action Point rolling
        
        Args:
            count: Number of dice to roll
            sides: Number of sides per die
            context: Description of roll
            
        Returns:
            (highest_die, all_rolls)
        """
        rolls = [self.rng.randint(1, sides) for _ in range(count)]
        highest = max(rolls)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="highest",
                dice=f"{count}d{sides} (take highest)",
                rolls=rolls,
                result=highest,
                context=context
            )
        
        return highest, rolls
    
    def roll_lowest(
        self,
        count: int,
        sides: int = 6,
        context: str = ""
    ) -> Tuple[int, List[int]]:
        """
        Roll multiple dice and take the lowest.
        
        Used for: Destroyer depth charges (2d6 take lowest)
        
        Args:
            count: Number of dice to roll
            sides: Number of sides per die
            context: Description of roll
            
        Returns:
            (lowest_die, all_rolls)
        """
        rolls = [self.rng.randint(1, sides) for _ in range(count)]
        lowest = min(rolls)
        
        if self.enable_logging:
            self._log_roll(
                roll_type="lowest",
                dice=f"{count}d{sides} (take lowest)",
                rolls=rolls,
                result=lowest,
                context=context
            )
        
        return lowest, rolls
    
    def _log_roll(
        self,
        roll_type: str,
        dice: str,
        rolls: List[int],
        result: int,
        context: str
    ):
        """Internal: Log a roll to history."""
        record = RollRecord(
            timestamp=datetime.now().isoformat(),
            roll_type=roll_type,
            dice=dice,
            rolls=rolls,
            result=result,
            context=context
        )
        self.roll_history.append(record)
    
    def get_roll_history(self, last_n: Optional[int] = None) -> List[RollRecord]:
        """
        Get roll history.
        
        Args:
            last_n: Optional limit to last N rolls
            
        Returns:
            List of RollRecord objects
        """
        if last_n:
            return self.roll_history[-last_n:]
        return self.roll_history.copy()
    
    def clear_history(self):
        """Clear roll history (e.g., at start of new turn)."""
        self.roll_history.clear()
    
    def get_history_summary(self, last_n: Optional[int] = None) -> List[str]:
        """
        Get formatted roll history for display.
        
        Args:
            last_n: Optional limit to last N rolls
            
        Returns:
            List of formatted strings
        """
        history = self.get_roll_history(last_n)
        summary: List[str] = []
        
        for record in history:
            rolls_str = ", ".join(str(r) for r in record.rolls)
            line = f"{record.dice}: [{rolls_str}] = {record.result}"
            if record.context:
                line += f" ({record.context})"
            summary.append(line)
        
        return summary
    
    def set_logging(self, enabled: bool):
        """Enable or disable roll logging."""
        self.enable_logging = enabled
    
    def roll(self, num_dice: int) -> int:
        """
        Convenience method for rolling dice and returning sum.
        Equivalent to roll_dice() but simpler for common usage.
        
        Args:
            num_dice: Number of d6 to roll
            
        Returns:
            Sum of all dice (or single die value for 1d6)
        """
        if num_dice == 1:
            return self.roll_1d6()
        elif num_dice == 2:
            return self.roll_2d6()
        else:
            _, total = self.roll_dice(num_dice, 6)
            return total
    
    def set_seed(self, seed: int):
        """
        Set new random seed for deterministic testing.
        
        Args:
            seed: New seed value
        """
        self.rng.seed(seed)
    
    def random_choice(self, choices: List[T]) -> T:
        """
        Pick a random element from a list.
        
        Args:
            choices: List to choose from
            
        Returns:
            Random element from list
        """
        return self.rng.choice(choices)
