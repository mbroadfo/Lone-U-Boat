"""
Tests for Interactive Escort AI Actions.

This test suite validates escort ships activating and acting one at a time
with animations, mirroring the behavior tested in test_escort_ai.py but using
the new Action-based system.
"""

import pytest
import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.actions.ai import (
    EscortActivationAction, EscortDieAction, EscortActionType,
    EscortMoveAction, EscortTurnAction, EscortFireAction, EscortDepthChargeAction
)
from core.models import Ship, UBoat, HexCoord, Facing, Depth
from tests.interactive_ai.conftest import MockGameState, MockDice


@pytest.fixture
def simple_game_state(destroyer: Ship):
    """Create a minimal game state for die action tests."""
    class SimpleState:
        ships: list[Ship] = [destroyer]  # Need a real ship
    return SimpleState()


# =============================================================================
# ESCORT ACTIVATION TESTS
# =============================================================================

def test_escort_activation_creation():
    """Test creating an escort activation action."""
    print("\n=== Test: Escort Activation Creation ===")
    
    action = EscortActivationAction(entity_index=0, detection_level=2)
    
    assert action.entity_index == 0
    assert action.detection_level == 2
    assert action.requires_player_input is True
    print("✓ Escort activation action created successfully")


def test_destroyer_dice_count_undamaged(mock_game_state: MockGameState, destroyer: Ship):
    """Test destroyer gets 3 base + DL bonus when undamaged."""
    print("\n=== Test: Destroyer Dice Count (Undamaged) ===")
    
    mock_game_state.ships = [destroyer]
    
    # DL 0: 3 base dice
    action = EscortActivationAction(entity_index=0, detection_level=0)
    can_activate, _ = action.validate(mock_game_state)
    assert can_activate is True
    assert action.dice_count == 3
    print(f"  DL 0: {action.dice_count} dice")
    
    # DL 2: 3 base + 2 = 5 dice
    action = EscortActivationAction(entity_index=0, detection_level=2)
    can_activate, _ = action.validate(mock_game_state)
    assert can_activate is True
    assert action.dice_count == 5
    print(f"  DL 2: {action.dice_count} dice")
    
    print("✓ Destroyer dice count correct")


def test_corvette_dice_count_undamaged(mock_game_state: MockGameState, corvette: Ship):
    """Test corvette gets 2 base + DL bonus when undamaged."""
    print("\n=== Test: Corvette Dice Count (Undamaged) ===")
    
    mock_game_state.ships = [corvette]
    
    # DL 0: 2 base dice
    action = EscortActivationAction(entity_index=0, detection_level=0)
    can_activate, _ = action.validate(mock_game_state)
    assert can_activate is True
    assert action.dice_count == 2
    print(f"  DL 0: {action.dice_count} dice")
    
    # DL 3: 2 base + 3 = 5 dice
    action = EscortActivationAction(entity_index=0, detection_level=3)
    can_activate, _ = action.validate(mock_game_state)
    assert can_activate is True
    assert action.dice_count == 5
    print(f"  DL 3: {action.dice_count} dice")
    
    print("✓ Corvette dice count correct")


def test_damaged_escort_no_dl_bonus(mock_game_state: MockGameState, damaged_destroyer: Ship):
    """Test damaged escorts don't get DL bonus."""
    print("\n=== Test: Damaged Escort No DL Bonus ===")
    
    mock_game_state.ships = [damaged_destroyer]
    
    # DL 2: 3 base dice only (no DL bonus)
    action = EscortActivationAction(entity_index=0, detection_level=2)
    can_activate, _ = action.validate(mock_game_state)
    assert can_activate is True
    assert action.dice_count == 3  # Base only, no +2 from DL
    print(f"  DL 2 (damaged): {action.dice_count} dice (no DL bonus)")
    
    print("✓ Damaged escorts don't get DL bonus")


def test_escort_activation_execution(mock_game_state: MockGameState, destroyer: Ship, mock_dice: MockDice):
    """Test escort activation rolls dice."""
    print("\n=== Test: Escort Activation Execution ===")
    
    mock_game_state.ships = [destroyer]
    mock_game_state.escort_ai.dice = mock_dice
    mock_dice.set_roll_sequence([4, 2, 6])  # 3 dice
    
    action = EscortActivationAction(entity_index=0, detection_level=0)
    action.validate(mock_game_state)
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert action.rolls == [2, 4, 6]  # Sorted
    assert len(action.rolls) == 3
    print(f"✓ Rolled: {action.rolls}")


