"""
Action cost lookup system for Lone U-Boat.

Reads action costs from JSON rules and provides fast lookups by action and depth.
All costs come from missions/u_boat_ruleset_default.json -> u_boat_action_costs
"""

from typing import Dict, Optional, List, Any
from enum import Enum

from .models import Depth


class ActionType(str, Enum):
    """Valid U-Boat action types."""
    MOVE = "MOVE"
    TURN = "TURN"
    CHANGE_DEPTH = "CHANGE DEPTH"
    REPAIR = "REPAIR"
    FIRE_DECK_GUN = "FIRE DECK GUN"
    LOAD_TORPS = "LOAD TORPS"
    FIRE_TORPS = "FIRE TORPS"


class ActionCostLookup:
    """
    Lookup action costs from JSON rules.
    
    Parses u_boat_action_costs from mission rules and provides efficient
    cost queries by action name and depth.
    """
    
    def __init__(self, mission_rules: Any):
        """
        Initialize cost lookup from mission rules.
        
        Args:
            mission_rules: MissionRules instance with loaded JSON
        """
        self.mission_rules = mission_rules
        self.costs: Dict[str, Dict[Depth, Optional[int]]] = {}
        self.restrictions: Dict[str, List[str]] = {}
        self.requirements: Dict[str, Dict[str, Any]] = {}
        
        self._parse_action_costs()
    
    def _parse_action_costs(self):
        """Parse u_boat_action_costs from JSON rules."""
        try:
            # Get action costs from u_boat_ruleset_default.json
            action_costs = self.mission_rules.get_section_by_id("u_boat_action_costs")
            
            if not action_costs or "actions" not in action_costs:
                raise ValueError("u_boat_action_costs not found in mission rules")
            
            # Parse each action
            for action_data in action_costs["actions"]:
                action_name = action_data["action"]
                
                # Parse costs by depth
                depth_costs = {}
                costs_data = action_data.get("costs", {})
                
                for depth_name, cost in costs_data.items():
                    try:
                        depth = Depth[depth_name]
                        depth_costs[depth] = cost  # cost can be int or None
                    except KeyError:
                        print(f"Warning: Unknown depth '{depth_name}' for action {action_name}")
                
                self.costs[action_name] = depth_costs
                
                # Parse restrictions
                if "restrictions" in action_data:
                    self.restrictions[action_name] = action_data["restrictions"]
                
                # Parse requirements (for REPAIR action, etc.)
                if "requirements" in action_data:
                    self.requirements[action_name] = action_data["requirements"]
        
        except Exception as e:
            print(f"Error parsing action costs: {e}")
            # Initialize with empty dicts to avoid crashes
            self.costs = {}
            self.restrictions = {}
            self.requirements = {}
    
    def get_cost(self, action: str, depth: Depth) -> Optional[int]:
        """
        Get AP cost for action at given depth.
        
        Args:
            action: Action name (e.g., "MOVE", "TURN")
            depth: Current U-Boat depth
            
        Returns:
            AP cost (int) or None if action unavailable at this depth
        """
        if action not in self.costs:
            return None
        
        return self.costs[action].get(depth)
    
    def is_available_at_depth(self, action: str, depth: Depth) -> bool:
        """
        Check if action is available at given depth.
        
        Args:
            action: Action name
            depth: Current U-Boat depth
            
        Returns:
            True if action has a cost (not None) at this depth
        """
        cost = self.get_cost(action, depth)
        return cost is not None
    
    def get_all_costs_at_depth(self, depth: Depth) -> Dict[str, int]:
        """
        Get all available actions and their costs at given depth.
        
        Args:
            depth: Current U-Boat depth
            
        Returns:
            Dictionary of {action_name: cost} for available actions
        """
        available: Dict[str, int] = {}
        
        for action, depth_costs in self.costs.items():
            cost = depth_costs.get(depth)
            if cost is not None:
                available[action] = cost
        
        return available
    
    def get_restrictions(self, action: str) -> List[str]:
        """
        Get list of restrictions for an action.
        
        Args:
            action: Action name
            
        Returns:
            List of restriction strings from JSON
        """
        return self.restrictions.get(action, [])
    
    def get_requirements(self, action: str) -> Dict[str, Any]:
        """
        Get requirements for an action.
        
        Args:
            action: Action name
            
        Returns:
            Dictionary of requirements from JSON
        """
        return self.requirements.get(action, {})
    
    def get_all_actions(self) -> List[str]:
        """Get list of all action names."""
        return list(self.costs.keys())
    
    def format_action_summary(self, depth: Depth) -> List[str]:
        """
        Format available actions at depth for display.
        
        Args:
            depth: Current U-Boat depth
            
        Returns:
            List of formatted strings like "MOVE (1 AP)", "TURN (1 AP)"
        """
        summary: List[str] = []
        available = self.get_all_costs_at_depth(depth)
        
        for action, cost in sorted(available.items()):
            summary.append(f"{action} ({cost} AP)")
        
        return summary
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<ActionCostLookup: {len(self.costs)} actions>"
