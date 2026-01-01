"""
Mission Rules Loader

Utilities for loading and querying structured mission metadata with layered inheritance.

Layered Architecture:
    1. core_system_rules.json - Immutable game mechanics (NEVER override)
    2. u_boat_ruleset_default.json - Standard U-Boat capabilities (RARELY override)
    3. escort_ai_baseline.json - Standard escort AI behavior (RARELY override)
    4. mission_X_rules.json - Mission-specific rules + overrides (ALWAYS override)
"""

import json
from pathlib import Path
from typing import Any, Optional


class MissionRules:
    """
    Structured mission rules loaded from JSON metadata.
    Provides convenience methods for querying rules by phase, type, and ID.
    Supports layered inheritance from baseline rule files.
    """
    
    # Non-overrideable section IDs from core_system_rules.json
    CORE_SECTIONS = {
        "u_boat_damage_chart",
        "allied_ship_damage",
        "reminder_rules"
    }
    
    def __init__(self, mission_data: dict[str, Any]):
        """
        Initialize with mission data dictionary (after layer merging).
        
        Args:
            mission_data: Parsed JSON mission data with all layers merged
        """
        self.meta = mission_data.get("mission_meta", {})
        self.sections = mission_data.get("sections", [])
        # Inherits can be at top level or in mission_meta
        self.inherits = mission_data.get("inherits", self.meta.get("inherits", []))
        self._section_index = self._build_section_index()
    
    def _build_section_index(self) -> dict[str, dict[str, Any]]:
        """Build an index of sections by ID for fast lookup."""
        return {section["id"]: section for section in self.sections if "id" in section}
    
    # ==================== METADATA ====================
    
    @property
    def mission_number(self) -> int:
        """Get mission number."""
        return self.meta.get("number", 0)
    
    @property
    def mission_title(self) -> str:
        """Get mission title."""
        return self.meta.get("title", "Unknown Mission")
    
    @property
    def objective(self) -> str:
        """Get mission objective text."""
        return self.meta.get("objective", "")
    
    @property
    def difficulty(self) -> str:
        """Get mission difficulty."""
        return self.meta.get("difficulty", "unknown")
    
    # ==================== SECTION QUERIES ====================
    
    def get_section_by_id(self, section_id: str) -> Optional[dict[str, Any]]:
        """
        Get a specific section by its ID.
        
        Args:
            section_id: The section ID (e.g., "u_boat_action_costs")
        
        Returns:
            Section dictionary or None if not found
        """
        return self._section_index.get(section_id)
    
    def get_sections_by_phase(self, phase: int) -> list[dict[str, Any]]:
        """
        Get all sections for a specific game phase.
        
        Args:
            phase: Phase number (1-6)
        
        Returns:
            List of section dictionaries
        """
        return [s for s in self.sections if s.get("phase") == phase]
    
    def get_sections_by_type(self, section_type: str) -> list[dict[str, Any]]:
        """
        Get all sections of a specific type.
        
        Args:
            section_type: Section type (e.g., "action_costs", "damage_chart")
        
        Returns:
            List of section dictionaries
        """
        return [s for s in self.sections if s.get("type") == section_type]
    
    def get_global_sections(self) -> list[dict[str, Any]]:
        """
        Get all sections with phase=null (applies to all phases).
        
        Returns:
            List of global section dictionaries
        """
        return [s for s in self.sections if s.get("phase") is None]
    
    # ==================== ACTION COSTS ====================
    
    def get_action_cost(self, action_name: str, depth: str) -> Optional[int]:
        """
        Get the AP cost for a specific action at a given depth.
        
        Args:
            action_name: Action name (e.g., "MOVE", "TURN")
            depth: Depth level (e.g., "SURFACED", "MEDIUM")
        
        Returns:
            AP cost or None if action not available at that depth
        """
        action_costs_section = self.get_section_by_id("u_boat_action_costs")
        if not action_costs_section:
            return None
        
        for action in action_costs_section.get("actions", []):
            if action["action"] == action_name:
                return action["costs"].get(depth)
        
        return None
    
    def get_action_notes(self, action_name: str) -> Optional[str]:
        """
        Get the notes/constraints for a specific action.
        
        Args:
            action_name: Action name (e.g., "MOVE", "TURN")
        
        Returns:
            Notes string or None
        """
        action_costs_section = self.get_section_by_id("u_boat_action_costs")
        if not action_costs_section:
            return None
        
        for action in action_costs_section.get("actions", []):
            if action["action"] == action_name:
                return action.get("notes")
        
        return None
    
    def get_available_actions(self, depth: str) -> list[dict[str, Any]]:
        """
        Get all actions available at a given depth.
        
        Args:
            depth: Depth level (e.g., "SURFACED", "MEDIUM")
        
        Returns:
            List of action dictionaries with costs
        """
        action_costs_section = self.get_section_by_id("u_boat_action_costs")
        if not action_costs_section:
            return []
        
        available: list[dict[str, Any]] = []
        for action in action_costs_section.get("actions", []):
            cost = action["costs"].get(depth)
            if cost is not None:
                available.append({
                    "action": action["action"],
                    "cost": cost,
                    "notes": action.get("notes", "")
                })
        
        return available
    
    # ==================== DEPTH MODIFIERS ====================
    
    def get_depth_dl_modifier(self, depth: str) -> int:
        """
        Get the detection level modifier for a given depth.
        
        Args:
            depth: Depth level (e.g., "SURFACED", "MEDIUM")
        
        Returns:
            DL modifier (negative values decrease DL)
        """
        depth_mods_section = self.get_section_by_id("u_boat_depth_modifiers")
        if not depth_mods_section:
            return 0
        
        for mod in depth_mods_section.get("modifiers", []):
            if mod["depth"] == depth:
                return mod["dl_modifier"]
        
        return 0
    
    # ==================== DAMAGE CHARTS ====================
    
    def get_ship_damage_outcome(self, ship_type: str, roll: int) -> Optional[dict[str, Any]]:
        """
        Look up damage outcome for a ship given a dice roll.
        
        Args:
            ship_type: Ship type (e.g., "merchant", "corvette", "destroyer")
            roll: Dice roll result (1-6)
        
        Returns:
            Outcome dictionary with result and description, or None
        """
        damage_chart = self.get_section_by_id("allied_ship_damage")
        if not damage_chart:
            return None
        
        for ship_class in damage_chart.get("ship_classes", []):
            if ship_class["ship_type"] == ship_type:
                for outcome in ship_class["outcomes"]:
                    if outcome["roll_min"] <= roll <= outcome["roll_max"]:
                        return {
                            "result": outcome["result"],
                            "description": outcome["description"]
                        }
        
        return None
    
    def get_u_boat_damage_outcome(self, roll: int) -> Optional[dict[str, Any]]:
        """
        Look up U-Boat damage outcome given a dice roll.
        
        Args:
            roll: Dice roll result (1-6)
        
        Returns:
            Outcome dictionary with result, description, and possible sub_table
        """
        damage_chart = self.get_section_by_id("u_boat_damage_chart")
        if not damage_chart:
            return None
        
        for outcome in damage_chart.get("outcomes", []):
            if outcome["roll_min"] <= roll <= outcome["roll_max"]:
                return outcome
        
        return None
    
    def get_u_boat_sub_table_outcome(self, table_name: str, roll: int) -> Optional[dict[str, Any]]:
        """
        Look up outcome from a U-Boat damage sub-table.
        
        Args:
            table_name: Sub-table name (e.g., "critical_hit_table")
            roll: Dice roll result (1-6)
        
        Returns:
            Outcome dictionary or None
        """
        damage_chart = self.get_section_by_id("u_boat_damage_chart")
        if not damage_chart:
            return None
        
        sub_tables = damage_chart.get("sub_tables", {})
        sub_table = sub_tables.get(table_name)
        if not sub_table:
            return None
        
        for outcome in sub_table.get("outcomes", []):
            if outcome["roll_min"] <= roll <= outcome["roll_max"]:
                return outcome
        
        return None
    
    # ==================== DETECTION ====================
    
    def get_detection_threshold(self, depth: str) -> int:
        """
        Get base detection roll threshold for a given depth.
        
        Args:
            depth: Depth level (e.g., "SURFACED", "MEDIUM")
        
        Returns:
            Minimum roll required for detection (1-6)
        """
        detection_section = self.get_section_by_id("detection_rules")
        if not detection_section:
            return 6  # Default: very hard to detect
        
        for threshold in detection_section.get("base_detection_thresholds", []):
            if threshold["depth"] == depth:
                return threshold["roll_required"]
        
        return 6
    
    def get_detection_modifiers(self) -> list[dict[str, Any]]:
        """
        Get all detection modifiers (engine damage, sonar operator, etc.).
        
        Returns:
            List of modifier dictionaries
        """
        detection_section = self.get_section_by_id("detection_rules")
        if not detection_section:
            return []
        
        return detection_section.get("modifiers", [])
    
    # ==================== ESCORT BEHAVIOR ====================
    
    def get_escort_action_result(self, ship_type: str, roll: int) -> Optional[dict[str, Any]]:
        """
        Get escort action for a given ship type and dice roll.
        
        Args:
            ship_type: "destroyer" or "corvette"
            roll: Dice roll result (1-6)
        
        Returns:
            Action result dictionary or None
        """
        section_id = f"{ship_type}_actions"
        action_table = self.get_section_by_id(section_id)
        if not action_table:
            return None
        
        for result in action_table.get("results", []):
            if result["roll"] == roll:
                return result
        
        return None
    
    def get_escort_action_definition(self, action_name: str) -> Optional[dict[str, Any]]:
        """
        Get detailed definition of an escort action (FIRE, DEPTH_CHARGE, etc.).
        
        Args:
            action_name: Action name (e.g., "DEPTH_CHARGE")
        
        Returns:
            Action definition dictionary or None
        """
        definitions = self.get_section_by_id("escort_action_definitions")
        if not definitions:
            return None
        
        for action in definitions.get("actions", []):
            if action["action"] == action_name:
                return action
        
        return None
    
    # ==================== VICTORY CONDITIONS ====================
    
    def get_victory_conditions(self) -> Optional[dict[str, Any]]:
        """
        Get all victory/failure conditions.
        
        Returns:
            Victory conditions dictionary or None
        """
        return self.get_section_by_id("victory_conditions")
    
    # ==================== REMINDER RULES ====================
    
    def get_reminder_rules(self) -> list[dict[str, Any]]:
        """
        Get all reminder rules (forced dive, shallow water, etc.).
        
        Returns:
            List of reminder rule dictionaries
        """
        reminder_section = self.get_section_by_id("reminder_rules")
        if not reminder_section:
            return []
        
        return reminder_section.get("rules", [])
    
    def get_reminder_by_category(self, category: str) -> Optional[dict[str, Any]]:
        """
        Get a specific reminder rule by category.
        
        Args:
            category: Rule category (e.g., "forced_dive", "shallow_water")
        
        Returns:
            Reminder rule dictionary or None
        """
        for rule in self.get_reminder_rules():
            if rule.get("category") == category:
                return rule
        
        return None