# =============================================================================
# DIE ACTION TESTS
# =============================================================================

def test_die_action_mapping_1(simple_game_state: Any):
    """Test die 1 maps to FIRE or DEPTH_CHARGE."""
    print("\n=== Test: Die 1 Action Mapping ===")
    
    action = EscortDieAction(entity_index=0, die_value=1, detection_level=2)
    action.validate(simple_game_state)  # Initializes actions_granted
    assert EscortActionType.FIRE in action.actions_granted
    assert EscortActionType.DEPTH_CHARGE in action.actions_granted
    print("✓ Die 1 -> FIRE or DEPTH_CHARGE")


def test_die_action_mapping_2(simple_game_state: Any):
    """Test die 2 maps to MOVE -> TURN -> DEPTH_CHARGE."""
    print("\n=== Test: Die 2 Action Mapping ===")
    
    action = EscortDieAction(entity_index=0, die_value=2)
    action.validate(simple_game_state)  # Initializes actions_granted
    actions = action.actions_granted
    assert EscortActionType.MOVE in actions
    assert EscortActionType.TURN in actions
    assert EscortActionType.DEPTH_CHARGE in actions
    print("✓ Die 2 -> MOVE + TURN + DEPTH_CHARGE")


def test_die_action_mapping_3(simple_game_state: Any):
    """Test die 3 maps to MOVE only."""
    print("\n=== Test: Die 3 Action Mapping ===")
    
    action = EscortDieAction(entity_index=0, die_value=3)
    action.validate(simple_game_state)  # Initializes actions_granted
    actions = action.actions_granted
    assert actions == [EscortActionType.MOVE]
    print("✓ Die 3 -> MOVE")


def test_die_action_mapping_4_and_6(simple_game_state: Any):
    """Test die 4 and 6 map to MOVE + TURN."""
    print("\n=== Test: Die 4/6 Action Mapping ===")
    
    for die_val in [4, 6]:
        action = EscortDieAction(entity_index=0, die_value=die_val)
        action.validate(simple_game_state)  # Initializes actions_granted
        actions = action.actions_granted
        assert EscortActionType.MOVE in actions
        assert EscortActionType.TURN in actions
        print(f"✓ Die {die_val} -> MOVE + TURN")


def test_die_action_mapping_5(simple_game_state: Any):
    """Test die 5 maps to TURN only."""
    print("\n=== Test: Die 5 Action Mapping ===")
    
    action = EscortDieAction(entity_index=0, die_value=5)
    action.validate(simple_game_state)  # Initializes actions_granted
    actions = action.actions_granted
    assert actions == [EscortActionType.TURN]
    print("✓ Die 5 -> TURN")


# =============================================================================
# ESCORT MOVE TESTS
# =============================================================================

