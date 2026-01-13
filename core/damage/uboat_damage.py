"""
U-Boat damage resolution - U-Boat Damage Chart.

Handles damage to U-boat from depth charges, ramming, and other sources.
"""

from typing import Tuple, Optional, List
from dataclasses import dataclass
from ..models import UBoat
from ..dice import DiceRoller


@dataclass
class UBoatDamageResult:
    """Result of U-boat damage roll."""
    damage_type: str  # "critical", "general", "crew_casualty"
    roll: int
    effect: str
    description: str
    hull_damage_taken: int
    systems_damaged: List[str]
    crew_casualties: List[str]
    medic_saves: List[Tuple[str, bool]]  # (crew_member, saved)
    is_destroyed: bool
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"U-Boat Damage: {self.description}"


class UBoatDamageResolver:
    """
    Resolve damage to U-boat using damage charts.
    
    U-Boat Damage Chart (from rules):
    
    Critical Hit (roll 2d6):
      2-3: Hull Breach +2 (cannot repair)
      4-5: Hull Breach +1
      6-7: Random system damaged
      8-9: Random crew casualty (medic save 5+)
      10+: Lucky - no critical damage
    
    General Damage (roll 1d6):
      1: Hull +1
      2: Engine damaged
      3: Deck gun damaged
      4: Flak gun damaged
      5-6: Torpedo tube damaged (random)
    
    Crew Casualties:
      Roll 1d6 to select: 1=Engineer, 2=WO, 3=Medic, 4=Radio, 5-6=Reroll
      Medic save: 5+ on 1d6 (if Medic alive)
    """
    
    def __init__(self, dice: DiceRoller):
        """
        Initialize U-boat damage resolver.
        
        Args:
            dice: Dice roller for damage rolls
        """
        self.dice = dice
    
    def apply_critical_damage(self, u_boat: UBoat) -> UBoatDamageResult:
        """
        Apply critical hit damage to U-boat.
        
        Args:
            u_boat: U-boat taking damage
            
        Returns:
            UBoatDamageResult with damage effects
        """
        roll = self.dice.roll(2)
        hull_damage = 0
        systems_damaged: List[str] = []
        crew_casualties: List[str] = []
        medic_saves: List[Tuple[str, bool]] = []
        
        if roll <= 3:
            # Hull Breach +2
            hull_damage = 2
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
            effect = f"Hull Breach +2 (total: {u_boat.hull_damage})"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        elif roll <= 5:
            # Hull Breach +1
            hull_damage = 1
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
            effect = f"Hull Breach +1 (total: {u_boat.hull_damage})"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        elif roll <= 7:
            # Random system damaged
            system = self._random_system_damage(u_boat)
            systems_damaged.append(system)
            effect = f"{system} damaged"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        elif roll <= 9:
            # Random crew casualty
            casualty, saved, save_roll = self._random_crew_casualty(u_boat)
            if casualty:
                if not saved:
                    crew_casualties.append(casualty)
                medic_saves.append((casualty, saved))
                if saved:
                    effect = f"{casualty} wounded but saved by Medic! (Roll: {save_roll})"
                else:
                    effect = f"{casualty} KIA!"
                    if not u_boat.medic_alive:
                        effect += " (No medic available)"
            else:
                effect = "No crew available to casualty"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        else:  # roll >= 10
            # Lucky - no damage
            effect = "No critical damage (lucky!)"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        # Check if U-boat is destroyed
        is_destroyed = u_boat.hull_damage >= 4
        if is_destroyed:
            description += " - U-BOAT DESTROYED!"
        
        return UBoatDamageResult(
            damage_type="critical",
            roll=roll,
            effect=effect,
            description=description,
            hull_damage_taken=hull_damage,
            systems_damaged=systems_damaged,
            crew_casualties=crew_casualties,
            medic_saves=medic_saves,
            is_destroyed=is_destroyed
        )
    
    def apply_general_damage(self, u_boat: UBoat) -> UBoatDamageResult:
        """
        Apply general damage to U-boat.
        
        Args:
            u_boat: U-boat taking damage
            
        Returns:
            UBoatDamageResult with damage effects
        """
        roll = self.dice.roll(1)
        hull_damage = 0
        systems_damaged: List[str] = []
        
        if roll == 1:
            # Hull +1
            hull_damage = 1
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
            effect = f"Hull damage +1 (total: {u_boat.hull_damage})"
        
        elif roll == 2:
            # Engine damaged
            if not u_boat.engine_damaged:
                u_boat.engine_damaged = True
                systems_damaged.append("Engine")
                effect = "Engine damaged"
            else:
                effect = "Engine already damaged - no additional effect"
        
        elif roll == 3:
            # Deck gun damaged
            if not u_boat.deck_gun_damaged:
                u_boat.deck_gun_damaged = True
                systems_damaged.append("Deck Gun")
                effect = "Deck Gun damaged"
            else:
                effect = "Deck Gun already damaged - no additional effect"
        
        elif roll == 4:
            # Flak gun damaged
            if not u_boat.flak_gun_damaged:
                u_boat.flak_gun_damaged = True
                systems_damaged.append("Flak Gun")
                effect = "Flak Gun damaged"
            else:
                effect = "Flak Gun already damaged - no additional effect"
        
        else:  # roll >= 5
            # Random torpedo tube damaged
            tube = self._random_torpedo_tube_damage(u_boat)
            if tube is not None:
                systems_damaged.append(f"Torpedo Tube {tube + 1}")
                effect = f"Torpedo Tube {tube + 1} damaged"
            else:
                effect = "All torpedo tubes already damaged"
        
        description = f"General Damage! Roll {roll}: {effect}"
        
        # Check if U-boat is destroyed
        is_destroyed = u_boat.hull_damage >= 4
        if is_destroyed:
            description += " - U-BOAT DESTROYED!"
        
        return UBoatDamageResult(
            damage_type="general",
            roll=roll,
            effect=effect,
            description=description,
            hull_damage_taken=hull_damage,
            systems_damaged=systems_damaged,
            crew_casualties=[],
            medic_saves=[],
            is_destroyed=is_destroyed
        )
    
    def _random_system_damage(self, u_boat: UBoat) -> str:
        """
        Randomly damage a system.
        
        Args:
            u_boat: U-boat to damage
            
        Returns:
            Name of system damaged
        """
        # Pick a random system (1d6)
        roll = self.dice.roll(1)
        
        if roll == 1 and not u_boat.engine_damaged:
            u_boat.engine_damaged = True
            return "Engine"
        elif roll == 2 and not u_boat.deck_gun_damaged:
            u_boat.deck_gun_damaged = True
            return "Deck Gun"
        elif roll == 3 and not u_boat.flak_gun_damaged:
            u_boat.flak_gun_damaged = True
            return "Flak Gun"
        else:
            # Damage random torpedo tube
            tube = self._random_torpedo_tube_damage(u_boat)
            if tube is not None:
                return f"Torpedo Tube {tube + 1}"
            else:
                # All tubes damaged, try other systems
                if not u_boat.engine_damaged:
                    u_boat.engine_damaged = True
                    return "Engine"
                elif not u_boat.deck_gun_damaged:
                    u_boat.deck_gun_damaged = True
                    return "Deck Gun"
                else:
                    return "No undamaged systems"
    
    def _random_torpedo_tube_damage(self, u_boat: UBoat) -> Optional[int]:
        """
        Damage a random torpedo tube.
        
        Args:
            u_boat: U-boat to damage
            
        Returns:
            Index of tube damaged, or None if all damaged
        """
        # Find undamaged tubes
        undamaged: List[int] = [i for i, loaded in enumerate(u_boat.torpedo_tubes) if loaded]
        
        if not undamaged:
            return None
        
        # Pick random undamaged tube
        tube_index: int = self.dice.random_choice(undamaged)
        u_boat.torpedo_tubes[tube_index] = False  # Mark as damaged/unloaded
        return tube_index
    
    def _random_crew_casualty(self, u_boat: UBoat) -> Tuple[Optional[str], bool, Optional[int]]:
        """
        Apply random crew casualty with medic save.
        
        Args:
            u_boat: U-boat taking casualty
            
        Returns:
            (crew_member, saved_by_medic, save_roll)
        """
        # Roll for which crew member (reroll 5-6)
        while True:
            roll = self.dice.roll_1d6()
            if roll <= 4:
                break
        
        crew_members = {
            1: ("Engineer", "engineer_alive"),
            2: ("Weapons Officer", "weapons_officer_alive"),
            3: ("Medic", "medic_alive"),
            4: ("Radio Operator", "radio_operator_alive")
        }
        
        crew_name, crew_attr = crew_members[roll]
        
        # Check if crew member is already dead
        if not getattr(u_boat, crew_attr):
            return None, False, None
        
        # Medic save (5+ on 1d6) - if medic is alive
        saved = False
        save_roll = None
        
        if u_boat.medic_alive and crew_name != "Medic":
            save_roll = self.dice.roll_1d6()
            saved = save_roll >= 5
        
        # Apply casualty if not saved
        if not saved:
            setattr(u_boat, crew_attr, False)
        
        return crew_name, saved, save_roll
    
    def check_destruction(self, u_boat: UBoat) -> Tuple[bool, str]:
        """
        Check if U-boat is destroyed.
        
        Args:
            u_boat: U-boat to check
            
        Returns:
            (is_destroyed, reason)
        """
        if u_boat.hull_damage >= 4:
            return True, f"Hull damage critical ({u_boat.hull_damage}/4)"
        
        return False, ""
    
    def apply_escort_attack_damage(
        self,
        u_boat: UBoat,
        attack_type: str = "depth_charge",
        ship_type: str = "corvette"
    ) -> UBoatDamageResult:
        """
        Apply damage from escort attack using exact RULES.md damage chart.
        
        U-Boat Damage Chart (Depth Charge, Ship Gun Fire, B24):
        1   Critical Hit! Roll d6:
            1 U-Boat Destroyed
            2 +2 Hull Damage
            3-4 Torp tubes 3d6
            5-6 Damage x 2 (roll twice at 3-4 below)
        
        2   Hull Damage: +1 Hull Damage
        
        3-4 Damage: Roll 1d6:
            1 +1 Hull Damage
            2 Flak gun
            3 Torp tubes 2d6
            4-5 Engine
            6 Deck gun
        
        5-6 Crew KIA: Roll d6 for crew member (medic save 5+)
        
        Args:
            u_boat: U-boat taking damage
            attack_type: "depth_charge", "gunfire", or "b24"
            ship_type: "corvette" or "destroyer" (destroyer rolls 2d6, takes lowest)
            
        Returns:
            UBoatDamageResult with damage effects
        """
        # Roll on damage chart
        if attack_type == "gunfire":
            # Gunfire is automatic critical hit (roll 1 on chart)
            chart_roll = 1
        elif ship_type == "destroyer" and attack_type == "depth_charge":
            # Destroyer rolls 2d6, takes lowest
            roll1 = self.dice.roll_1d6()
            roll2 = self.dice.roll_1d6()
            chart_roll = min(roll1, roll2)
        else:
            # Corvette or other: roll 1d6
            chart_roll = self.dice.roll_1d6()
        
        hull_damage = 0
        systems_damaged: List[str] = []
        crew_casualties: List[str] = []
        medic_saves: List[Tuple[str, bool]] = []
        is_destroyed = False
        
        # Apply damage based on chart roll
        if chart_roll == 1:
            # Critical Hit!
            crit_roll = self.dice.roll_1d6()
            
            if crit_roll == 1:
                # U-Boat Destroyed
                is_destroyed = True
                u_boat.hull_damage = 4
                effect = "U-BOAT DESTROYED!"
                description = f"Critical Hit! Roll {crit_roll}: {effect}"
            
            elif crit_roll == 2:
                # +2 Hull Damage
                hull_damage = 2
                u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
                effect = f"+2 Hull Damage (total: {u_boat.hull_damage})"
                description = f"Critical Hit! Roll {crit_roll}: {effect}"
                if u_boat.hull_damage >= 4:
                    is_destroyed = True
                    description += " - U-BOAT DESTROYED!"
            
            elif crit_roll in [3, 4]:
                # Torp tubes 3d6
                damaged_tubes = self._damage_torpedo_tubes(u_boat, 3)
                systems_damaged.extend([f"Torpedo Tube {t+1}" for t in damaged_tubes])
                effect = f"Torpedo tubes damaged: {[t+1 for t in damaged_tubes]}"
                description = f"Critical Hit! Roll {crit_roll}: {effect}"
            
            else:  # crit_roll in [5, 6]
                # Damage x2 (roll twice on 3-4 below)
                result1 = self._apply_general_damage_roll(u_boat)
                result2 = self._apply_general_damage_roll(u_boat)
                systems_damaged.extend(result1[0])
                systems_damaged.extend(result2[0])
                hull_damage = result1[1] + result2[1]
                effect = f"Double damage: {result1[2]} AND {result2[2]}"
                description = f"Critical Hit! Roll {crit_roll}: {effect}"
                if u_boat.hull_damage >= 4:
                    is_destroyed = True
                    description += " - U-BOAT DESTROYED!"
        
        elif chart_roll == 2:
            # Hull Damage +1
            hull_damage = 1
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
            effect = f"+1 Hull Damage (total: {u_boat.hull_damage})"
            description = f"Hull Damage! {effect}"
            if u_boat.hull_damage >= 4:
                is_destroyed = True
                description += " - U-BOAT DESTROYED!"
        
        elif chart_roll in [3, 4]:
            # General Damage - roll 1d6
            systems, hull, effect = self._apply_general_damage_roll(u_boat)
            systems_damaged.extend(systems)
            hull_damage = hull
            description = f"Damage! {effect}"
            if u_boat.hull_damage >= 4:
                is_destroyed = True
                description += " - U-BOAT DESTROYED!"
        
        else:  # chart_roll in [5, 6]
            # Crew KIA
            crew_result = self._random_crew_casualty(u_boat)
            if crew_result[0] is not None:
                crew_name, saved, save_roll = crew_result
                if saved:
                    medic_saves.append((crew_name, True))
                    effect = f"{crew_name} targeted but saved by Medic (rolled {save_roll})"
                else:
                    crew_casualties.append(crew_name)
                    effect = f"{crew_name} KIA"
                    if save_roll is not None:
                        effect += f" (Medic save failed: {save_roll})"
            else:
                effect = "Crew member already KIA - no effect"
            description = f"Crew Casualty! {effect}"
        
        return UBoatDamageResult(
            damage_type="escort_attack",
            roll=chart_roll,
            effect=effect,
            description=description,
            hull_damage_taken=hull_damage,
            systems_damaged=systems_damaged,
            crew_casualties=crew_casualties,
            medic_saves=medic_saves,
            is_destroyed=is_destroyed
        )
    
    def _apply_general_damage_roll(self, u_boat: UBoat) -> Tuple[List[str], int, str]:
        """
        Apply general damage (3-4 on main chart).
        
        Returns:
            (systems_damaged, hull_damage, effect_description)
        """
        roll = self.dice.roll_1d6()
        systems: List[str] = []
        hull = 0
        
        if roll == 1:
            # +1 Hull Damage
            hull = 1
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull)
            effect = f"+1 Hull Damage (total: {u_boat.hull_damage})"
        
        elif roll == 2:
            # Flak gun
            if not u_boat.flak_gun_damaged:
                u_boat.flak_gun_damaged = True
                systems.append("Flak Gun")
                effect = "Flak Gun damaged"
            else:
                effect = "Flak Gun already damaged"
        
        elif roll == 3:
            # Torp tubes 2d6
            damaged_tubes = self._damage_torpedo_tubes(u_boat, 2)
            systems.extend([f"Torpedo Tube {t+1}" for t in damaged_tubes])
            effect = f"Torpedo tubes damaged: {[t+1 for t in damaged_tubes]}" if damaged_tubes else "No tubes damaged"
        
        elif roll in [4, 5]:
            # Engine
            if not u_boat.engine_damaged:
                u_boat.engine_damaged = True
                systems.append("Engine")
                effect = "Engine damaged"
            else:
                effect = "Engine already damaged"
        
        else:  # roll == 6
            # Deck gun
            if not u_boat.deck_gun_damaged:
                u_boat.deck_gun_damaged = True
                systems.append("Deck Gun")
                effect = "Deck Gun damaged"
            else:
                effect = "Deck Gun already damaged"
        
        return (systems, hull, effect)
    
    def _damage_torpedo_tubes(self, u_boat: UBoat, num_dice: int) -> List[int]:
        """
        Damage torpedo tubes by rolling dice.
        
        Args:
            u_boat: U-boat to damage
            num_dice: Number of d6 to roll
            
        Returns:
            List of tube indices that were damaged
        """
        damaged = []
        for _ in range(num_dice):
            roll = self.dice.roll_1d6()
            if roll <= 5:  # Valid tube number (1-5)
                tube_index = roll - 1
                # Only damage if not already damaged
                if u_boat.torpedo_tubes[tube_index]:
                    u_boat.torpedo_tubes[tube_index] = False
                    damaged.append(tube_index)
        return damaged
