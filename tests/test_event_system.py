"""
Tests for End Turn Events System (Phase 6).

Tests event rolling, condition checking, spawning mechanics, and special effects.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.event_system import EventSystem, EventResult
from core.models import UBoat, Ship, Aircraft, HexCoord, Facing, Depth
from core.dice import DiceRoller


class MockDice:
    """Mock dice roller for deterministic testing."""
    
    def __init__(self, predetermined_roll: int = 7):
        """Initialize with predetermined roll."""
        self.predetermined_roll = predetermined_roll
        self.roll_history = []
    
    def roll_2d6(self) -> int:
        """Return predetermined 2d6 roll."""
        self.roll_history.append(self.predetermined_roll)
        return self.predetermined_roll
    
    def roll_1d6(self) -> int:
        """Return predetermined 1d6 roll."""
        return self.predetermined_roll


class MockGameState:
    """Mock game state for testing event conditions."""
    
    def __init__(self, detection_level: int = 0, depth: Depth = Depth.SURFACED, 
                 engine_damaged: bool = False):
        """Initialize mock game state."""
        self.detection_level = detection_level
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=depth
        )
        self.u_boat.engine_damaged = engine_damaged
        self.mission_hexes = [HexCoord(q, r) for q in range(0, 11) for r in range(0, 11)]
        self.ships = []
        self.aircraft = []


def create_test_mission_rules(enabled: bool = True, events: dict = None) -> dict:
    """Create test mission rules with event table."""
    if events is None:
        events = {
            "7": {
                "type": "special",
                "name": "Test Event",
                "description": "Test event description",
                "effect": "test_effect"
            }
        }
    
    return {
        "sections": [
            {
                "id": "end_of_turn_events",
                "enabled": enabled,
                "events": events
            }
        ]
    }


# ==================== Event System Initialization Tests ====================

def test_event_system_initialization_enabled():
    """Test event system initializes correctly when enabled."""
    dice = MockDice()
    mission_rules = create_test_mission_rules(enabled=True)
    
    event_system = EventSystem(mission_rules, dice)
    
    assert event_system.enabled is True
    assert event_system.dice == dice


def test_event_system_initialization_disabled():
    """Test event system initializes correctly when disabled."""
    dice = MockDice()
    mission_rules = create_test_mission_rules(enabled=False)
    
    event_system = EventSystem(mission_rules, dice)
    
    assert event_system.enabled is False


def test_event_system_no_event_table():
    """Test event system handles missing event table gracefully."""
    dice = MockDice()
    mission_rules = {"sections": []}
    
    event_system = EventSystem(mission_rules, dice)
    
    assert event_system.enabled is False


# ==================== Event Rolling Tests ====================

def test_event_roll_executes_correct_event():
    """Test that correct event is executed based on 2d6 roll."""
    dice = MockDice(predetermined_roll=7)
    events = {
        "7": {
            "type": "special",
            "name": "Lucky Seven",
            "description": "Roll 7 event",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.event_name == "Lucky Seven"
    assert result.condition_met is True


def test_event_roll_no_event_for_roll():
    """Test that no event occurs when roll has no entry."""
    dice = MockDice(predetermined_roll=11)
    events = {
        "7": {
            "type": "special",
            "name": "Seven Only",
            "description": "Only on 7",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.event_name == "No Event"
    assert "11" in result.description


def test_event_disabled_returns_empty_result():
    """Test that disabled event system returns empty result."""
    dice = MockDice(predetermined_roll=7)
    mission_rules = create_test_mission_rules(enabled=False)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.event_name == "No Events"
    assert len(result.spawned_ships) == 0
    assert len(result.spawned_aircraft) == 0


# ==================== Condition Checking Tests ====================

def test_condition_detection_level_check():
    """Test condition checking for detection level."""
    dice = MockDice(predetermined_roll=6)
    events = {
        "6": {
            "type": "special",
            "name": "High DL Event",
            "description": "Requires DL >= 2",
            "condition": "detection_level >= 2",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=2)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is True
    assert result.event_name == "High DL Event"


def test_condition_detection_level_not_met():
    """Test event doesn't trigger when DL condition not met."""
    dice = MockDice(predetermined_roll=6)
    events = {
        "6": {
            "type": "special",
            "name": "High DL Event",
            "description": "Requires DL >= 2",
            "condition": "detection_level >= 2",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=1)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is False


def test_condition_depth_check():
    """Test condition checking for depth."""
    dice = MockDice(predetermined_roll=8)
    events = {
        "8": {
            "type": "special",
            "name": "Deep Event",
            "description": "Requires deep depth",
            "condition": "depth == 3",
            "effect": "hull_damage_1_force_medium"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(depth=Depth.DEEP)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is True
    assert result.event_name == "Deep Event"


def test_condition_depth_and_dl_combined():
    """Test combined depth and DL condition."""
    dice = MockDice(predetermined_roll=7)
    events = {
        "7": {
            "type": "special",
            "name": "Radio Event",
            "description": "Surfaced and DL 0",
            "condition": "depth <= 1 and detection_level == 0",
            "effect": "set_detection_level_1"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=0, depth=Depth.SURFACED)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is True


def test_condition_engine_damage_check():
    """Test condition checking for engine damage."""
    dice = MockDice(predetermined_roll=9)
    events = {
        "9": {
            "type": "special",
            "name": "Silent Running",
            "description": "Engine not damaged, submerged",
            "condition": "depth > 0 and engine_not_damaged",
            "effect": "reduce_detection_level_1"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(depth=Depth.PERISCOPE, engine_damaged=False)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is True


def test_condition_engine_damaged_fails_check():
    """Test event doesn't trigger when engine is damaged."""
    dice = MockDice(predetermined_roll=9)
    events = {
        "9": {
            "type": "special",
            "name": "Silent Running",
            "description": "Engine not damaged, submerged",
            "condition": "depth > 0 and engine_not_damaged",
            "effect": "reduce_detection_level_1"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(depth=Depth.PERISCOPE, engine_damaged=True)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is False


# ==================== Aircraft Spawning Tests ====================

def test_aircraft_spawn_with_static_position():
    """Test spawning aircraft with static position."""
    dice = MockDice(predetermined_roll=5)
    events = {
        "5": {
            "type": "aircraft_spawn",
            "name": "B24 Arrives",
            "description": "B24 spawns",
            "aircraft": [
                {
                    "type": "B24",
                    "position": [10, 5],
                    "facing": "W"
                }
            ]
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert len(result.spawned_aircraft) == 1
    assert result.spawned_aircraft[0].position == HexCoord(10, 5)
    assert result.spawned_aircraft[0].aircraft_type == "B24"


def test_aircraft_spawn_with_dynamic_position():
    """Test spawning aircraft with dynamic positioning."""
    dice = MockDice(predetermined_roll=4)
    events = {
        "4": {
            "type": "aircraft_spawn",
            "name": "B24 Arrives",
            "description": "B24 spawns at edge",
            "condition": "detection_level >= 2",
            "aircraft": [
                {
                    "type": "B24",
                    "position": "edge_furthest_from_uboat",
                    "facing": "towards_uboat"
                }
            ]
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=2)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert len(result.spawned_aircraft) == 1
    # Position should be calculated based on U-boat position
    assert result.spawned_aircraft[0].aircraft_type.lower() == "b24"


def test_aircraft_spawn_condition_not_met():
    """Test aircraft doesn't spawn when condition not met."""
    dice = MockDice(predetermined_roll=3)
    events = {
        "3": {
            "type": "aircraft_spawn",
            "name": "B24 Arrives",
            "description": "B24 spawns if DL >= 2",
            "condition": "detection_level >= 2",
            "aircraft": [
                {
                    "type": "B24",
                    "position": [10, 5],
                    "facing": "S"
                }
            ]
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=1)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert len(result.spawned_aircraft) == 0
    assert result.condition_met is False


# ==================== Special Effects Tests ====================

def test_special_effect_recorded():
    """Test special effects are recorded in result."""
    dice = MockDice(predetermined_roll=6)
    events = {
        "6": {
            "type": "special",
            "name": "Detection Event",
            "description": "Rerun detection",
            "condition": "detection_level < 3",
            "effect": "rerun_detection_phase"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=2)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert "rerun_detection_phase" in result.special_effects
    assert result.condition_met is True


def test_multiple_special_effects():
    """Test multiple events can have different special effects."""
    dice = MockDice()
    events = {
        "6": {
            "type": "special",
            "name": "Event 1",
            "description": "Effect 1",
            "effect": "effect_1"
        },
        "7": {
            "type": "special",
            "name": "Event 2",
            "description": "Effect 2",
            "effect": "effect_2"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    # Test roll 6
    dice.predetermined_roll = 6
    result1 = event_system.execute_end_turn_events(turn_number=1)
    assert "effect_1" in result1.special_effects
    
    # Test roll 7
    dice.predetermined_roll = 7
    result2 = event_system.execute_end_turn_events(turn_number=2)
    assert "effect_2" in result2.special_effects


# ==================== Turn-Specific Events Tests ====================

def test_turn_specific_event_overrides_general():
    """Test turn-specific events override general events."""
    dice = MockDice(predetermined_roll=7)
    events = {
        "7": {
            "type": "special",
            "name": "General Event",
            "description": "General event for all turns",
            "effect": "general_effect"
        },
        "turn_3": {
            "7": {
                "type": "special",
                "name": "Turn 3 Event",
                "description": "Special event for turn 3",
                "effect": "turn_3_effect"
            }
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    # Turn 1: general event
    result1 = event_system.execute_end_turn_events(turn_number=1)
    assert result1.event_name == "General Event"
    
    # Turn 3: specific event
    result3 = event_system.execute_end_turn_events(turn_number=3)
    assert result3.event_name == "Turn 3 Event"


def test_turn_specific_event_no_general_fallback():
    """Test turn without specific event uses general event."""
    dice = MockDice(predetermined_roll=8)
    events = {
        "8": {
            "type": "special",
            "name": "General Event",
            "description": "Always happens on 8",
            "effect": "general_effect"
        },
        "turn_5": {
            "7": {
                "type": "special",
                "name": "Turn 5 Special",
                "description": "Only on turn 5 roll 7",
                "effect": "turn_5_effect"
            }
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    # Turn 5 with roll 8: should use general event
    result = event_system.execute_end_turn_events(turn_number=5)
    assert result.event_name == "General Event"


# ==================== Message Generation Tests ====================

def test_event_messages_include_roll_and_name():
    """Test event messages include roll and event name."""
    dice = MockDice(predetermined_roll=7)
    events = {
        "7": {
            "type": "special",
            "name": "Test Event",
            "description": "Test description",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert any("Roll: 7" in msg for msg in result.messages)
    assert any("Test Event" in msg for msg in result.messages)


def test_condition_not_met_message():
    """Test message when condition not met."""
    dice = MockDice(predetermined_roll=6)
    events = {
        "6": {
            "type": "special",
            "name": "Conditional Event",
            "description": "Requires DL >= 2",
            "condition": "detection_level >= 2",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    game_state = MockGameState(detection_level=0)
    event_system = EventSystem(mission_rules, dice, game_state)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert any("Condition not met" in msg for msg in result.messages)
    assert any("not triggered" in msg for msg in result.messages)


# ==================== Edge Cases and Error Handling ====================

def test_missing_game_state_allows_event():
    """Test events execute without game state (no condition checking)."""
    dice = MockDice(predetermined_roll=7)
    events = {
        "7": {
            "type": "special",
            "name": "Unconditioned Event",
            "description": "No condition required",
            "effect": "test_effect"
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice, game_state=None)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.condition_met is True
    assert result.event_name == "Unconditioned Event"


def test_invalid_facing_string_defaults_to_north():
    """Test invalid facing string defaults gracefully."""
    dice = MockDice(predetermined_roll=5)
    events = {
        "5": {
            "type": "aircraft_spawn",
            "name": "B24 Arrives",
            "description": "B24 with invalid facing",
            "aircraft": [
                {
                    "type": "B24",
                    "position": [10, 5],
                    "facing": "INVALID"
                }
            ]
        }
    }
    mission_rules = create_test_mission_rules(events=events)
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert len(result.spawned_aircraft) == 1
    assert result.spawned_aircraft[0].facing == Facing.NORTH  # Default


def test_empty_events_dict():
    """Test event system with empty events dictionary."""
    dice = MockDice(predetermined_roll=7)
    mission_rules = create_test_mission_rules(events={})
    event_system = EventSystem(mission_rules, dice)
    
    result = event_system.execute_end_turn_events(turn_number=1)
    
    assert result.event_name == "No Event"
    assert len(result.spawned_ships) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
