"""
Integration test for merchant AI in game state.
Tests that merchant phase executes correctly during turn cycle.
"""

# pyright: reportPrivateUsage=false

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.game_state import Game
from core.models import GamePhase, HexCoord


def test_merchant_phase_integration():
    """Test that merchant phase executes in the game loop."""
    print("\n=== Test: Merchant Phase Integration ===")
    
    # Create game instance
    game = Game(mission_number=1)
    
    # Start first turn
    game.turn_manager.start_new_turn(game.u_boat)
    
    print(f"Initial merchant position: {game.ships[0].position.q},{game.ships[0].position.r}")
    
    # Advance through U-Boat phase
    assert game.turn_manager.current_phase == GamePhase.UBOAT_PHASE
    game._advance_to_next_phase()
    
    # Now in merchant phase
    assert game.turn_manager.current_phase == GamePhase.MERCHANT_PHASE
    
    # Advance through merchant phase (this executes merchant AI)
    game._advance_to_next_phase()
    
    # Check merchant position changed (should have moved from (1,4) to (1,5))
    merchant = game.ships[0]
    print(f"Merchant position after phase: {merchant.position.q},{merchant.position.r}")
    assert merchant.position == HexCoord(1, 5), f"Expected (1,5), got {merchant.position}"
    
    # Check phase log
    logs = game.turn_manager.get_phase_log("Merchant Phase")
    print(f"\nPhase logs:")
    for log in logs:
        print(f"  {log}")
    
    assert len(logs) >= 2  # Should have "Merchant ships acting..." and movement message
    assert any("moves to [1,5]" in log for log in logs)
    
    print("✓ Merchant phase executed correctly")


def test_merchant_movement_multiple_turns():
    """Test merchant movement over multiple turns."""
    print("\n=== Test: Merchant Movement Over Multiple Turns ===")
    
    game = Game(mission_number=1)
    game.turn_manager.start_new_turn(game.u_boat)
    
    merchant = game.ships[0]
    expected_positions = [
        HexCoord(1, 4),  # Start
        HexCoord(1, 5),  # Turn 1
        HexCoord(1, 6),  # Turn 2
        HexCoord(1, 7),  # Turn 3
        HexCoord(2, 7),  # Turn 4 (turn east)
    ]
    
    for turn_num, expected_pos in enumerate(expected_positions):
        if turn_num == 0:
            # Starting position
            assert merchant.position == expected_pos
            print(f"Turn {turn_num}: {merchant.position.q},{merchant.position.r} (start)")
        else:
            # Advance through U-Boat phase
            game._advance_to_next_phase()
            
            # Advance through merchant phase
            game._advance_to_next_phase()
            
            # Skip other phases to start next turn
            while game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
                game._advance_to_next_phase()
            
            # Check position
            print(f"Turn {turn_num}: {merchant.position.q},{merchant.position.r}")
            assert merchant.position == expected_pos, f"Turn {turn_num}: Expected {expected_pos}, got {merchant.position}"
    
    print("✓ Merchant follows expected path over multiple turns")


def test_damaged_merchant_movement():
    """Test that damaged merchants roll for movement."""
    print("\n=== Test: Damaged Merchant Movement ===")
    
    game = Game(mission_number=1)
    
    # Damage the merchant
    merchant = game.ships[0]
    merchant.damaged = True
    
    game.turn_manager.start_new_turn(game.u_boat)
    
    initial_pos = merchant.position
    print(f"Damaged merchant at: {initial_pos.q},{initial_pos.r}")
    
    # Advance through U-Boat phase then merchant phase
    game._advance_to_next_phase()
    game._advance_to_next_phase()
    
    # Check logs mention dice roll
    logs = game.turn_manager.get_phase_log("Merchant Phase")
    print(f"\nPhase logs:")
    for log in logs:
        print(f"  {log}")
    
    # Should mention "rolled" in the logs
    assert any("rolled" in log.lower() for log in logs)
    
    # Merchant may or may not have moved (depends on roll)
    final_pos = merchant.position
    print(f"Final position: {final_pos.q},{final_pos.r}")
    
    if final_pos == initial_pos:
        print("✓ Damaged merchant failed roll and didn't move")
    else:
        print("✓ Damaged merchant passed roll and moved")


def run_all_tests():
    """Run all integration tests."""
    print("="*60)
    print("MERCHANT AI INTEGRATION TESTS")
    print("="*60)
    
    test_functions = [
        test_merchant_phase_integration,
        test_merchant_movement_multiple_turns,
        test_damaged_merchant_movement,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
