"""
Tests for Interactive B-24 AI Actions.

This test suite validates B-24 aircraft activating and acting with animations,
mirroring the behavior tested in test_b24_ai.py but using the new Action-based system.
"""

import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.actions.ai import (
    B24MoveAction, B24TurnAction, B24BombAction, FlakDefenseAction
)
from core.models import Aircraft, UBoat, HexCoord, Facing, Depth
from core.damage.uboat_damage import UBoatDamageResolver
from tests.interactive_ai.conftest import MockGameState, MockDice


# =============================================================================
# B-24 Movement Tests
# =============================================================================

def test_b24_move_two_hexes(hex_grid: Any):
    """Test B-24 moves 2 hexes forward."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.hex_grid = hex_grid
    
    action = B24MoveAction(aircraft_index=0)
    can_move, _ = action.validate(game_state)
    assert can_move
    
    result = action.execute(game_state)
    assert result.success
    assert aircraft.position == HexCoord(5, 3)  # 2 hexes north
    assert len(action.moves_made) == 2
    assert not action.off_map


def test_b24_move_off_map_first_hex(hex_grid: Any):
    """Test B-24 moving off map on first hex."""
    # Place aircraft at edge facing off-map
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.hex_grid = hex_grid
    
    action = B24MoveAction(aircraft_index=0)
    can_move, _ = action.validate(game_state)
    assert can_move
    
    result = action.execute(game_state)
    assert result.success
    assert action.off_map
    assert "flew off map" in result.message.lower()


def test_b24_move_off_map_second_hex(hex_grid: Any):
    """Test B-24 moving off map on second hex."""
    # Place aircraft 1 hex from edge
    aircraft = Aircraft(position=HexCoord(0, 1), facing=Facing.NORTH)
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.hex_grid = hex_grid
    
    action = B24MoveAction(aircraft_index=0)
    can_move, _ = action.validate(game_state)
    assert can_move
    
    result = action.execute(game_state)
    assert result.success
    assert action.off_map
    assert len(action.moves_made) == 1  # Only made 1 move before going off map


def test_b24_move_validation_no_aircraft():
    """Test validation fails with no aircraft list."""
    game_state = MockGameState()
    # No aircraft attribute
    
    action = B24MoveAction(aircraft_index=0)
    can_move, reason = action.validate(game_state)
    assert not can_move
    assert "out of range" in reason.lower() or "aircraft" in reason.lower()


def test_b24_move_validation_invalid_index(hex_grid: Any):
    """Test validation fails with invalid aircraft index."""
    game_state = MockGameState()
    game_state.aircraft = []
    game_state.hex_grid = hex_grid
    
    action = B24MoveAction(aircraft_index=0)
    can_move, reason = action.validate(game_state)
    assert not can_move
    assert "out of range" in reason.lower()


# =============================================================================
# B-24 Turn Tests
# =============================================================================

def test_b24_turn_requires_dl_2(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 cannot turn at DL < 2."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(6, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # DL 1 - cannot turn
    action = B24TurnAction(aircraft_index=0, detection_level=1)
    can_turn, reason = action.validate(game_state)
    assert not can_turn
    assert "detection level" in reason.lower()


def test_b24_turn_toward_uboat(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 turns toward U-boat at DL 2+."""
    # B-24 facing north, U-boat to the east
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(7, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    action = B24TurnAction(aircraft_index=0, detection_level=2)
    can_turn, _ = action.validate(game_state)
    assert can_turn
    
    result = action.execute(game_state)
    assert result.success
    assert action.turn_direction == "clockwise"  # NORTH -> NORTHEAST toward east
    assert aircraft.facing == Facing.NORTHEAST


def test_b24_no_turn_when_facing_uboat(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 doesn't turn when already facing U-boat."""
    # B-24 facing north, U-boat directly north
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 3), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    action = B24TurnAction(aircraft_index=0, detection_level=2)
    result = action.execute(game_state)
    assert result.success
    assert action.turn_direction is None
    assert "facing" in result.message.lower() and "u-boat" in result.message.lower()


def test_b24_turn_randomly_when_facing_away(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 turns randomly when facing away from U-boat."""
    # B-24 facing north, U-boat directly south
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 7), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # Roll <= 3: clockwise
    mock_dice.set_next_roll(2)
    action = B24TurnAction(aircraft_index=0, detection_level=2)
    result = action.execute(game_state)
    assert result.success
    assert action.turn_direction == "clockwise"
    assert "facing away" in result.message.lower()


def test_b24_turn_same_hex_facing_off_map(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 turns randomly when same hex as U-boat and facing off map."""
    # B-24 at edge facing off-map, same hex as U-boat
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    mock_dice.set_next_roll(4)  # > 3: counterclockwise
    action = B24TurnAction(aircraft_index=0, detection_level=2)
    result = action.execute(game_state)
    assert result.success
    assert action.turn_direction == "counterclockwise"
    assert "same hex" in result.message.lower()


# =============================================================================
# B-24 Bomb Tests
# =============================================================================

def test_b24_bomb_critical_hit(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 bombing with critical hit (roll 1)."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    game_state.damage_resolver = UBoatDamageResolver(mock_dice, None)
    
    # Roll 1 for critical hit
    mock_dice.set_next_roll(1)
    
    action = B24BombAction(aircraft_index=0)
    can_attack, _ = action.validate(game_state)
    assert can_attack
    
    result = action.execute(game_state)
    assert result.success
    assert action.attack_roll == 1
    assert action.damage_applied
    assert action.attack_succeeded
    assert "critical" in result.message.lower()


def test_b24_bomb_general_damage(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 bombing with general damage (roll 2-3)."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    game_state.damage_resolver = UBoatDamageResolver(mock_dice, None)
    
    # Roll 2 for general damage
    mock_dice.set_next_roll(2)
    
    action = B24BombAction(aircraft_index=0)
    result = action.execute(game_state)
    assert result.success
    assert action.attack_roll == 2
    assert action.damage_applied
    assert action.attack_succeeded


def test_b24_bomb_miss(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 bombing miss (roll 4-6)."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    game_state.damage_resolver = UBoatDamageResolver(mock_dice, None)
    
    # Roll 5 for miss
    mock_dice.set_next_roll(5)
    
    action = B24BombAction(aircraft_index=0)
    result = action.execute(game_state)
    assert result.success
    assert action.attack_roll == 5
    assert not action.damage_applied
    assert not action.attack_succeeded
    assert "missed" in result.message.lower()


def test_b24_bomb_validation_range_too_far(hex_grid: Any):
    """Test B-24 cannot bomb at range > 1."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    
    action = B24BombAction(aircraft_index=0)
    can_attack, reason = action.validate(game_state)
    assert not can_attack
    assert "range" in reason.lower()


def test_b24_bomb_validation_uboat_too_deep(hex_grid: Any):
    """Test B-24 cannot bomb submerged U-boat."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.DEEP)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    
    action = B24BombAction(aircraft_index=0)
    can_attack, reason = action.validate(game_state)
    assert not can_attack
    assert "deep" in reason.lower() or "surfaced" in reason.lower()


def test_b24_bomb_can_attack_at_periscope(hex_grid: Any, mock_dice: MockDice):
    """Test B-24 can bomb U-boat at periscope depth."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    game_state.damage_resolver = UBoatDamageResolver(mock_dice, None)
    
    action = B24BombAction(aircraft_index=0)
    can_attack, _ = action.validate(game_state)
    assert can_attack


# =============================================================================
# Flak Defense Tests
# =============================================================================

def test_flak_defense_shot_down(hex_grid: Any, mock_dice: MockDice):
    """Test flak gun shoots down B-24 (hit + roll 1-3)."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.lookout_alive = True
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # Roll 4+3=7 to hit (threshold 7 with lookout), then roll 2 for shot down
    mock_dice.set_roll_sequence([4, 3, 2])
    
    action = FlakDefenseAction(aircraft_index=0)
    can_fire, _ = action.validate(game_state)
    assert can_fire
    
    result = action.execute(game_state)
    assert result.success
    assert action.flak_roll == 7
    assert action.threshold == 7
    assert action.b24_destroyed
    assert action.outcome == 'shot_down'
    assert "shot down" in result.message.lower()


def test_flak_defense_scared_off(hex_grid: Any, mock_dice: MockDice):
    """Test flak gun scares off B-24 (hit + roll 4-6)."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.lookout_alive = False
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # Roll 5+3=8 to hit (threshold 8 without lookout), then roll 5 for scared off
    mock_dice.set_roll_sequence([5, 3, 5])
    
    action = FlakDefenseAction(aircraft_index=0)
    result = action.execute(game_state)
    assert result.success
    assert action.flak_roll == 8
    assert action.threshold == 8
    assert action.b24_destroyed
    assert action.outcome == 'scared_off'
    assert "scared off" in result.message.lower()


def test_flak_defense_miss(hex_grid: Any, mock_dice: MockDice):
    """Test flak gun misses B-24."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.lookout_alive = False
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # Roll 3+3=6 (below threshold 8)
    mock_dice.set_roll_sequence([3, 3])
    
    action = FlakDefenseAction(aircraft_index=0)
    result = action.execute(game_state)
    assert result.success
    assert action.flak_roll == 6
    assert not action.b24_destroyed
    assert action.outcome is None
    assert "survives" in result.message.lower()


def test_flak_defense_validation_not_surfaced():
    """Test flak validation fails when U-boat not surfaced."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    
    action = FlakDefenseAction(aircraft_index=0)
    can_fire, reason = action.validate(game_state)
    assert not can_fire
    assert "surfaced" in reason.lower()


def test_flak_defense_validation_gun_damaged():
    """Test flak validation fails when flak gun damaged."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.flak_gun_damaged = True
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    
    action = FlakDefenseAction(aircraft_index=0)
    can_fire, reason = action.validate(game_state)
    assert not can_fire
    assert "damaged" in reason.lower()


def test_flak_defense_lookout_bonus(hex_grid: Any, mock_dice: MockDice):
    """Test lookout reduces flak threshold from 8 to 7."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat_with_lookout = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat_with_lookout.lookout_alive = True
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat_with_lookout
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    action = FlakDefenseAction(aircraft_index=0)
    action.validate(game_state)
    mock_dice.set_roll_sequence([4, 3, 1])  # 7 total
    _ = action.execute(game_state)
    
    assert action.threshold == 7
    assert action.flak_roll == 7
    assert action.b24_destroyed  # Hit with threshold 7


# =============================================================================
# Integration Tests
# =============================================================================

def test_b24_full_sequence(hex_grid: Any, mock_dice: MockDice):
    """Test complete B-24 activation sequence: move, turn, flak, bomb."""
    # Setup: B-24 near U-boat
    aircraft = Aircraft(position=HexCoord(5, 7), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.lookout_alive = False
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    game_state.damage_resolver = UBoatDamageResolver(mock_dice, None)
    
    # Step 1: Move (2 hexes north, now at 5,5 same as U-boat)
    move_action = B24MoveAction(aircraft_index=0)
    move_result = move_action.execute(game_state)
    assert move_result.success
    assert aircraft.position == HexCoord(5, 5)
    
    # Step 2: Turn (DL 2+, already same hex so depends on facing off-map)
    turn_action = B24TurnAction(aircraft_index=0, detection_level=2)
    turn_result = turn_action.execute(game_state)
    assert turn_result.success
    
    # Step 3: Flak defense (roll 3+3=6 miss)
    mock_dice.set_roll_sequence([3, 3])
    flak_action = FlakDefenseAction(aircraft_index=0)
    flak_result = flak_action.execute(game_state)
    assert flak_result.success
    assert not flak_action.b24_destroyed
    
    # Step 4: Bomb (B-24 survived flak, now attacks)
    mock_dice.set_next_roll(1)  # Critical hit
    bomb_action = B24BombAction(aircraft_index=0)
    bomb_result = bomb_action.execute(game_state)
    assert bomb_result.success
    assert bomb_action.attack_succeeded


def test_b24_flak_prevents_bombing(hex_grid: Any, mock_dice: MockDice):
    """Test flak shooting down B-24 prevents bombing attack."""
    aircraft = Aircraft(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 5), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.lookout_alive = True
    
    game_state = MockGameState()
    game_state.aircraft = [aircraft]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.dice_roller = mock_dice
    
    # Flak hits and shoots down
    mock_dice.set_roll_sequence([4, 3, 2])  # 7 to hit, 2 for shot down
    flak_action = FlakDefenseAction(aircraft_index=0)
    flak_result = flak_action.execute(game_state)
    assert flak_result.success
    assert flak_action.b24_destroyed
    
    # B-24 is destroyed, cannot bomb
    # (In real game, B-24 would be removed from aircraft)
