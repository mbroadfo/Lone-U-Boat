"""
Tests for AIActionQueue.

This test suite validates the AI action queue manager that sequences
player-executed AI actions during AI phases (solitaire-style gameplay).
"""

import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.models import HexCoord, Facing, Depth, UBoat, Ship
from core.actions.ai.ai_action_queue import AIActionQueue
from core.actions.ai import (
    AIAction,
    MerchantMoveAction, 
    EscortDetectionAction,
    B24MoveAction,
    MerchantVisualAction
)
from tests.interactive_ai.conftest import MockGameState, MockDice


# ============================================================================
# BASIC QUEUE OPERATIONS
# ============================================================================

def test_queue_initialization():
    """Test creating empty queue."""
    queue = AIActionQueue()
    
    assert queue.is_empty()
    assert queue.is_exhausted()
    assert queue.total_count() == 0
    assert queue.remaining_count() == 0
    assert queue.current_action() is None
    assert len(queue) == 0


def test_add_single_action(hex_grid: Any):
    """Test adding one action to queue."""
    queue = AIActionQueue()
    
    waypoint = HexCoord(5, 7)
    action = MerchantMoveAction(entity_index=0, target_hex=waypoint)
    
    queue.add(action)
    
    assert not queue.is_empty()
    assert queue.total_count() == 1
    assert queue.remaining_count() == 1
    assert queue.current_action() == action
    assert len(queue) == 1


def test_add_multiple_actions_individually(hex_grid: Any):
    """Test adding multiple actions one at a time."""
    queue = AIActionQueue()
    
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    action2 = MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8))
    action3 = EscortDetectionAction(ship_index=2, current_detection_level=0)
    
    queue.add(action1)
    queue.add(action2)
    queue.add(action3)
    
    assert queue.total_count() == 3
    assert queue.remaining_count() == 3
    assert queue.current_action() == action1


def test_add_multiple_actions_at_once(hex_grid: Any):
    """Test adding list of actions."""
    queue = AIActionQueue()
    
    actions: list[AIAction] = [
        MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)),
        MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8)),
        EscortDetectionAction(ship_index=2, current_detection_level=0)
    ]
    
    queue.add_multiple(actions)
    
    assert queue.total_count() == 3
    assert queue.remaining_count() == 3


# ============================================================================
# QUEUE NAVIGATION
# ============================================================================

def test_next_advances_queue():
    """Test next() moves to next action."""
    queue = AIActionQueue()
    
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    action2 = MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8))
    
    queue.add(action1)
    queue.add(action2)
    
    assert queue.current_action() == action1
    assert queue.remaining_count() == 2
    
    has_more = queue.next()
    
    assert has_more is True
    assert queue.current_action() == action2
    assert queue.remaining_count() == 1


def test_next_at_end_returns_false():
    """Test next() returns False when queue exhausted."""
    queue = AIActionQueue()
    action = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    queue.add(action)
    
    has_more = queue.next()
    
    assert has_more is False
    assert queue.is_exhausted()
    assert queue.current_action() is None


def test_peek_next_without_advancing():
    """Test peek_next() shows next action without moving forward."""
    queue = AIActionQueue()
    
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    action2 = MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8))
    
    queue.add(action1)
    queue.add(action2)
    
    next_action = queue.peek_next()
    
    assert next_action == action2
    assert queue.current_action() == action1  # Current didn't change
    assert queue.remaining_count() == 2  # Count didn't change


def test_peek_next_at_last_returns_none():
    """Test peek_next() returns None when at last action."""
    queue = AIActionQueue()
    action = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    queue.add(action)
    
    assert queue.peek_next() is None


# ============================================================================
# EXECUTION
# ============================================================================

def test_execute_current_merchant_move(hex_grid: Any):
    """Test executing a merchant move action from queue."""
    game_state = MockGameState()
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    game_state.ships = [tanker]
    game_state.hex_grid = hex_grid
    
    queue = AIActionQueue()
    action = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    queue.add(action)
    
    result = queue.execute_current(game_state)
    
    assert result is not None
    assert result.success
    assert tanker.position == HexCoord(5, 7)


def test_execute_current_returns_none_when_exhausted():
    """Test execute_current() returns None when no current action."""
    game_state = MockGameState()
    queue = AIActionQueue()
    
    result = queue.execute_current(game_state)
    
    assert result is None


def test_execution_history_tracking(hex_grid: Any):
    """Test that execution history is recorded."""
    game_state = MockGameState()
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    game_state.ships = [tanker]
    game_state.hex_grid = hex_grid
    
    queue = AIActionQueue()
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 6))
    action2 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    queue.add(action1)
    queue.add(action2)
    
    result1 = queue.execute_current(game_state)
    queue.next()
    result2 = queue.execute_current(game_state)
    
    history = queue.get_execution_history()
    
    assert len(history) == 2
    assert history[0] == result1
    assert history[1] == result2


