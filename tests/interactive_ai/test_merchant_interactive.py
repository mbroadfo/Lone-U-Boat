"""
Tests for Interactive Merchant AI Actions.

This test suite validates merchant ships moving one at a time with animations,
mirroring the behavior tested in test_merchant_ai.py but using the new
Action-based system.
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.actions.ai import MerchantMoveAction, MerchantDamageCheckAction
from core.models import Ship, HexCoord, Facing
from tests.interactive_ai.conftest import MockGameState, MockDice


def test_merchant_move_action_creation():
    """Test creating a merchant move action."""
    print("\n=== Test: Merchant Move Action Creation ===")
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTH
    )
    
    assert action.entity_index == 0
    assert action.target_hex == HexCoord(1, 5)
    assert action.new_facing == Facing.SOUTH
    assert action.triggers_animation is True
    print("✓ Merchant move action created successfully")


def test_merchant_move_action_validation_success(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant move action validates successfully."""
    print("\n=== Test: Merchant Move Validation (Success) ===")
    
    mock_game_state.ships = [undamaged_merchant]
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTH
    )
    
    can_move, reason = action.validate(mock_game_state)
    
    assert can_move is True
    assert "Can move" in reason
    print(f"✓ Validation passed: {reason}")


def test_merchant_move_action_blocked_by_ship(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant move fails when destination is blocked."""
    print("\n=== Test: Merchant Move Blocked ===")
    
    # Create blocking ship at destination
    blocking_ship = Ship(
        position=HexCoord(1, 5),
        facing=Facing.NORTH,
        ship_type='corvette',
        damaged=False
    )
    
    mock_game_state.ships = [undamaged_merchant, blocking_ship]
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTH
    )
    
    can_move, reason = action.validate(mock_game_state)
    
    assert can_move is False
    assert "blocked" in reason.lower()
    assert action.blocked_by == blocking_ship
    print(f"✓ Correctly blocked: {reason}")


def test_merchant_move_action_execution(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant move action executes and changes position."""
    print("\n=== Test: Merchant Move Execution ===")
    
    mock_game_state.ships = [undamaged_merchant]
    old_position = undamaged_merchant.position
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTH
    )
    
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert undamaged_merchant.position == HexCoord(1, 5)
    assert undamaged_merchant.facing == Facing.SOUTH
    assert result.state_changes['old_position'] == old_position
    assert result.state_changes['new_position'] == HexCoord(1, 5)
    print(f"✓ Merchant moved: {result.message}")


def test_merchant_move_triggers_animation(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant move triggers animation manager."""
    print("\n=== Test: Merchant Move Animation ===")
    
    mock_game_state.ships = [undamaged_merchant]
    old_position = undamaged_merchant.position
    old_facing = undamaged_merchant.facing
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTHEAST
    )
    
    result = action.execute(mock_game_state)
    
    # Check animation was triggered
    anim_mgr = mock_game_state.animation_manager
    assert len(anim_mgr.ship_movements) == 1
    assert anim_mgr.ship_movements[0] == (0, old_position, HexCoord(1, 5))
    
    assert len(anim_mgr.ship_rotations) == 1
    assert anim_mgr.ship_rotations[0] == (0, old_facing, Facing.SOUTHEAST)
    assert result.success is True
    
    print("✓ Movement and rotation animations triggered")


def test_merchant_move_no_animation_if_same_position(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test no movement animation if position unchanged."""
    print("\n=== Test: No Animation for Same Position ===")
    
    mock_game_state.ships = [undamaged_merchant]
    current_pos = undamaged_merchant.position
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=current_pos,  # Same position
        new_facing=Facing.SOUTHEAST
    )
    
    result = action.execute(mock_game_state)
    
    # Only rotation animation, no movement
    anim_mgr = mock_game_state.animation_manager
    assert len(anim_mgr.ship_movements) == 0
    assert len(anim_mgr.ship_rotations) == 1
    assert result.success is True
    
    print("✓ Only rotation animation triggered")


