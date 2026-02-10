"""
End Turn Events System (Phase 6).

Handles random events that occur at the end of each turn based on 2d6 roll.
Events can spawn ships, aircraft, change weather, or trigger special occurrences.
Events may have conditions that must be met for them to execute.
"""

from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from .models import Ship, Aircraft, HexCoord, Facing, Depth
from .dice import DiceRoller

if TYPE_CHECKING:
    from .game_state import GameState


@dataclass
class EventResult:
    """Result of an end-turn event."""
    event_name: str
    description: str
    spawned_ships: List[Ship]
    spawned_aircraft: List[Aircraft]
    special_effects: List[str]  # Special game state changes
    messages: List[str]
    condition_met: bool  # Whether event condition was met


class EventSystem:
    """Manages end-of-turn random events for missions."""
    
    def __init__(self, mission_rules: Dict[str, Any], dice_roller: DiceRoller, game_state: 'GameState' = None):
        """Initialize event system with mission-specific event table.
        
        Args:
            mission_rules: Mission configuration dictionary
            dice_roller: Dice roller for event rolls
            game_state: Reference to game state for checking conditions and applying effects
        """
        self.dice = dice_roller
        self.mission_rules = mission_rules
        self.game_state = game_state
        
        # Load event table from mission rules
        self.event_table_config = self._load_event_table()
        self.enabled = self.event_table_config.get('enabled', False)
    
    def _load_event_table(self) -> Dict[str, Any]:
        """Load end_of_turn_events configuration from mission rules."""
        # Handle both dict and MissionRules object
        if hasattr(self.mission_rules, 'get_section_by_id'):
            # MissionRules object
            section = self.mission_rules.get_section_by_id('end_of_turn_events')
            return section if section else {'enabled': False, 'events': {}}
        else:
            # Dict format (legacy or direct dict)
            tables = self.mission_rules.get('mission_tables', [])
            for table in tables:
                if table.get('id') == 'end_of_turn_events':
                    return table
            # Also check sections
            sections = self.mission_rules.get('sections', [])
            for section in sections:
                if section.get('id') == 'end_of_turn_events':
                    return section
            # Default: disabled
            return {'enabled': False, 'events': {}}
    
    def execute_end_turn_events(self, turn_number: int) -> EventResult:
        """Execute end-of-turn event for current turn.
        
        Args:
            turn_number: Current turn number
        
        Returns:
            EventResult with spawned entities and messages
        """
        # If events disabled, return empty result
        if not self.enabled:
            return EventResult(
                event_name="No Events",
                description="End-of-turn events not enabled for this mission",
                spawned_ships=[],
                spawned_aircraft=[],
                special_effects=[],
                messages=[],
                condition_met=False
            )
        
        # Roll 2d6 for event
        roll = self.dice.roll_2d6()
        
        # Get individual dice from roll history (if available)
        if hasattr(self.dice, 'roll_history') and len(self.dice.roll_history) > 0:
            last_record = self.dice.roll_history[-1]
            if hasattr(last_record, 'rolls') and len(last_record.rolls) == 2:
                self.last_roll_dice = (last_record.rolls[0], last_record.rolls[1])
            else:
                # Fallback: split evenly (for MockDice that doesn't track individual rolls)
                self.last_roll_dice = (roll // 2, roll - roll // 2)
        else:
            # Fallback for test mocks without roll_history
            self.last_roll_dice = (roll // 2, roll - roll // 2)
        
        # Get event from table
        event_config = self._get_event_for_roll(roll, turn_number)
        
        if event_config is None:
            # Format dice roll message for no-event
            if hasattr(self, 'last_roll_dice'):
                die1, die2 = self.last_roll_dice
                roll_msg = f"End Turn Event: rolled 2d6 [{die1},{die2}] = {roll} - No event"
            else:
                roll_msg = f"End Turn Event Roll: {roll} - No event"
            
            return EventResult(
                event_name="No Event",
                description=f"Rolled {roll}: No event occurs",
                spawned_ships=[],
                spawned_aircraft=[],
                special_effects=[],
                messages=[roll_msg],
                condition_met=False
            )
        
        # Execute the event
        return self._execute_event(event_config, roll)
    
    def _get_event_for_roll(self, roll: int, turn_number: int) -> Optional[Dict[str, Any]]:
        """Get event configuration for a 2d6 roll.
        
        Args:
            roll: 2d6 result (2-12)
            turn_number: Current turn number
        
        Returns:
            Event configuration dict or None if no event
        """
        events = self.event_table_config.get('events', {})
        
        # Check for turn-specific event first
        turn_key = f"turn_{turn_number}"
        if turn_key in events:
            turn_events = events[turn_key]
            if str(roll) in turn_events:
                return turn_events[str(roll)]
        
        # Check for general event
        if str(roll) in events:
            return events[str(roll)]
        
        return None
    
    def _execute_event(self, event_config: Dict[str, Any], roll: int) -> EventResult:
        """Execute a specific event based on configuration.
        
        Args:
            event_config: Event configuration dictionary
            roll: The 2d6 roll that triggered this event
        
        Returns:
            EventResult with spawned entities and messages
        """
        event_type = event_config.get('type', 'none')
        event_name = event_config.get('name', 'Unknown Event')
        description = event_config.get('description', '')
        condition_str = event_config.get('condition', None)
        
        # Format dice roll message
        if hasattr(self, 'last_roll_dice'):
            die1, die2 = self.last_roll_dice
            roll_msg = f"End Turn Event: rolled 2d6 [{die1},{die2}] = {roll}"
        else:
            roll_msg = f"End Turn Event Roll: {roll}"
        
        messages = [
            roll_msg,
            f"Event: {event_name}"
        ]
        
        # Check condition if present
        condition_met = True
        if condition_str and self.game_state:
            condition_met = self._check_condition(condition_str)
            if not condition_met:
                messages.append(f"  Condition not met: {condition_str}")
                messages.append(f"  Event not triggered")
                return EventResult(
                    event_name=event_name,
                    description=description,
                    spawned_ships=[],
                    spawned_aircraft=[],
                    special_effects=[],
                    messages=messages,
                    condition_met=False
                )
        
        messages.append(f"  {description}")
        
        spawned_ships = []
        spawned_aircraft = []
        special_effects = []
        
        # Handle different event types
        if event_type == 'ship_spawn':
            spawned_ships = self._spawn_ships(event_config, messages)
        
        elif event_type == 'aircraft_spawn':
            spawned_aircraft = self._spawn_aircraft(event_config, messages)
        
        elif event_type == 'multiple_spawns':
            # Both ships and aircraft
            if 'ships' in event_config:
                spawned_ships = self._spawn_ships({'ships': event_config['ships']}, messages)
            if 'aircraft' in event_config:
                spawned_aircraft = self._spawn_aircraft({'aircraft': event_config['aircraft']}, messages)
        
        elif event_type == 'weather':
            self._handle_weather_event(event_config, messages)
        
        elif event_type == 'special':
            # Special events with game state effects
            effect = event_config.get('effect', '')
            special_effects.append(effect)
            messages.append(f"  Effect: {effect}")
        
        return EventResult(
            event_name=event_name,
            description=description,
            spawned_ships=spawned_ships,
            spawned_aircraft=spawned_aircraft,
            special_effects=special_effects,
            messages=messages,
            condition_met=True
        )
    
    def _check_condition(self, condition_str: str) -> bool:
        """Check if event condition is met.
        
        Args:
            condition_str: Condition string to evaluate
        
        Returns:
            True if condition met, False otherwise
        """
        if not self.game_state:
            return True  # No game state, allow event
        
        # Parse condition string (simplified evaluation)
        # Format: "detection_level >= 2" or "depth == 3" etc.
        
        try:
            # Get current game state values
            dl = self.game_state.detection_level
            depth_value = self.game_state.u_boat.depth.value if hasattr(self.game_state.u_boat.depth, 'value') else 0
            engine_damaged = self.game_state.u_boat.engine_damaged
            
            # Simple condition evaluation
            if "detection_level >= 2" in condition_str:
                return dl >= 2
            elif "detection_level < 3" in condition_str:
                return dl < 3
            elif "depth <= 1 and detection_level == 0" in condition_str:
                return depth_value <= 1 and dl == 0
            elif "depth == 3" in condition_str:
                return depth_value == 3
            elif "depth > 0 and engine_not_damaged" in condition_str:
                return depth_value > 0 and not engine_damaged
            
            # Default: condition met
            return True
            
        except Exception:
            # If condition evaluation fails, allow event
            return True
    
    def _spawn_ships(self, config: Dict[str, Any], messages: List[str]) -> List[Ship]:
        """Spawn ships based on event configuration.
        
        Args:
            config: Ship spawn configuration
            messages: List to append messages to
        
        Returns:
            List of spawned Ship objects
        """
        ships_config = config.get('ships', [])
        if isinstance(ships_config, dict):
            ships_config = [ships_config]
        
        spawned = []
        for ship_data in ships_config:
            ship = Ship(
                position=HexCoord(ship_data['position'][0], ship_data['position'][1]),
                facing=self._parse_facing(ship_data['facing']),
                ship_type=ship_data['type'],
                damaged=ship_data.get('damaged', False)
            )
            spawned.append(ship)
            messages.append(f"  Spawned {ship.ship_type} at [{ship.position.q},{ship.position.r}] facing {ship.facing.name}")
        
        return spawned
    
    def _spawn_aircraft(self, config: Dict[str, Any], messages: List[str]) -> List[Aircraft]:
        """Spawn aircraft based on event configuration.
        
        Args:
            config: Aircraft spawn configuration
            messages: List to append messages to
        
        Returns:
            List of spawned Aircraft objects
        """
        aircraft_config = config.get('aircraft', [])
        if isinstance(aircraft_config, dict):
            aircraft_config = [aircraft_config]
        
        spawned = []
        for aircraft_data in aircraft_config:
            # Handle dynamic positioning
            if aircraft_data.get('position') == 'edge_furthest_from_uboat':
                if self.game_state:
                    position = self._get_furthest_edge_position()
                else:
                    position = HexCoord(0, 0)  # Fallback
            else:
                pos_data = aircraft_data.get('position', [0, 0])
                position = HexCoord(pos_data[0], pos_data[1])
            
            # Handle dynamic facing
            if aircraft_data.get('facing') == 'towards_uboat':
                if self.game_state:
                    facing = self._get_facing_towards_uboat(position)
                else:
                    facing = Facing.SOUTH  # Fallback
            else:
                facing = self._parse_facing(aircraft_data.get('facing', 'S'))
            
            aircraft = Aircraft(
                position=position,
                facing=facing,
                aircraft_type=aircraft_data.get('type', 'b24')
            )
            spawned.append(aircraft)
            messages.append(f"  Spawned {aircraft.aircraft_type.upper()} at [{aircraft.position.q},{aircraft.position.r}] facing {aircraft.facing.name}")
        
        return spawned
    
    def _handle_weather_event(self, config: Dict[str, Any], messages: List[str]) -> None:
        """Handle weather change events.
        
        Args:
            config: Weather event configuration
            messages: List to append messages to
        """
        weather_type = config.get('weather_type', 'fog')
        effect = config.get('effect', '')
        
        messages.append(f"  Weather: {weather_type}")
        if effect:
            messages.append(f"  Effect: {effect}")
    
    def _get_furthest_edge_position(self) -> HexCoord:
        """Get position on map edge furthest from U-boat on same hex-line.
        
        According to RULES.txt: "trace the 6 lines of hexes that run out of the 
        U-Boat's current hex until you reach the edge of the Map. Of the six lines, 
        take the longest (decide randomly if there is a tie). Then place the B24 on 
        the hex at the edge of the Map at the end of the longest line."
        
        Returns:
            HexCoord on edge of map (guaranteed to be a valid mission hex)
        """
        if not self.game_state:
            return HexCoord(0, 0)
        
        uboat_pos = self.game_state.u_boat.position
        
        # Get map bounds from mission hexes
        if hasattr(self.game_state, 'mission_hexes') and self.game_state.mission_hexes:
            hexes = self.game_state.mission_hexes
            
            # Trace lines in all 6 directions from U-boat
            longest_line = []
            longest_distance = 0
            
            for facing in [Facing.NORTH, Facing.NORTHEAST, Facing.SOUTHEAST, 
                          Facing.SOUTH, Facing.SOUTHWEST, Facing.NORTHWEST]:
                # Trace line in this direction until we hit edge or off-map
                current = uboat_pos
                line_hexes = []
                
                for _ in range(50):  # Max trace distance
                    current = facing.forward(current)
                    if current not in hexes:
                        # Hit edge - last valid hex was the end of the line
                        break
                    line_hexes.append(current)
                
                # Check if this is the longest line
                if len(line_hexes) > longest_distance:
                    longest_distance = len(line_hexes)
                    longest_line = line_hexes
            
            # Return the last hex in the longest line (edge of map)
            if longest_line:
                return longest_line[-1]
        
        # Fallback
        return HexCoord(uboat_pos.q + 10, uboat_pos.r)
    
    def _get_facing_towards_uboat(self, position: HexCoord) -> Facing:
        """Get facing direction from position towards U-boat.
        
        Args:
            position: Starting position
        
        Returns:
            Facing enum pointing towards U-boat
        """
        if not self.game_state:
            return Facing.SOUTH
        
        uboat_pos = self.game_state.u_boat.position
        
        # Calculate direction vector
        dq = uboat_pos.q - position.q
        dr = uboat_pos.r - position.r
        
        # Determine facing based on direction
        if abs(dq) > abs(dr):
            # Primary direction is horizontal
            if dq > 0:
                return Facing.SOUTHEAST if dr > 0 else Facing.NORTHEAST if dr < 0 else Facing.SOUTHEAST
            else:
                return Facing.NORTHWEST if dr < 0 else Facing.SOUTHWEST if dr > 0 else Facing.NORTHWEST
        else:
            # Primary direction is vertical
            if dr > 0:
                return Facing.SOUTH if abs(dq) < abs(dr) else Facing.SOUTHWEST if dq < 0 else Facing.SOUTHEAST
            else:
                return Facing.NORTH if abs(dq) < abs(dr) else Facing.NORTHWEST if dq < 0 else Facing.NORTHEAST
    
    def _parse_facing(self, facing_str: str) -> Facing:
        """Parse facing string to Facing enum.
        
        Args:
            facing_str: Facing string ('N', 'NE', 'SE', 'S', 'SW', 'NW' or full names)
        
        Returns:
            Facing enum value
        """
        facing_map = {
            'N': Facing.NORTH, 'NORTH': Facing.NORTH,
            'NE': Facing.NORTHEAST, 'NORTHEAST': Facing.NORTHEAST,
            'SE': Facing.SOUTHEAST, 'SOUTHEAST': Facing.SOUTHEAST,
            'S': Facing.SOUTH, 'SOUTH': Facing.SOUTH,
            'SW': Facing.SOUTHWEST, 'SOUTHWEST': Facing.SOUTHWEST,
            'NW': Facing.NORTHWEST, 'NORTHWEST': Facing.NORTHWEST
        }
        
        return facing_map.get(facing_str.upper(), Facing.NORTH)