def load_mission_rules(mission_number: int, missions_dir: str = "missions") -> MissionRules:
    """
    Load mission rules from JSON file with layered inheritance.
    
    Args:
        mission_number: Mission number (1, 2, 3, etc.)
        missions_dir: Directory containing mission files
    
    Returns:
        MissionRules instance with all layers merged
    
    Raises:
        FileNotFoundError: If mission rules file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        ValueError: If mission attempts to override core sections
    """
    missions_path = Path(missions_dir)
    rules_file = missions_path / f"mission_{mission_number}_rules.json"
    
    if not rules_file.exists():
        raise FileNotFoundError(f"Mission rules file not found: {rules_file}")
    
    with rules_file.open("r", encoding="utf-8") as f:
        mission_data = json.load(f)
    
    # Get list of files to inherit from (can be at top level or in mission_meta)
    inherits = mission_data.get("inherits", mission_data.get("mission_meta", {}).get("inherits", []))
    
    # Load and merge layers
    merged_data = _merge_layers(missions_path, inherits, mission_data)
    
    # Validate that mission doesn't override core sections
    _validate_overrides(mission_data)
    
    return MissionRules(merged_data)


def load_mission_rules_from_path(file_path: str | Path) -> MissionRules:
    """
    Load mission rules from a specific file path (for testing/debugging).
    Does NOT perform layered inheritance - loads single file only.
    
    Args:
        file_path: Path to mission rules JSON file
    
    Returns:
        MissionRules instance (single file, no inheritance)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Mission rules file not found: {path}")
    
    with path.open("r", encoding="utf-8") as f:
        mission_data = json.load(f)
    
    return MissionRules(mission_data)


def _merge_layers(missions_dir: Path, inherits: list[str], mission_data: dict[str, Any]) -> dict[str, Any]:
    """
    Merge inherited layers with mission data.
    
    Args:
        missions_dir: Directory containing rule files
        inherits: List of baseline file names to inherit from (without .json)
        mission_data: Mission-specific data (top layer)
        
    Returns:
        Merged data dictionary
    """
    # Start with mission metadata and top-level fields
    merged: dict[str, Any] = {
        "mission_meta": mission_data.get("mission_meta", {}),
        "inherits": inherits,  # Preserve inherits list for reference
        "sections": []
    }
    
    section_index: dict[str, dict[str, Any]] = {}  # Track sections by ID to handle overrides
    
    # Load and merge each inherited layer in order
    for layer_name in inherits:
        layer_file = missions_dir / f"{layer_name}.json"
        if layer_file.exists():
            with layer_file.open("r", encoding="utf-8") as f:
                layer_data = json.load(f)
            
            # Baseline files have flat structure with sections as top-level keys
            # Mission files have sections array
            if "sections" in layer_data:
                # Mission file format - iterate sections array
                for section in layer_data["sections"]:
                    section_id = section.get("id")
                    if section_id:
                        section_index[section_id] = section.copy()
            else:
                # Baseline file format - iterate top-level keys (skip metadata)
                for key, value in layer_data.items():
                    if not key.startswith("_") and isinstance(value, dict) and "id" in value:
                        section_index[value["id"]] = value.copy()
    
    # Finally, add/override with mission-specific sections
    for section in mission_data.get("sections", []):
        section_id = section.get("id")
        if section_id:
            section_index[section_id] = section.copy()
    
    # Build final sections list
    merged["sections"] = list(section_index.values())
    
    return merged


def _validate_overrides(mission_data: dict[str, Any]):
    """
    Validate that mission doesn't override non-overrideable sections.
    
    Args:
        mission_data: Mission-specific data (before merging)
        
    Raises:
        ValueError: If mission attempts to override core sections
    """
    mission_section_ids = {s.get("id") for s in mission_data.get("sections", []) if s.get("id")}
    
    for core_id in MissionRules.CORE_SECTIONS:
        if core_id in mission_section_ids:
            raise ValueError(
                f"Mission attempts to override non-overrideable section: {core_id}. "
                f"Core system rules from core_system_rules.json cannot be overridden."
            )


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Example: Load Mission 1 rules with layered inheritance
    print("=== Loading Mission 1 with Layered Inheritance ===\n")
    
    try:
        rules = load_mission_rules(1)
        
        print(f"Mission: {rules.mission_title}")
        print(f"Objective: {rules.objective}")
        print(f"Inherits from: {', '.join(rules.inherits)}")
        print(f"Total sections loaded: {len(rules.sections)}\n")
        
        # Check action costs (from u_boat_ruleset_default)
        print("=== Action Costs (from u_boat_ruleset_default) ===")
        for action_name in ["MOVE", "TURN", "CHANGE DEPTH", "REPAIR", "FIRE DECK GUN", "LOAD TORPS", "FIRE TORPS"]:
            print(f"{action_name}:")
            
            # Special handling for REPAIR to show engineer requirements
            if action_name == "REPAIR":
                action_section = None
                for section in rules.sections:
                    if section.get("id") == "u_boat_action_costs":
                        for action in section.get("actions", []):
                            if action.get("action") == action_name:
                                action_section = action
                                break
                        break
                
                for depth in ["SURFACED", "PERISCOPE", "MEDIUM", "DEEP"]:
                    cost = rules.get_action_cost(action_name, depth)
                    if cost is not None:
                        req = action_section.get("requirements", {}).get(depth, "") if action_section else ""
                        if req and "Engineer must be alive" in req:
                            print(f"  {depth}: {cost} AP (Eng)")
                        else:
                            print(f"  {depth}: {cost} AP")
                    else:
                        print(f"  {depth}: --")
            else:
                for depth in ["SURFACED", "PERISCOPE", "MEDIUM", "DEEP"]:
                    cost = rules.get_action_cost(action_name, depth)
                    if cost is not None:
                        print(f"  {depth}: {cost} AP")
                    else:
                        print(f"  {depth}: --")
            print()
        
        # Check ship damage (from core_system_rules)
        print("=== Allied Ship Damage Chart (from core_system_rules) ===")
        for ship_type in ["merchant", "corvette", "destroyer"]:
            ship_name = ship_type.capitalize()
            print(f"{ship_name}:")
            for roll in range(1, 7):
                outcome = rules.get_ship_damage_outcome(ship_type, roll)
                if outcome:
                    print(f"  {roll}: {outcome['result']} — {outcome['description']}")
            print()
        
        # Check detection system (from escort_ai_baseline)
        print("=== Detection System (from escort_ai_baseline) ===")
        detection = rules.get_section_by_id("detection_rules")
        if detection:
            print(f"Phase: {detection.get('phase')}")
            print(f"Range: {detection.get('range')} hexes")
            print(f"LOS Required: {detection.get('requires_los')}")
            print("\nBase Detection Thresholds:")
            for depth in ["SURFACED", "PERISCOPE", "MEDIUM", "DEEP"]:
                threshold = rules.get_detection_threshold(depth)
                print(f"  {depth}: {threshold}+ on d6")
            print("\nModifiers:")
            mods = detection.get('modifiers', [])
            for mod in mods:
                print(f"  {mod.get('condition')}: {mod.get('effect'):+d} ({mod.get('description')})")
        print()
        
        # Check escort activation (from escort_ai_baseline)
        print("=== Escort Activation (from escort_ai_baseline) ===")
        activation = rules.get_section_by_id("escort_activation_order")
        if activation:
            print(f"Rule: {activation.get('rule')}")
            print(f"Tie-breaking: {activation.get('tie_breaking')}")
            print("Dice Calculation:")
            dice_calc = activation.get('dice_calculation', {})
            for ship_type, calc in dice_calc.items():
                formula = calc.get('formula', '')
                print(f"  {ship_type.capitalize()}: {formula}")
            print(f"Resolution: {activation.get('resolution')}")
        print()
        
        # Check escort action table (from escort_ai_baseline)
        print("=== Escort Action Table (from escort_ai_baseline) ===")
        escort_actions = rules.get_section_by_id("destroyer_actions")
        if escort_actions:
            print(f"Label: {escort_actions.get('label')}")
            print(f"Applies to: {escort_actions.get('ship_type').replace('_', ' ').title()}")
            print(f"Dice: {escort_actions.get('dice')}")
            print("\nAction Results:")
            for result in escort_actions.get('results', []):
                print(f"  {result.get('roll')}: {result.get('description')}")
        print()
        
        # Check merchant movement (from escort_ai_baseline)
        print("=== Merchant Ship Movement (from escort_ai_baseline) ===")
        merchant = rules.get_section_by_id("merchant_movement_default")
        if merchant:
            for rule in merchant.get('rules', []):
                condition = rule.get('condition', '')
                action = rule.get('action', '')
                if 'roll_required' in rule:
                    roll = rule.get('roll_required')
                    print(f"{condition}: Roll {roll} to {action}")
                elif 'distance' in rule:
                    distance = rule.get('distance', '')
                    path = rule.get('path', '')
                    print(f"{condition}: {action} {distance} hex ({path})")
                else:
                    print(f"{condition}: {action}")
        print()
        
        # Check B24 aircraft (from escort_ai_baseline)
        print("=== B24 Aircraft (from escort_ai_baseline) ===")
        b24 = rules.get_section_by_id("b24_default")
        if b24:
            print(f"Phase: {b24.get('phase')}")
            print(f"Max on map: {b24.get('max_on_map')}")
            move = b24.get('move', {})
            print(f"Movement: {move.get('distance')} hexes {move.get('direction')}")
            turn = b24.get('turn', {})
            print(f"Turn: {turn.get('condition')}")
            attack = b24.get('attack', {})
            print(f"Attack requirements: {', '.join(attack.get('requirements', []))}")
            flak = attack.get('flak_defense', {})
            print(f"Flak defense: {flak.get('roll')} {flak.get('success_base')} ({flak.get('success_with_lookout')})")
        print()
        
        # Check victory conditions (mission-specific)
        print("=== Victory Conditions (mission-specific) ===")
        victory = rules.get_victory_conditions()
        if victory:
            print(f"  Primary: {victory['primary']['description']}")
            print(f"  Secondary: {victory['secondary']['description']}")
            print(f"  Failure: {victory['failure']['description']}")
        
        print("\n=== Test Complete ===")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure mission_1_rules.json and baseline files exist in missions/")
    except ValueError as e:
        print(f"Validation Error: {e}")