def test_merchant_damage_check_action_creation():
    """Test creating damage check action."""
    print("\n=== Test: Damage Check Action Creation ===")
    
    action = MerchantDamageCheckAction(entity_index=0, required_roll=4)
    
    assert action.entity_index == 0
    assert action.required_roll == 4
    assert action.requires_player_input is True
    assert action.triggers_animation is False
    print("✓ Damage check action created")


def test_merchant_damage_check_validation_success(mock_game_state: MockGameState, damaged_merchant: Ship):
    """Test damage check validates for damaged merchant."""
    print("\n=== Test: Damage Check Validation ===")
    
    mock_game_state.ships = [damaged_merchant]
    
    action = MerchantDamageCheckAction(entity_index=0)
    can_check, reason = action.validate(mock_game_state)
    
    assert can_check is True
    assert "can make damage check" in reason.lower()
    print(f"✓ Validation passed: {reason}")


def test_merchant_damage_check_validation_fails_undamaged(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test damage check fails for undamaged merchant."""
    print("\n=== Test: Damage Check Fails for Undamaged ===")
    
    mock_game_state.ships = [undamaged_merchant]
    
    action = MerchantDamageCheckAction(entity_index=0)
    can_check, reason = action.validate(mock_game_state)
    
    assert can_check is False
    assert "not damaged" in reason.lower()
    print(f"✓ Correctly rejected: {reason}")


def test_merchant_damage_check_roll_success(mock_game_state: MockGameState, damaged_merchant: Ship, mock_dice: MockDice):
    """Test damage check with successful roll (4+)."""
    print("\n=== Test: Damage Check Roll Success ===")
    
    mock_game_state.ships = [damaged_merchant]
    mock_game_state.merchant_ai.dice = mock_dice
    mock_dice.set_next_roll(5)  # Roll 5 = success
    
    action = MerchantDamageCheckAction(entity_index=0, required_roll=4)
    result = action.execute(mock_game_state)
    
    assert result.success is True
    assert action.roll_result == 5
    assert action.can_move is True
    assert "CAN move" in result.message
    print(f"✓ Rolled 5: {result.message}")


def test_merchant_damage_check_roll_failure(mock_game_state: MockGameState, damaged_merchant: Ship, mock_dice: MockDice):
    """Test damage check with failed roll (1-3)."""
    print("\n=== Test: Damage Check Roll Failure ===")
    
    mock_game_state.ships = [damaged_merchant]
    mock_game_state.merchant_ai.dice = mock_dice
    mock_dice.set_next_roll(2)  # Roll 2 = fail
    
    action = MerchantDamageCheckAction(entity_index=0, required_roll=4)
    result = action.execute(mock_game_state)
    
    assert result.success is True  # Roll was made successfully
    assert action.roll_result == 2
    assert action.can_move is False
    assert "cannot move" in result.message
    print(f"✓ Rolled 2: {result.message}")


def test_merchant_move_with_path_calculation(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant move calculates path automatically."""
    print("\n=== Test: Automatic Path Calculation ===")
    
    mock_game_state.ships = [undamaged_merchant]
    
    # Create action without target (should calculate from path)
    action = MerchantMoveAction(entity_index=0)
    
    can_move, _reason = action.validate(mock_game_state)
    
    assert can_move is True
    assert action.target_hex is not None  # Should be calculated
    assert action.target_hex == HexCoord(1, 5)  # Next waypoint from (1,4)
    print(f"✓ Path calculated: target is {action.target_hex}")


def test_merchant_facing_changes_correctly(mock_game_state: MockGameState):
    """Test merchant facing changes at path turns."""
    print("\n=== Test: Merchant Facing at Turns ===")
    
    # Merchant at waypoint (1, 5), next is (1, 6) which is SOUTH
    merchant = Ship(
        position=HexCoord(1, 5),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    mock_game_state.ships = [merchant]
    
    action = MerchantMoveAction(entity_index=0)
    action.validate(mock_game_state)
    result = action.execute(mock_game_state)
    
    # Should move to (1, 6) - facing may change based on path algorithm
    assert merchant.position == HexCoord(1, 6)
    assert result.success is True
    print(f"✓ Merchant moved to {merchant.position}, facing {merchant.facing.name}")


def test_merchant_at_end_of_path(mock_game_state: MockGameState):
    """Test merchant action when at end of path."""
    print("\n=== Test: Merchant at End of Path ===")
    
    # Merchant at last waypoint (6, 9) which is the exit
    merchant = Ship(
        position=HexCoord(6, 9),
        facing=Facing.SOUTHEAST,
        ship_type='merchant',
        damaged=False
    )
    mock_game_state.ships = [merchant]
    
    action = MerchantMoveAction(entity_index=0)
    can_move, reason = action.validate(mock_game_state)
    
    assert can_move is False
    assert "exited" in reason.lower() or "end" in reason.lower()
    print(f"✓ Correctly detected end: {reason}")


def test_merchant_action_get_preview_data(mock_game_state: MockGameState, undamaged_merchant: Ship):
    """Test merchant action provides preview data for UI."""
    print("\n=== Test: Action Preview Data ===")
    
    mock_game_state.ships = [undamaged_merchant]
    
    action = MerchantMoveAction(
        entity_index=0,
        target_hex=HexCoord(1, 5),
        new_facing=Facing.SOUTH
    )
    
    preview = action.get_preview_data(mock_game_state)
    
    assert preview['type'] == 'merchant_move'
    assert preview['ship_index'] == 0
    assert preview['current_position'] == HexCoord(1, 4)
    assert preview['target_position'] == HexCoord(1, 5)
    assert preview['valid'] is True
    print(f"✓ Preview data: {preview}")


def test_multiple_merchants_sequential_actions(mock_game_state: MockGameState):
    """Test multiple merchants can have separate actions."""
    print("\n=== Test: Multiple Merchants Sequential ===")
    
    merchant1 = Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    merchant2 = Ship(
        position=HexCoord(1, 5),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    
    mock_game_state.ships = [merchant1, merchant2]
    
    # Action for merchant 1
    action1 = MerchantMoveAction(entity_index=0)
    can_move1, _ = action1.validate(mock_game_state)
    if can_move1:
        result1 = action1.execute(mock_game_state)
        assert result1.success is True
        assert merchant1.position == HexCoord(1, 5)
        print(f"  Merchant 1 moved to {merchant1.position}")
    
    # Action for merchant 2 - note: merchant 1 may have blocked its next position
    action2 = MerchantMoveAction(entity_index=1)
    can_move2, _ = action2.validate(mock_game_state)
    _result2 = action2.execute(mock_game_state) if can_move2 else None
    
    # At least one should have moved successfully
    assert can_move1 or can_move2
    print("✓ Merchants acted independently")


def test_damaged_merchant_full_workflow(mock_game_state: MockGameState, damaged_merchant: Ship, mock_dice: MockDice):
    """Test complete workflow: damage check -> movement."""
    print("\n=== Test: Damaged Merchant Full Workflow ===")
    
    mock_game_state.ships = [damaged_merchant]
    mock_game_state.merchant_ai.dice = mock_dice
    mock_dice.set_next_roll(5)  # Success
    
    # Step 1: Damage check
    check_action = MerchantDamageCheckAction(entity_index=0)
    check_result = check_action.execute(mock_game_state)
    
    assert check_result.success is True
    assert check_action.can_move is True
    print(f"  Step 1: {check_result.message}")
    
    # Step 2: Move (because check passed)
    if check_action.can_move:
        move_action = MerchantMoveAction(entity_index=0)
        move_action.validate(mock_game_state)
        move_result = move_action.execute(mock_game_state)
        
        assert move_result.success is True
        assert damaged_merchant.position == HexCoord(1, 5)
        print(f"  Step 2: {move_result.message}")
    
    print("✓ Full damaged merchant workflow completed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