def test_execute_all_runs_sequence(hex_grid: Any, mock_dice: MockDice):
    """Test execute_all() runs all actions in order."""
    game_state = MockGameState()
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 8), facing=Facing.SOUTH)
    u_boat = UBoat(position=HexCoord(5, 10), facing=Facing.NORTH, depth=Depth.MEDIUM)
    
    game_state.ships = [tanker, corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    queue = AIActionQueue()
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(EscortDetectionAction(ship_index=1, current_detection_level=0))
    
    mock_dice.set_roll_sequence([6])  # Detection succeeds
    
    results = queue.execute_all(game_state)
    
    assert len(results) == 2
    assert results[0].success  # Merchant moved
    assert results[1].success  # Detection attempted
    assert tanker.position == HexCoord(5, 7)
    assert game_state.detection_level == 1  # Detection succeeded


# ============================================================================
# QUEUE MANAGEMENT
# ============================================================================

def test_clear_resets_queue():
    """Test clear() empties queue and resets state."""
    queue = AIActionQueue()
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8)))
    queue.next()
    
    queue.clear()
    
    assert queue.is_empty()
    assert queue.total_count() == 0
    assert queue.remaining_count() == 0
    assert queue.current_action() is None
    assert len(queue.get_execution_history()) == 0


def test_reset_to_start_preserves_actions(hex_grid: Any):
    """Test reset_to_start() rewinds without clearing."""
    game_state = MockGameState()
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    game_state.ships = [tanker]
    game_state.hex_grid = hex_grid
    
    queue = AIActionQueue()
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 6))
    action2 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    queue.add(action1)
    queue.add(action2)
    
    # Execute and advance
    queue.execute_current(game_state)
    queue.next()
    
    assert queue.remaining_count() == 1
    
    # Reset
    queue.reset_to_start()
    
    assert queue.total_count() == 2
    assert queue.remaining_count() == 2
    assert queue.current_action() == action1
    assert len(queue.get_execution_history()) == 0


def test_get_all_actions_returns_copy():
    """Test get_all_actions() returns independent copy."""
    queue = AIActionQueue()
    action1 = MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7))
    action2 = MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8))
    queue.add(action1)
    queue.add(action2)
    
    actions = queue.get_all_actions()
    
    assert len(actions) == 2
    assert actions[0] == action1
    assert actions[1] == action2
    
    # Modify copy shouldn't affect queue
    actions.append(MerchantMoveAction(entity_index=2, target_hex=HexCoord(7, 9)))
    assert queue.total_count() == 2  # Original unchanged


# ============================================================================
# PROGRESS TRACKING
# ============================================================================

def test_get_progress_empty_queue():
    """Test progress info for empty queue."""
    queue = AIActionQueue()
    
    progress = queue.get_progress()
    
    assert progress['current_index'] == 0
    assert progress['total_count'] == 0
    assert progress['remaining_count'] == 0
    assert progress['completed_count'] == 0
    assert progress['progress_percent'] == 100
    assert progress['is_exhausted'] is True
    assert progress['is_empty'] is True


def test_get_progress_partial_completion():
    """Test progress info during execution."""
    queue = AIActionQueue()
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8)))
    queue.add(MerchantMoveAction(entity_index=2, target_hex=HexCoord(7, 9)))
    
    # Execute first action
    queue.next()
    
    progress = queue.get_progress()
    
    assert progress['current_index'] == 1
    assert progress['total_count'] == 3
    assert progress['remaining_count'] == 2
    assert progress['completed_count'] == 1
    assert progress['progress_percent'] == 33
    assert progress['is_exhausted'] is False
    assert progress['is_empty'] is False


def test_get_progress_fully_completed():
    """Test progress info when all actions executed."""
    queue = AIActionQueue()
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8)))
    
    # Execute all
    queue.next()
    queue.next()
    
    progress = queue.get_progress()
    
    assert progress['current_index'] == 2
    assert progress['total_count'] == 2
    assert progress['remaining_count'] == 0
    assert progress['completed_count'] == 2
    assert progress['progress_percent'] == 100
    assert progress['is_exhausted'] is True
    assert progress['is_empty'] is False


# ============================================================================
# INTEGRATION WITH REAL ACTIONS
# ============================================================================

def test_mixed_action_types_sequence(hex_grid: Any, mock_dice: MockDice):
    """Test queue with different action types (merchant, escort, B24)."""
    game_state = MockGameState()
    
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    corvette = Ship(ship_type='corvette', position=HexCoord(6, 8), facing=Facing.SOUTH)
    u_boat = UBoat(position=HexCoord(5, 10), facing=Facing.NORTH, depth=Depth.SURFACED)
    
    game_state.ships = [tanker, corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    game_state.dice_roller = mock_dice
    game_state.aircraft = [Ship(ship_type='b24', position=HexCoord(4, 8), facing=Facing.NORTHEAST)]
    
    queue = AIActionQueue()
    
    # Mix of different AI action types
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(EscortDetectionAction(ship_index=1, current_detection_level=0))
    queue.add(B24MoveAction(aircraft_index=0))
    queue.add(MerchantVisualAction(ship_index=0, current_detection_level=3))
    
    mock_dice.set_roll_sequence([1])  # Detection succeeds (threshold 2 for surfaced + sonar)
    
    # Execute all in sequence
    results = queue.execute_all(game_state)
    
    assert len(results) == 4
    assert all(result.success for result in results)
    
    # Verify final progress
    progress = queue.get_progress()
    assert progress['completed_count'] == 4
    assert progress['is_exhausted'] is True


def test_queue_repr():
    """Test string representation for debugging."""
    queue = AIActionQueue()
    queue.add(MerchantMoveAction(entity_index=0, target_hex=HexCoord(5, 7)))
    queue.add(MerchantMoveAction(entity_index=1, target_hex=HexCoord(6, 8)))
    queue.next()
    
    repr_str = repr(queue)
    
    assert 'AIActionQueue' in repr_str
    assert 'total=2' in repr_str
    assert 'current=1' in repr_str
    assert 'remaining=1' in repr_str


