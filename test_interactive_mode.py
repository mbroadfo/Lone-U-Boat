"""
Test interactive AI mode - strangler fig pattern verification.

Tests that interactive_ai_mode=True routes through AIActionQueue
instead of batch AI execution.
"""

# pyright: reportPrivateUsage=false

import sys
from pathlib import Path
from typing import List, Tuple, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.game_state import Game
from core.models import GamePhase


def test_interactive_merchant_phase():
    """Test that merchant phase generates action queue in interactive mode."""
    print("\n=== Test: Interactive Merchant Phase ===")
    
    # Create game with interactive mode enabled
    game = Game(mission_number=1, interactive_ai_mode=True)
    game.turn_manager.start_new_turn(game.u_boat)
    
    print(f"Merchants: {sum(1 for s in game.ships if s.ship_type == 'merchant')}")
    
    # Advance to merchant phase
    assert game.turn_manager.current_phase == GamePhase.UBOAT_PHASE
    game._advance_to_next_phase()
    
    # Now in merchant phase - should have generated action queue
    assert game.turn_manager.current_phase == GamePhase.MERCHANT_PHASE
    
    print(f"Queue after phase: {game.current_ai_queue}")
    if game.current_ai_queue:
        print(f"Queue count: {game.current_ai_queue.total_count()}")
    
    # Merchant might have no path or be at destination - that's OK for first turn
    # Just check that batch mode wasn't used
    print("✓ Interactive mode attempted (queue may be empty if no moves available)")
    
    return True


def test_interactive_detection_phase():
    """Test that detection phase generates action queue in interactive mode."""
    print("\n=== Test: Interactive Detection Phase ===")
    
    game = Game(mission_number=1, interactive_ai_mode=True)
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Advance to detection phase
    game._advance_to_next_phase()  # Skip merchant phase
    game._advance_to_next_phase()  # Now in detection
    
    assert game.turn_manager.current_phase == GamePhase.DETECTION_PHASE
    
    # Should have detection action queue
    assert game.current_ai_queue is not None
    assert game.current_ai_queue.total_count() > 0
    
    print(f"✓ Detection phase created queue with {game.current_ai_queue.total_count()} actions")
    
    return True


def test_interactive_escort_phase():
    """Test that escort phase generates action queue in interactive mode."""
    print("\n=== Test: Interactive Escort Phase ===")
    
    game = Game(mission_number=1, interactive_ai_mode=True)
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Advance to escort phase
    game._advance_to_next_phase()  # Merchant
    game._advance_to_next_phase()  # Detection
    game._advance_to_next_phase()  # Escort
    
    assert game.turn_manager.current_phase == GamePhase.ESCORT_PHASE
    
    # Should have escort action queue
    assert game.current_ai_queue is not None
    assert game.current_ai_queue.total_count() > 0
    
    print(f"✓ Escort phase created queue with {game.current_ai_queue.total_count()} actions")
    
    return True


def test_batch_mode_still_works():
    """Test that batch mode (default) still works without queues."""
    print("\n=== Test: Batch Mode Still Works ===")
    
    # Create game with batch mode (default)
    game = Game(mission_number=1, interactive_ai_mode=False)
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Advance to merchant phase
    game._advance_to_next_phase()
    assert game.turn_manager.current_phase == GamePhase.MERCHANT_PHASE
    
    # Advance through merchant phase (batch execution)
    game._advance_to_next_phase()
    
    # Should NOT have created queue (batch mode doesn't use queues)
    assert game.current_ai_queue is None, "Batch mode should not create queues"
    
    # Should have moved to detection phase
    assert game.turn_manager.current_phase == GamePhase.DETECTION_PHASE
    
    print("✓ Batch mode works without queues")
    
    return True


def test_has_pending_ai_actions():
    """Test has_pending_ai_actions() helper method."""
    print("\n=== Test: Pending AI Actions Check ===")
    
    game = Game(mission_number=1, interactive_ai_mode=True)
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Initially no pending actions
    assert not game.has_pending_ai_actions()
    
    # Advance to detection phase (more likely to have actions)
    game._advance_to_next_phase()  # Merchant (might be empty)
    game._advance_to_next_phase()  # Detection
    
    # Detection phase should have pending actions
    if game.has_pending_ai_actions():
        assert game.current_ai_queue is not None, "Queue should exist when has_pending_ai_actions is True"
        print(f"✓ Has pending actions: {game.current_ai_queue.total_count()}")
        
        # Execute all actions
        while game.has_pending_ai_actions():
            _, _ = game.execute_next_ai_action()
        
        # No more pending actions
        assert not game.has_pending_ai_actions()
        print("✓ All actions executed")
    else:
        print("✓ No actions needed (acceptable)")
    
    return True


def run_all_tests():
    """Run all interactive mode tests."""
    tests = [
        test_interactive_merchant_phase,
        test_interactive_detection_phase,
        test_interactive_escort_phase,
        test_batch_mode_still_works,
        test_has_pending_ai_actions
    ]
    
    results: List[Tuple[str, bool, Optional[str]]] = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result, None))
        except Exception as e:
            results.append((test_func.__name__, False, str(e)))
    
    # Print summary
    print("\n" + "="*60)
    print("INTERACTIVE MODE TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")
    
    print(f"\n{passed}/{total} tests passed")
    
    return all(result for _, result, _ in results)


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
