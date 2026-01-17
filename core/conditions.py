"""
Condition evaluators for game state and UI elements.
Used primarily for status box markers and game rules.
"""

from typing import Callable

from .models import UBoat


class ConditionFactory:
    """Factory for creating condition lambda functions based on string keys."""
    
    @staticmethod
    def create_condition(condition_key: str, u_boat: UBoat, detection_level: int) -> Callable[[], bool]:
        """Create a lambda function for status box conditions based on config string.
        
        Args:
            condition_key: String key describing the condition (e.g., 'detection_level_1')
            u_boat: Reference to the U-Boat object
            detection_level: Reference to detection level (passed as int, captured by closure)
            
        Returns:
            Lambda function that evaluates to True/False
        """
        # Detection levels
        if condition_key.startswith('detection_level_'):
            level = int(condition_key.split('_')[-1])
            # Note: We need to capture detection_level by reference
            # This is a limitation - caller must ensure detection_level is updated
            return lambda: detection_level == level
        
        # Hull damage
        elif condition_key.startswith('hull_damage_'):
            level = int(condition_key.split('_')[-1])
            return lambda: u_boat.hull_damage >= level
        
        # Torpedo tubes (condition is true if LOADED)
        elif condition_key.startswith('torpedo_tube_'):
            tube_index = int(condition_key.split('_')[-1])
            return lambda: u_boat.torpedo_tubes[tube_index] == TubeState.LOADED
        
        # Crew (alive status - condition triggers when dead)
        elif condition_key == 'captain_dead':
            return lambda: not u_boat.captain_alive
        elif condition_key == 'sonar_operator_dead':
            return lambda: not u_boat.sonar_operator_alive
        elif condition_key == 'engineer_dead':
            return lambda: not u_boat.engineer_alive
        elif condition_key == 'weapons_officer_dead':
            return lambda: not u_boat.weapons_officer_alive
        elif condition_key == 'lookout_dead':
            return lambda: not u_boat.lookout_alive
        elif condition_key == 'medic_dead':
            return lambda: not u_boat.medic_alive
        
        # Equipment damage
        elif condition_key == 'engine_damaged':
            return lambda: u_boat.engine_damaged
        elif condition_key == 'flak_gun_damaged':
            return lambda: u_boat.flak_gun_damaged
        elif condition_key == 'deck_gun_damaged':
            return lambda: u_boat.deck_gun_damaged
        
        # Default fallback
        return lambda: False
    
    @staticmethod
    def create_condition_with_getter(condition_key: str, 
                                     u_boat_getter: Callable[[], UBoat],
                                     detection_getter: Callable[[], int]) -> Callable[[], bool]:
        """Create condition with getter functions for dynamic state access.
        
        This version uses getter functions to access current state, avoiding closure issues.
        
        Args:
            condition_key: String key describing the condition
            u_boat_getter: Function that returns current UBoat instance
            detection_getter: Function that returns current detection level
            
        Returns:
            Lambda function that evaluates to True/False
        """
        # Detection levels
        if condition_key.startswith('detection_level_'):
            level = int(condition_key.split('_')[-1])
            return lambda: detection_getter() == level
        
        # Hull damage
        elif condition_key.startswith('hull_damage_'):
            level = int(condition_key.split('_')[-1])
            return lambda: u_boat_getter().hull_damage >= level
        
        # Torpedo tubes (condition is true if LOADED)
        elif condition_key.startswith('torpedo_tube_'):
            tube_index = int(condition_key.split('_')[-1])
            return lambda: u_boat_getter().torpedo_tubes[tube_index] == TubeState.LOADED
        
        # Crew (alive status - condition triggers when dead)
        elif condition_key == 'captain_dead':
            return lambda: not u_boat_getter().captain_alive
        elif condition_key == 'sonar_operator_dead':
            return lambda: not u_boat_getter().sonar_operator_alive
        elif condition_key == 'engineer_dead':
            return lambda: not u_boat_getter().engineer_alive
        elif condition_key == 'weapons_officer_dead':
            return lambda: not u_boat_getter().weapons_officer_alive
        elif condition_key == 'lookout_dead':
            return lambda: not u_boat_getter().lookout_alive
        elif condition_key == 'medic_dead':
            return lambda: not u_boat_getter().medic_alive
        
        # Equipment damage
        elif condition_key == 'engine_damaged':
            return lambda: u_boat_getter().engine_damaged
        elif condition_key == 'flak_gun_damaged':
            return lambda: u_boat_getter().flak_gun_damaged
        elif condition_key == 'deck_gun_damaged':
            return lambda: u_boat_getter().deck_gun_damaged
        
        # Default fallback
        return lambda: False
