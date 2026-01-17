"""
U-Boat damage resolution - U-Boat Damage Chart.

Handles damage to U-boat from depth charges, ramming, and other sources.
"""

from typing import Tuple, Optional, List, Any, Dict
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
    
    U-Boat Damage Chart (from damage_tables.json):
    
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
    
    def __init__(self, dice: DiceRoller, mission_rules: Optional[Any] = None):
        """
        Initialize U-boat damage resolver.
        
        Args:
            dice: Dice roller for damage rolls
            mission_rules: Optional mission rules for loading damage tables from JSON
        """
        self.dice = dice
        self.mission_rules = mission_rules
        
        # Default damage tables (used if mission_rules not provided or parsing fails)
        self.critical_damage_table: Dict[str, Dict[str, Any]] = {
            "2-3": {"roll_range": [2, 3], "type": "hull_breach", "hull_damage": 2, "repairable": False},
            "4-5": {"roll_range": [4, 5], "type": "hull_breach", "hull_damage": 1, "repairable": True},
            "6-7": {"roll_range": [6, 7], "type": "system_damage", "effect": "random_system"},
            "8-9": {"roll_range": [8, 9], "type": "crew_casualty", "effect": "random_crew"},
            "10-12": {"roll_range": [10, 12], "type": "no_damage"}
        }
        
        self.general_damage_table: Dict[int, Dict[str, Any]] = {
            1: {"type": "hull_damage", "hull_damage": 1},
            2: {"type": "system_damage", "system": "engine"},
            3: {"type": "system_damage", "system": "deck_gun"},
            4: {"type": "system_damage", "system": "flak_gun"},
            5: {"type": "system_damage", "system": "random_torpedo_tube"},
            6: {"type": "system_damage", "system": "random_torpedo_tube"}
        }
        
        self.crew_selection_table: Dict[int, str] = {
            1: "engineer",
            2: "weapons_officer",
            3: "medic",
            4: "radio_operator"
        }
        
        self.medic_save_threshold: int = 5
        self.max_hull_damage: int = 4
        
        # Load from JSON if mission rules provided
        if mission_rules:
            self._load_damage_tables()
        # Load from JSON if mission rules provided
        if mission_rules:
            self._load_damage_tables()
    
    def _load_damage_tables(self) -> None:
        """Load U-Boat damage tables from mission_rules JSON."""
        if self.mission_rules is None:
            return
        
        try:
            # Load critical damage table
            critical_damage = self.mission_rules.get_section_by_id("uboat_critical_damage")
            if critical_damage and "damage_table" in critical_damage:
                self.critical_damage_table = critical_damage["damage_table"]
            
            # Load general damage table
            general_damage = self.mission_rules.get_section_by_id("uboat_general_damage")
            if general_damage and "damage_table" in general_damage:
                # Convert string keys to integers for general damage
                new_table = {}
                for _key, value in general_damage["damage_table"].items():
                    if "roll_range" in value:
                        # Handle ranges like "5-6"
                        for roll_val in range(value["roll_range"][0], value["roll_range"][1] + 1):
                            new_table[roll_val] = value
                    elif "roll" in value:
                        new_table[value["roll"]] = value
                if new_table:
                    self.general_damage_table = new_table
            
            # Load crew casualties
            crew_casualties = self.mission_rules.get_section_by_id("uboat_crew_casualties")
            if crew_casualties:
                if "selection_table" in crew_casualties:
                    new_crew_table = {}
                    for _key, value in crew_casualties["selection_table"].items():
                        if "roll" in value and "crew_member" in value:
                            new_crew_table[value["roll"]] = value["crew_member"]
                    if new_crew_table:
                        self.crew_selection_table = new_crew_table
                
                if "medic_save" in crew_casualties:
                    self.medic_save_threshold = crew_casualties["medic_save"].get("threshold", 5)
            
            # Load destruction thresholds
            destruction = self.mission_rules.get_section_by_id("destruction_thresholds")
            if destruction and "uboat_hull_damage" in destruction:
                self.max_hull_damage = destruction["uboat_hull_damage"].get("max_hull_damage", 4)
        
        except Exception:
            # Keep defaults if parsing fails
            pass
    
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
        
        # Find matching entry in damage table
        for _key, entry in self.critical_damage_table.items():
            roll_range = entry.get("roll_range", [])
            if len(roll_range) == 2 and roll_range[0] <= roll <= roll_range[1]:
                damage_type = entry.get("type", "no_damage")
                
                if damage_type == "hull_breach":
                    hull_damage = entry.get("hull_damage", 0)
                    u_boat.hull_damage = min(self.max_hull_damage, u_boat.hull_damage + hull_damage)
                    effect = f"Hull Breach +{hull_damage} (total: {u_boat.hull_damage})"
                    description = f"Critical Hit! Roll {roll}: {effect}"
                
                elif damage_type == "system_damage":
                    system = self._random_system_damage(u_boat)
                    systems_damaged.append(system)
                    effect = f"{system} damaged"
                    description = f"Critical Hit! Roll {roll}: {effect}"
                
                elif damage_type == "crew_casualty":
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
                
                else:  # no_damage
                    effect = "No critical damage (lucky!)"
                    description = f"Critical Hit! Roll {roll}: {effect}"
                
                break
        else:
            # Fallback if no match found (shouldn't happen with valid tables)
            effect = "Unknown damage effect"
            description = f"Critical Hit! Roll {roll}: {effect}"
        
        # Check if U-boat is destroyed
        is_destroyed = u_boat.hull_damage >= self.max_hull_damage
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
        
        # Look up damage effect in table
        entry = self.general_damage_table.get(roll, {})
        damage_type = entry.get("type", "hull_damage")
        
        if damage_type == "hull_damage":
            hull_damage = entry.get("hull_damage", 1)
            u_boat.hull_damage = min(self.max_hull_damage, u_boat.hull_damage + hull_damage)
            effect = f"Hull damage +{hull_damage} (total: {u_boat.hull_damage})"
        
        elif damage_type == "system_damage":
            system_name = entry.get("system", "")
            
            if system_name == "engine":
                if not u_boat.engine_damaged:
                    u_boat.engine_damaged = True
                    systems_damaged.append("Engine")
                    effect = "Engine damaged"
                else:
                    effect = "Engine already damaged - no additional effect"
            
            elif system_name == "deck_gun":
                if not u_boat.deck_gun_damaged:
                    u_boat.deck_gun_damaged = True
                    systems_damaged.append("Deck Gun")
                    effect = "Deck Gun damaged"
                else:
                    effect = "Deck Gun already damaged - no additional effect"
            
            elif system_name == "flak_gun":
                if not u_boat.flak_gun_damaged:
                    u_boat.flak_gun_damaged = True
                    systems_damaged.append("Flak Gun")
                    effect = "Flak Gun damaged"
                else:
                    effect = "Flak Gun already damaged - no additional effect"
            
            elif system_name == "random_torpedo_tube":
                tube = self._random_torpedo_tube_damage(u_boat)
                if tube is not None:
                    systems_damaged.append(f"Torpedo Tube {tube + 1}")
                    effect = f"Torpedo Tube {tube + 1} damaged"
                else:
                    effect = "All torpedo tubes already damaged"
            else:
                effect = "Unknown system damage"
        else:
            effect = "Unknown damage type"
        
        description = f"General Damage! Roll {roll}: {effect}"
        
        # Check if U-boat is destroyed
        is_destroyed = u_boat.hull_damage >= self.max_hull_damage
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
        # Roll for which crew member (reroll 5-6 if in table)
        max_attempts = 10  # Prevent infinite loop
        roll = None
        for _ in range(max_attempts):
            roll = self.dice.roll_1d6()
            if roll in self.crew_selection_table:
                break
        
        if roll is None or roll not in self.crew_selection_table:
            return None, False, None
        
        # Map crew member names to U-boat attributes
        crew_attr_map = {
            "engineer": ("Engineer", "engineer_alive"),
            "weapons_officer": ("Weapons Officer", "weapons_officer_alive"),
            "medic": ("Medic", "medic_alive"),
            "radio_operator": ("Sonar Operator", "sonar_operator_alive"),  # JSON uses radio_operator, map to sonar_operator
            "sonar_operator": ("Sonar Operator", "sonar_operator_alive"),
            "captain": ("Captain", "captain_alive"),
            "lookout": ("Lookout", "lookout_alive")
        }
        
        crew_member_key = self.crew_selection_table[roll]
        if crew_member_key not in crew_attr_map:
            return None, False, None
        
        crew_name, crew_attr = crew_attr_map[crew_member_key]
        
        # Check if crew member is already dead
        if not getattr(u_boat, crew_attr):
            return None, False, None
        
        # Medic save (threshold from JSON) - if medic is alive
        saved = False
        save_roll = None
        
        if u_boat.medic_alive and crew_name != "Medic":
            save_roll = self.dice.roll_1d6()
            saved = save_roll >= self.medic_save_threshold
        
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
        if u_boat.hull_damage >= self.max_hull_damage:
            return True, f"Hull damage critical ({u_boat.hull_damage}/{self.max_hull_damage})"
        
        return False, ""
    
    def apply_escort_attack_damage(
        self,
        u_boat: UBoat,
        attack_type: str = "depth_charge",
        ship_type: str = "corvette",
        ships: Optional[List[Any]] = None
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
            print(f"[DAMAGE] Gunfire attack: automatic critical hit (chart roll = 1)")
        elif ship_type == "destroyer" and attack_type == "depth_charge":
            # Destroyer rolls 2d6, takes lowest
            roll1 = self.dice.roll_1d6()
            roll2 = self.dice.roll_1d6()
            chart_roll = min(roll1, roll2)
            print(f"[DAMAGE] Destroyer depth charge: rolled {roll1}, {roll2} -> chart roll = {chart_roll}")
        else:
            # Corvette or other: roll 1d6
            chart_roll = self.dice.roll_1d6()
            ship_name = ship_type.capitalize() if ship_type else "B24"
            print(f"[DAMAGE] {ship_name} {attack_type}: chart roll = {chart_roll}")
        
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
            old_hull = u_boat.hull_damage
            u_boat.hull_damage = min(4, u_boat.hull_damage + hull_damage)
            print(f"[DAMAGE] Hull damage: {old_hull} -> {u_boat.hull_damage}")
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
                    if crew_name is not None:
                        crew_casualties.append(crew_name)
                    effect = f"{crew_name} KIA"
                    if save_roll is not None:
                        effect += f" (Medic save failed: {save_roll})"
            else:
                effect = "Crew member already KIA - no effect"
            description = f"Crew Casualty! {effect}"
        
        # Check for ship blocking forced ascent (after hull damage applied)
        if hull_damage > 0 and not is_destroyed and ships is not None:
            from ..depth_validator import DepthValidator
            max_allowed_depth = DepthValidator.max_depth_for_hull_damage(u_boat.hull_damage)
            
            # If U-boat is deeper than allowed, it must ascend
            # Depth values: SURFACED=0, PERISCOPE=1, MEDIUM=2, DEEP=3
            if u_boat.depth.value > max_allowed_depth.value:
                # Check if any ship is in same hex, blocking ascent
                ship_in_hex = any(ship.position == u_boat.position for ship in ships)
                if ship_in_hex:
                    is_destroyed = True
                    u_boat.hull_damage = 4
                    description += " - Ship blocks forced ascent - U-BOAT DESTROYED!"
        
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
        damaged: List[int] = []
        for _ in range(num_dice):
            roll = self.dice.roll_1d6()
            if roll <= 5:  # Valid tube number (1-5)
                tube_index = roll - 1
                # Only damage if not already damaged
                if u_boat.torpedo_tubes[tube_index]:
                    u_boat.torpedo_tubes[tube_index] = False
                    damaged.append(tube_index)
        return damaged
