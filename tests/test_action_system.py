"""
Tests for Action System (Phase 3.1).

Run with: python tests/test_action_system.py
"""

import sys
from typing import Dict, Any
sys.path.insert(0, '.')

from core.actions import Action, ActionResult, ActionQueue
from core.models import HexCoord, UBoat, Depth, Facing


# Mock game state for testing
class MockGameState:
    """Minimal game state for testing actions."""
    def __init__(self):
        self.u_boat = UBoat(
            position=HexCoord(5, 5),
            facing=Facing.NORTH,
            depth=Depth.SURFACED
        )
        self.ships = []
        self.current_phase = 1


# Mock action for testing
class MockAction(Action):
    """Simple test action."""
    
    def __init__(self, cost: int = 2, will_fail: bool = False):
        super().__init__()
        self._cost = cost
        self._will_fail = will_fail
        self._executed = False
    
    def get_cost(self, u_boat: UBoat) -> int:
        return self._cost
    
    def validate(self, game_state: Any) -> tuple[bool, str]:
        if self._will_fail:
            return False, "Mock validation failure"
        return True, ""
    
    def execute(self, game_state: Any) -> ActionResult:
        self._executed = True
        return ActionResult(
            success=not self._will_fail,
            message="Mock action executed",
            ap_spent=self._cost,
            state_changes={"executed": True}
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        return {"type": "mock", "cost": self._cost}
    
    def get_description(self) -> str:
        return f"MockAction({self._cost} AP)"


def create_test_game_state():
    """Create minimal game state for testing."""
    return MockGameState()


def test_action_result():
    """Test ActionResult creation and display."""
    print("\n=== Testing ActionResult ===")
    
    result = ActionResult(
        success=True,
        message="Action completed successfully",
        ap_spent=3,
        state_changes={"position": "changed"}
    )
    
    assert result.success, "Result should be successful"
    assert result.ap_spent == 3, "Should track AP spent"
    assert "position" in result.state_changes, "Should track state changes"
    
    result_str = str(result)
    print(f"Success result: {result_str}")
    assert "✓" in result_str, "Should show success checkmark"
    
    # Failed result
    failed = ActionResult(
        success=False,
        message="Action failed",
        ap_spent=0,
        state_changes={}
    )
    
    failed_str = str(failed)
    print(f"Failed result: {failed_str}")
    assert "✗" in failed_str, "Should show failure marker"
    
    print("✅ ActionResult tests passed!\n")


def test_mock_action():
    """Test mock action implementation."""
    print("\n=== Testing Mock Action ===")
    
    game_state = create_test_game_state()
    action = MockAction(cost=2)
    
    # Test cost
    cost = action.get_cost(game_state.u_boat)
    print(f"Action cost: {cost}")
    assert cost == 2, "Should return correct cost"
    
    # Test validation
    can_perform, reason = action.validate(game_state)
    print(f"Validation: {can_perform}, reason: '{reason}'")
    assert can_perform, "Should validate successfully"
    
    # Test preview
    preview = action.get_preview_data(game_state)
    print(f"Preview data: {preview}")
    assert preview["type"] == "mock", "Should return preview data"
    
    # Test execution
    result = action.execute(game_state)
    print(f"Execution result: {result}")
    assert result.success, "Should execute successfully"
    assert action._executed, "Should mark as executed"  # type: ignore[reportPrivateUsage]
    
    # Test failed action
    failed_action = MockAction(will_fail=True)
    can_perform, reason = failed_action.validate(game_state)
    print(f"Failed validation: {can_perform}, reason: '{reason}'")
    assert not can_perform, "Should fail validation"
    
    print("✅ Mock action tests passed!\n")


def test_action_queue_basic():
    """Test basic action queue operations."""
    print("\n=== Testing Action Queue Basic ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=10)
    
    # Empty queue
    assert queue.is_empty, "Queue should start empty"
    assert len(queue) == 0, "Length should be 0"
    assert queue.get_total_cost(game_state) == 0, "Cost should be 0"
    assert queue.get_remaining_ap(game_state) == 10, "Should have full AP"
    
    # Add actions
    action1 = MockAction(cost=2)
    success, msg = queue.add_action(action1, game_state)
    print(f"Add action 1: {success}, {msg}")
    assert success, "Should add action successfully"
    assert len(queue) == 1, "Should have 1 action"
    assert queue.get_total_cost(game_state) == 2, "Cost should be 2"
    assert queue.get_remaining_ap(game_state) == 8, "Should have 8 AP remaining"
    
    action2 = MockAction(cost=3)
    success, msg = queue.add_action(action2, game_state)
    print(f"Add action 2: {success}, {msg}")
    assert success, "Should add second action"
    assert len(queue) == 2, "Should have 2 actions"
    assert queue.get_total_cost(game_state) == 5, "Cost should be 5"
    
    # Get summary
    summary = queue.get_action_summary(game_state)
    print(f"Queue summary: {summary}")
    assert len(summary) == 2, "Should have 2 action summaries"
    
    print("✅ Action queue basic tests passed!\n")


def test_action_queue_undo():
    """Test action queue undo functionality."""
    print("\n=== Testing Action Queue Undo ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=10)
    
    # Add multiple actions
    queue.add_action(MockAction(cost=2), game_state)
    queue.add_action(MockAction(cost=3), game_state)
    queue.add_action(MockAction(cost=1), game_state)
    
    assert len(queue) == 3, "Should have 3 actions"
    assert queue.get_total_cost(game_state) == 6, "Total cost should be 6"
    
    # Undo last
    removed = queue.remove_last()
    print(f"Removed action: {removed}")
    assert removed is not None, "Should remove action"
    assert len(queue) == 2, "Should have 2 actions"
    assert queue.get_total_cost(game_state) == 5, "Cost should be 5"
    
    # Undo all
    queue.remove_last()
    queue.remove_last()
    assert queue.is_empty, "Queue should be empty"
    
    # Try undo on empty
    removed = queue.remove_last()
    print(f"Remove from empty: {removed}")
    assert removed is None, "Should return None"
    
    print("✅ Action queue undo tests passed!\n")


def test_action_queue_ap_limit():
    """Test action queue AP limit enforcement."""
    print("\n=== Testing Action Queue AP Limit ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=5)
    
    # Add actions within limit
    success, msg = queue.add_action(MockAction(cost=2), game_state)
    assert success, "Should add within limit"
    
    success, msg = queue.add_action(MockAction(cost=2), game_state)
    assert success, "Should add within limit"
    
    # Try to exceed limit
    success, msg = queue.add_action(MockAction(cost=3), game_state)
    print(f"Exceed limit: {success}, {msg}")
    assert not success, "Should reject action exceeding AP"
    assert "Not enough AP" in msg, "Should mention AP shortage"
    assert len(queue) == 2, "Should still have 2 actions"
    
    # Can afford check
    assert queue.can_afford(game_state), "Should be affordable"
    
    print("✅ Action queue AP limit tests passed!\n")


def test_action_queue_validation():
    """Test action queue validation checks."""
    print("\n=== Testing Action Queue Validation ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=10)
    
    # Try to add invalid action
    invalid_action = MockAction(cost=2, will_fail=True)
    success, msg = queue.add_action(invalid_action, game_state)
    print(f"Add invalid action: {success}, {msg}")
    assert not success, "Should reject invalid action"
    assert "Invalid action" in msg, "Should mention validation failure"
    assert queue.is_empty, "Should not add invalid action"
    
    # Add valid action
    valid_action = MockAction(cost=2)
    success, msg = queue.add_action(valid_action, game_state)
    assert success, "Should add valid action"
    
    print("✅ Action queue validation tests passed!\n")


def test_action_queue_commit():
    """Test action queue commit and execution."""
    print("\n=== Testing Action Queue Commit ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=10)
    
    # Add actions
    action1 = MockAction(cost=2)
    action2 = MockAction(cost=3)
    queue.add_action(action1, game_state)
    queue.add_action(action2, game_state)
    
    assert not queue.is_committed, "Should not be committed yet"
    
    # Commit
    results = queue.commit_all(game_state)
    print(f"Commit results: {len(results)} actions executed")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result}")
    
    assert len(results) == 2, "Should execute 2 actions"
    assert all(r.success for r in results), "All should succeed"
    assert queue.is_committed, "Should be committed"
    assert action1._executed, "Action 1 should be executed"  # type: ignore[reportPrivateUsage]
    assert action2._executed, "Action 2 should be executed"  # type: ignore[reportPrivateUsage]
    
    # Try to commit again
    results2 = queue.commit_all(game_state)
    print(f"Second commit attempt: {results2[0].message}")
    assert not results2[0].success, "Should reject second commit"
    
    print("✅ Action queue commit tests passed!\n")


def test_action_queue_clear():
    """Test action queue clear functionality."""
    print("\n=== Testing Action Queue Clear ===")
    
    game_state = create_test_game_state()
    queue = ActionQueue(max_ap=10)
    
    # Add actions
    queue.add_action(MockAction(cost=2), game_state)
    assert not queue.is_empty, "Should have actions before clear"
    
    # Clear
    queue.clear()
    print("Queue cleared")
    
    assert queue.is_empty, "Should be empty after clear"
    assert not queue.is_committed, "Should not be committed after clear"
    
    # Can add new actions
    success, _ = queue.add_action(MockAction(cost=2), game_state)
    assert success, "Should allow new actions after clear"
    
    print("✅ Action queue clear tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3.1 Tests - Action System")
    print("=" * 60)
    
    try:
        test_action_result()
        test_mock_action()
        test_action_queue_basic()
        test_action_queue_undo()
        test_action_queue_ap_limit()
        test_action_queue_validation()
        test_action_queue_commit()
        test_action_queue_clear()
        
        print("=" * 60)
        print("✅ ALL ACTION SYSTEM TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
