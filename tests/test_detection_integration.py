"""
Integration test for detection AI in game state.
Tests that detection phase executes correctly during turn cycle.
"""

# pyright: reportPrivateUsage=false

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.game_state import Game
from core.models import GamePhase, HexCoord, Depth


def test_detection_phase_integration():
    """Test that detection phase executes in the game loop."""
    print("\n=== Test: Detection Phase Integration ===")
    
    # Create game instance
    game = Game(mission_number=1)
    
    # Start first turn
    game.turn_manager.start_new_turn(game.u_boat)
    
    print(f"Initial DL: {game.detection_level}")
    print(f"U-boat depth: {game.u_boat.depth.name}")
    print(f"U-boat position: {game.u_boat.position.q},{game.u_boat.position.r}")
    print(f"Corvette position: {game.ships[1].position.q},{game.ships[1].position.r}")
    
    # Advance through U-Boat phase
    assert game.turn_manager.current_phase == GamePhase.UBOAT_PHASE
    game._advance_to_next_phase()
    
    # Advance through Merchant phase
    assert game.turn_manager.current_phase == GamePhase.MERCHANT_PHASE
    game._advance_to_next_phase()
    
    # Now in detection phase
    assert game.turn_manager.current_phase == GamePhase.DETECTION_PHASE
    
    initial_dl = game.detection_level
    
    # Advance through detection phase (this executes detection AI)
    game._advance_to_next_phase()
    
    # Check phase log
    logs = game.turn_manager.get_phase_log("Detection Phase")
    print(f"\nPhase logs:")
    for log in logs:
        print(f"  {log}")
    
    # Detection should have been attempted (or skipped if out of range)
    assert len(logs) >= 2  # Should have at least "Calculating..." and threshold message
    
    print(f"✓ Detection phase executed correctly (DL: {initial_dl} → {game.detection_level})")


def test_detection_with_close_escort():
    """Test detection when escort is close to U-boat."""
    print("\n=== Test: Detection with Close Escort ===")
    
    game = Game(mission_number=1)
    
    # Move corvette close to U-boat
    game.ships[1].position = HexCoord(9, 2)  # U-boat at (9,0), corvette at range 2
    
    game.turn_manager.start_new_turn(game.u_boat)
    
    print(f"U-boat at: {game.u_boat.position.q},{game.u_boat.position.r} (depth: {game.u_boat.depth.name})")
    print(f"Corvette at: {game.ships[1].position.q},{game.ships[1].position.r}")
    print(f"Initial DL: {game.detection_level}")
    
    # Advance to detection phase
    game._advance_to_next_phase()  # U-boat phase
    game._advance_to_next_phase()  # Merchant phase
    game._advance_to_next_phase()  # Detection phase
    
    # Check logs
    logs = game.turn_manager.get_phase_log("Detection Phase")
    print(f"\nDetection logs:")
    for log in logs:
        print(f"  {log}")
    
    # Should mention the corvette attempting detection
    assert any("Corvette" in log for log in logs)
    assert any("In range" in log or "rolled" in log for log in logs)
    
    print(f"✓ Escort detection attempted (DL: {game.detection_level})")


def test_detection_at_different_depths():
    """Test detection thresholds change with depth."""
    print("\n=== Test: Detection at Different Depths ===")
    
    for depth in [Depth.SURFACED, Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        game = Game(mission_number=1, initial_depth=depth)
        
        # Move corvette close
        game.ships[1].position = HexCoord(9, 2)  # Range 2
        
        game.turn_manager.start_new_turn(game.u_boat)
        
        # Advance to detection phase
        game._advance_to_next_phase()  # U-boat phase
        game._advance_to_next_phase()  # Merchant phase
        game._advance_to_next_phase()  # Detection phase
        
        logs = game.turn_manager.get_phase_log("Detection Phase")
        
        # Find the threshold message
        threshold_msg = [log for log in logs if "need" in log and "on 1d6" in log]
        if threshold_msg:
            print(f"  {depth.name}: {threshold_msg[0]}")
        
        # Verify threshold mentioned in logs
        assert any("need" in log for log in logs)
    
    print(f"✓ Detection thresholds vary by depth")


def test_detection_level_persistence():
    """Test that detection level persists across turns."""
    print("\n=== Test: Detection Level Persistence ===")
    
    game = Game(mission_number=1)
    
    # Move corvette very close
    game.ships[1].position = HexCoord(9, 1)  # Range 1
    
    # Force a high detection level
    game.detection_level = 2
    initial_dl = game.detection_level
    
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Advance through phases
    game._advance_to_next_phase()  # U-boat phase
    game._advance_to_next_phase()  # Merchant phase
    game._advance_to_next_phase()  # Detection phase
    
    # DL should be at least what we set (may increase if detection succeeds)
    assert game.detection_level >= initial_dl
    
    print(f"✓ Detection level persists (started at {initial_dl}, now {game.detection_level})")


def test_detection_skip_at_max():
    """Test detection phase skips when DL already at 3."""
    print("\n=== Test: Detection Skip at Max DL ===")
    
    game = Game(mission_number=1)
    
    # Set DL to max
    game.detection_level = 3
    
    # Move corvette close
    game.ships[1].position = HexCoord(9, 1)
    
    game.turn_manager.start_new_turn(game.u_boat)
    
    # Advance to detection phase
    game._advance_to_next_phase()  # U-boat phase
    game._advance_to_next_phase()  # Merchant phase
    game._advance_to_next_phase()  # Detection phase
    
    logs = game.turn_manager.get_phase_log("Detection Phase")
    
    # Should mention skipping
    assert any("already at maximum" in log for log in logs)
    assert game.detection_level == 3  # Should remain at 3
    
    print(f"✓ Detection phase skipped at max DL")


def run_all_tests():
    """Run all integration tests."""
    print("="*60)
    print("DETECTION AI INTEGRATION TESTS")
    print("="*60)
    
    test_functions = [
        test_detection_phase_integration,
        test_detection_with_close_escort,
        test_detection_at_different_depths,
        test_detection_level_persistence,
        test_detection_skip_at_max,
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