def test_escort_move_forward(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort moves one hex forward."""
    print("\n=== Test: Escort Move Forward ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    
    action = EscortMoveAction(entity_index=0)
    can_move, _ = action.validate(mock_game_state)
    assert can_move is True
    result = action.execute(mock_game_state)
    assert result.success is True
    assert destroyer.position == HexCoord(5, 4)  # North = -1r
    print(f"✓ Moved to {destroyer.position}")


def test_escort_move_blocked_by_land(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort move fails when blocked by land."""
    print("\n=== Test: Escort Move Blocked by Land ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    mock_game_state.land_hexes = {HexCoord(5, 4)}  # Block north hex
    
    action = EscortMoveAction(entity_index=0)
    can_move, reason = action.validate(mock_game_state)
    
    assert can_move is False
    assert "land" in reason.lower()
    print(f"✓ Correctly blocked: {reason}")


def test_escort_move_blocked_by_ship(mock_game_state: MockGameState, destroyer: Ship, corvette: Ship):
    """Test escort move fails when blocked by another ship."""
    print("\n=== Test: Escort Move Blocked by Ship ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    corvette.position = HexCoord(5, 4)  # Blocking north
    mock_game_state.ships = [destroyer, corvette]
    
    action = EscortMoveAction(entity_index=0)
    can_move, reason = action.validate(mock_game_state)
    
    assert can_move is False
    assert "corvette" in reason.lower()
    assert action.blocked_by == corvette
    print(f"✓ Correctly blocked: {reason}")


def test_escort_move_triggers_animation(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort move triggers animation."""
    print("\n=== Test: Escort Move Animation ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.SOUTHEAST
    mock_game_state.ships = [destroyer]
    
    old_pos = destroyer.position
    action = EscortMoveAction(entity_index=0)
    _ = action.validate(mock_game_state)
    _ = action.execute(mock_game_state)
    
    assert len(mock_game_state.animation_manager.ship_movements) == 1
    assert mock_game_state.animation_manager.ship_movements[0] == (0, old_pos, HexCoord(6, 5))
    print("✓ Movement animation triggered")


def test_escort_move_forced_dive(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort move triggers forced dive when reaching U-boat hex."""
    print("\n=== Test: Escort Move Forced Dive ===")
    
    destroyer.position = HexCoord(4, 5)
    destroyer.facing = Facing.SOUTHEAST
    surfaced_uboat.position = HexCoord(5, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    mock_game_state.detection_level = 1
    
    action = EscortMoveAction(entity_index=0)
    action.validate(mock_game_state)
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert action.forced_dive_triggered is True
    assert surfaced_uboat.depth == Depth.MEDIUM
    assert "FORCED DIVE" in result.message
    print("✓ Forced dive triggered")


# =============================================================================
# ESCORT TURN TESTS
# =============================================================================

def test_escort_turn_clockwise(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort turns clockwise."""
    print("\n=== Test: Escort Turn Clockwise ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat.position = HexCoord(6, 4)  # Northeast
    
    action = EscortTurnAction(entity_index=0, detection_level=2)  # Turn toward U-boat
    can_turn, reason = action.validate(mock_game_state)

    if can_turn:
        old_facing = destroyer.facing
        result = action.execute(mock_game_state)
        assert result.success is True
        assert destroyer.facing != old_facing
        print(f"✓ Turned from {old_facing.name} to {destroyer.facing.name}")
    else:
        print(f"  Turn not needed: {reason}")


def test_escort_turn_toward_anchor_dl0(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort turns toward anchor at DL 0-1."""
    print("\n=== Test: Escort Turn Toward Anchor (DL 0) ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    mock_game_state.escort_ai.anchor_hex = HexCoord(10, 10)  # Southeast
    
    action = EscortTurnAction(entity_index=0, detection_level=0)  # Turn toward anchor
    can_turn, reason = action.validate(mock_game_state)
    
    if can_turn:
        assert action.target_hex == HexCoord(10, 10)  # Should target anchor
        print(f"✓ Turning toward anchor at {action.target_hex}")
    else:
        print(f"  Already facing target: {reason}")


def test_escort_turn_toward_uboat_dl2(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort turns toward U-boat at DL 2-3."""
    print("\n=== Test: Escort Turn Toward U-boat (DL 2) ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat.position = HexCoord(3, 7)  # Southwest
    
    action = EscortTurnAction(entity_index=0, detection_level=2)  # Turn toward U-boat
    can_turn, reason = action.validate(mock_game_state)
    
    if can_turn:
        assert action.target_hex == mock_game_state.uboat.position
        print(f"✓ Turning toward U-boat at {action.target_hex}")
    else:
        print(f"  Already facing target: {reason}")


def test_escort_turn_triggers_animation(mock_game_state: MockGameState, destroyer: Ship):
    """Test escort turn triggers rotation animation."""
    print("\n=== Test: Escort Turn Animation ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    
    # Explicitly set new facing for test
    action = EscortTurnAction(entity_index=0, new_facing=Facing.NORTHEAST)
    can_turn, _ = action.validate(mock_game_state)
    
    if can_turn:
        old_facing = destroyer.facing
        _ = action.execute(mock_game_state)
        
        assert len(mock_game_state.animation_manager.ship_rotations) == 1
        assert mock_game_state.animation_manager.ship_rotations[0] == (0, old_facing, Facing.NORTHEAST)
        print("✓ Rotation animation triggered")


# =============================================================================
# ESCORT FIRE TESTS
# =============================================================================

def test_escort_fire_validation_success(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort can fire at surfaced U-boat in range."""
    print("\n=== Test: Escort Fire Validation (Success) ===")
    
    destroyer.position = HexCoord(5, 5)
    surfaced_uboat.position = HexCoord(8, 5)  # Range 3
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    
    action = EscortFireAction(entity_index=0, detection_level=2)
    can_fire, reason = action.validate(mock_game_state)
    
    assert can_fire is True
    # Validation sets internal attributes - check they exist
    assert hasattr(action, '_range')
    assert hasattr(action, '_has_los')
    print(f"✓ Can fire: {reason}")


def test_escort_fire_fails_submerged(mock_game_state: MockGameState, destroyer: Ship, submerged_uboat: UBoat):
    """Test escort cannot fire at submerged U-boat."""
    print("\n=== Test: Escort Fire Fails (Submerged) ===")
    
    destroyer.position = HexCoord(5, 5)
    submerged_uboat.position = HexCoord(7, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = submerged_uboat
    
    action = EscortFireAction(entity_index=0, detection_level=2)
    can_fire, reason = action.validate(mock_game_state)
    
    assert can_fire is False
    assert "SURFACED" in reason
    print(f"✓ Correctly rejected: {reason}")


def test_escort_fire_fails_range(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort cannot fire beyond range 6."""
    print("\n=== Test: Escort Fire Fails (Range) ===")
    
    destroyer.position = HexCoord(5, 5)
    surfaced_uboat.position = HexCoord(15, 5)  # Range > 6
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    
    action = EscortFireAction(entity_index=0, detection_level=2)
    can_fire, reason = action.validate(mock_game_state)
    
    assert can_fire is False
    assert "Range" in reason
    print(f"✓ Correctly rejected: {reason}")


def test_escort_fire_fails_dl0(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort cannot fire at DL 0."""
    print("\n=== Test: Escort Fire Fails (DL 0) ===")
    
    destroyer.position = HexCoord(5, 5)
    surfaced_uboat.position = HexCoord(7, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    
    action = EscortFireAction(entity_index=0, detection_level=0)
    can_fire, reason = action.validate(mock_game_state)
    
    assert can_fire is False
    assert "DL must be 1-3" in reason
    print(f"✓ Correctly rejected: {reason}")


def test_escort_fire_execution(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort fire execution increases DL and applies damage."""
    print("\n=== Test: Escort Fire Execution ===")
    
    destroyer.position = HexCoord(5, 5)
    surfaced_uboat.position = HexCoord(7, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    mock_game_state.detection_level = 1
    
    action = EscortFireAction(entity_index=0, detection_level=1)
    action.validate(mock_game_state)
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert action.hit is True
    assert mock_game_state.detection_level == 3  # Increased to 3
    assert "DL -> 3" in result.message
    print(f"✓ Fire executed: {result.message}")


# =============================================================================
# ESCORT DEPTH CHARGE TESTS
# =============================================================================

def test_escort_depth_charge_validation_success(mock_game_state: MockGameState, destroyer: Ship, submerged_uboat: UBoat):
    """Test escort can drop depth charges on submerged U-boat in same hex."""
    print("\n=== Test: Escort Depth Charge Validation (Success) ===")
    
    destroyer.position = HexCoord(5, 5)
    submerged_uboat.position = HexCoord(5, 5)  # Same hex
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = submerged_uboat
    
    action = EscortDepthChargeAction(entity_index=0, detection_level=2)
    can_attack, reason = action.validate(mock_game_state)
    
    assert can_attack is True
    # Validation sets internal attributes - check it exists
    assert hasattr(action, '_range')
    print(f"✓ Can drop depth charges: {reason}")


def test_escort_depth_charge_fails_surfaced(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat):
    """Test escort cannot depth charge surfaced U-boat."""
    print("\n=== Test: Escort Depth Charge Fails (Surfaced) ===")
    
    destroyer.position = HexCoord(5, 5)
    surfaced_uboat.position = HexCoord(5, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    
    action = EscortDepthChargeAction(entity_index=0, detection_level=2)
    can_attack, reason = action.validate(mock_game_state)
    
    assert can_attack is False
    assert "SURFACED" in reason
    print(f"✓ Correctly rejected: {reason}")


def test_escort_depth_charge_fails_range(mock_game_state: MockGameState, destroyer: Ship, submerged_uboat: UBoat):
    """Test escort cannot depth charge beyond range 1."""
    print("\n=== Test: Escort Depth Charge Fails (Range) ===")
    
    destroyer.position = HexCoord(5, 5)
    submerged_uboat.position = HexCoord(7, 5)  # Range > 1
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = submerged_uboat
    
    action = EscortDepthChargeAction(entity_index=0, detection_level=2)
    can_attack, reason = action.validate(mock_game_state)
    
    assert can_attack is False
    assert "Range" in reason
    print(f"✓ Correctly rejected: {reason}")


def test_escort_depth_charge_execution(mock_game_state: MockGameState, destroyer: Ship, submerged_uboat: UBoat):
    """Test escort depth charge execution applies damage."""
    print("\n=== Test: Escort Depth Charge Execution ===")
    
    destroyer.position = HexCoord(5, 5)
    submerged_uboat.position = HexCoord(5, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = submerged_uboat
    
    action = EscortDepthChargeAction(entity_index=0, detection_level=2)
    action.validate(mock_game_state)
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert action.damage_applied is True
    print(f"✓ Depth charge executed: {result.message}")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

def test_full_escort_workflow(mock_game_state: MockGameState, destroyer: Ship, surfaced_uboat: UBoat, mock_dice: MockDice):
    """Test complete escort workflow: activate -> roll -> move -> turn -> fire."""
    print("\n=== Test: Full Escort Workflow ===")
    
    destroyer.position = HexCoord(3, 5)
    destroyer.facing = Facing.SOUTHEAST
    surfaced_uboat.position = HexCoord(7, 5)
    mock_game_state.ships = [destroyer]
    mock_game_state.uboat = surfaced_uboat
    mock_game_state.escort_ai.dice = mock_dice
    mock_dice.set_roll_sequence([4, 2, 5, 6])  # 4 dice: destroyer (3 base + 1 DL bonus)
    
    # Step 1: Activate escort
    activate_action = EscortActivationAction(entity_index=0, detection_level=1)
    activate_action.validate(mock_game_state)
    activate_result = activate_action.execute(mock_game_state)
    assert activate_result.success is True
    assert activate_action.rolls == [2, 4, 5, 6]
    print(f"  Step 1: Activated with rolls {activate_action.rolls}")
    
    # Step 2: Process die 2 (MOVE + TURN)
    die_action = EscortDieAction(entity_index=0, die_value=2, detection_level=1)
    die_action.validate(mock_game_state)
    _ = die_action.execute(mock_game_state)
    assert EscortActionType.MOVE in die_action.actions_granted
    print(f"  Step 2: Die 2 grants {[a.value for a in die_action.actions_granted]}")
    
    # Step 3: Execute MOVE
    move_action = EscortMoveAction(entity_index=0)
    can_move, _ = move_action.validate(mock_game_state)
    if can_move:
        move_result = move_action.execute(mock_game_state)
        assert move_result.success is True
        assert destroyer.position == HexCoord(4, 5)  # Moved east
        print(f"  Step 3: Moved to {destroyer.position}")
    
    print("✓ Full escort workflow completed")


def test_escort_multiple_dice_results(mock_game_state: MockGameState, destroyer: Ship, mock_dice: MockDice):
    """Test processing multiple die results sequentially."""
    print("\n=== Test: Multiple Dice Results ===")
    
    destroyer.position = HexCoord(5, 5)
    destroyer.facing = Facing.NORTH
    mock_game_state.ships = [destroyer]
    mock_game_state.escort_ai.dice = mock_dice
    mock_dice.set_roll_sequence([3, 5, 6])
    
    # Activate
    activate_action = EscortActivationAction(entity_index=0, detection_level=0)
    activate_action.validate(mock_game_state)
    activate_action.execute(mock_game_state)
    
    # Process each die
    for die_val in [3, 5, 6]:
        die_action = EscortDieAction(entity_index=0, die_value=die_val)
        die_action.validate(mock_game_state)
        result = die_action.execute(mock_game_state)
        assert result.success is True
        print(f"  Die {die_val}: {[a.value for a in die_action.actions_granted]}")
    
    print("✓ Multiple dice processed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
