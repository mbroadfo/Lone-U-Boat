"""
Tests for Interactive Detection Actions.

This test suite validates detection actions (escorts and merchant visual)
that players execute during the Detection Phase.
"""

import sys
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.models import HexCoord, Facing, Depth, UBoat, Ship
from core.actions.ai import EscortDetectionAction, MerchantVisualAction
from tests.interactive_ai.conftest import MockGameState, MockDice, HexGrid


# ============================================================================
# ESCORT DETECTION TESTS
# ============================================================================

def test_escort_detection_success(hex_grid: Any, mock_dice: MockDice):
    """Test successful escort detection roll increases DL."""
    # Corvette at R2, U-boat at MEDIUM depth (threshold 4)
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 7), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    u_boat.sonar_operator_alive = False  # Base threshold without modifiers
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 1
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=1)
    can_detect, _ = action.validate(game_state)
    assert can_detect
    
    # Roll 4 - meets threshold
    mock_dice.set_roll_sequence([4])
    result = action.execute(game_state)
    
    assert result.success
    assert action.roll == 4
    assert action.threshold == 4
    assert action.success
    assert action.new_detection_level == 2
    assert "SUCCESS" in result.message
    assert game_state.detection_level == 2


def test_escort_detection_fail(hex_grid: Any, mock_dice: MockDice):
    """Test failed escort detection roll maintains DL."""
    # Destroyer at R1, U-boat at DEEP (threshold 5)
    destroyer = Ship(ship_type='destroyer', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.DEEP)
    u_boat.sonar_operator_alive = False  # Base threshold without modifiers
    
    game_state = MockGameState()
    game_state.ships = [destroyer]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    
    # Roll 3 - below threshold 5
    mock_dice.set_roll_sequence([3])
    result = action.execute(game_state)
    
    assert result.success
    assert action.roll == 3
    assert action.threshold == 5
    assert not action.success
    assert action.new_detection_level == 0
    assert "Failed" in result.message


def test_escort_detection_threshold_sonar_operator(hex_grid: Any, mock_dice: MockDice):
    """Test sonar operator increases detection threshold (+1)."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    u_boat.sonar_operator_alive = True
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    
    # Base threshold for PERISCOPE is 2, +1 for sonar = 3
    mock_dice.set_roll_sequence([2])
    result = action.execute(game_state)
    
    assert action.threshold == 3
    assert action.roll == 2
    assert not action.success  # 2 < 3


def test_escort_detection_threshold_engine_damaged(hex_grid: Any, mock_dice: MockDice):
    """Test engine damage decreases detection threshold (-1, easier to detect)."""
    destroyer = Ship(ship_type='destroyer', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 7), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    u_boat.sonar_operator_alive = False  # Disable for clean test
    u_boat.engine_damaged = True
    
    game_state = MockGameState()
    game_state.ships = [destroyer]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 1
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=1)
    
    # Base threshold for MEDIUM is 4, -1 for engine = 3
    mock_dice.set_roll_sequence([3])
    result = action.execute(game_state)
    
    assert action.threshold == 3
    assert action.roll == 3
    assert action.success  # 3 >= 3


def test_escort_detection_surfaced_auto(hex_grid: Any, mock_dice: MockDice):
    """Test U-boat at SURFACED has threshold 1 (auto-detect)."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    
    # Roll 1 - minimum roll succeeds
    mock_dice.set_roll_sequence([1])
    result = action.execute(game_state)
    
    assert action.threshold == 1
    assert action.success


def test_escort_detection_validation_out_of_range(hex_grid: Any):
    """Test validation fails when escort is out of range (>3)."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 10), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    can_detect, reason = action.validate(game_state)
    
    assert not can_detect
    assert "range" in reason.lower()


def test_escort_detection_validation_not_escort(hex_grid: Any):
    """Test validation fails for non-escort ships."""
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    game_state = MockGameState()
    game_state.ships = [tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    can_detect, reason = action.validate(game_state)
    
    assert not can_detect
    assert "cannot detect" in reason.lower()


def test_escort_detection_validation_max_dl(hex_grid: Any):
    """Test validation fails when already at max DL (3)."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=3)
    can_detect, reason = action.validate(game_state)
    
    assert not can_detect
    assert "maximum" in reason.lower()


def test_escort_detection_validation_blocked_los(hex_grid: Any):
    """Test validation fails when line of sight is blocked by land."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 7), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    # Land hex blocks LOS
    game_state.land_hexes = {HexCoord(5, 6)}
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=0)
    can_detect, reason = action.validate(game_state)
    
    assert not can_detect
    assert "line of sight" in reason.lower() or "blocked" in reason.lower()


def test_escort_detection_dl_caps_at_3(hex_grid: Any, mock_dice: MockDice):
    """Test DL caps at maximum of 3."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 2
    game_state.dice_roller = mock_dice
    
    action = EscortDetectionAction(ship_index=0, current_detection_level=2)
    
    # Successful detection
    mock_dice.set_roll_sequence([6])
    result = action.execute(game_state)
    
    assert action.success
    assert action.new_detection_level == 3  # Capped at 3, not 4


# ============================================================================
# MERCHANT VISUAL DETECTION TESTS
# ============================================================================

def test_merchant_visual_spots_uboat(hex_grid: Any):
    """Test merchant visually spots U-boat at range 1, DL 3."""
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=3)
    can_check, _ = action.validate(game_state)
    assert can_check
    
    result = action.execute(game_state)
    
    assert result.success
    assert action.spotted
    assert action.range_to_uboat == 1
    assert "SPOTS" in result.message or "spotted" in result.message.lower()


def test_merchant_visual_out_of_range(hex_grid: Any):
    """Test merchant doesn't spot U-boat beyond visual range."""
    freighter = Ship(ship_type='freighter', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [freighter]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=3)
    can_check, reason = action.validate(game_state)
    
    assert not can_check
    assert "visual range" in reason.lower()


def test_merchant_visual_uboat_too_deep(hex_grid: Any):
    """Test merchant cannot spot U-boat at MEDIUM depth."""
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    game_state = MockGameState()
    game_state.ships = [tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=3)
    can_check, reason = action.validate(game_state)
    
    assert not can_check
    assert "cannot be visually detected" in reason.lower() or "too deep" in reason.lower()


def test_merchant_visual_periscope_depth(hex_grid: Any):
    """Test merchant can spot U-boat at PERISCOPE depth."""
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    
    game_state = MockGameState()
    game_state.ships = [tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=3)
    can_check, _ = action.validate(game_state)
    assert can_check
    
    result = action.execute(game_state)
    
    assert result.success
    assert action.spotted


def test_merchant_visual_validation_not_dl3(hex_grid: Any):
    """Test merchant visual requires DL 3."""
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 2
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=2)
    can_check, reason = action.validate(game_state)
    
    assert not can_check
    assert "dl 3" in reason.lower() or "requires dl 3" in reason.lower()


def test_merchant_visual_validation_not_merchant(hex_grid: Any):
    """Test visual detection only works for merchants."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    game_state = MockGameState()
    game_state.ships = [corvette]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 3
    
    action = MerchantVisualAction(ship_index=0, current_detection_level=3)
    can_check, reason = action.validate(game_state)
    
    assert not can_check
    assert "merchant" in reason.lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_detection_phase_sequence(hex_grid: Any, mock_dice: MockDice):
    """Test typical detection phase: escort detects, increases DL, merchant checks visual."""
    # Setup: Corvette and tanker, U-boat at MEDIUM
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    tanker = Ship(ship_type='tanker', position=HexCoord(5, 7), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 6), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    u_boat.sonar_operator_alive = False  # Base threshold without modifiers
    
    game_state = MockGameState()
    game_state.ships = [corvette, tanker]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    # Phase 1: Corvette attempts detection (threshold 4)
    detection = EscortDetectionAction(ship_index=0, current_detection_level=0)
    mock_dice.set_roll_sequence([4])
    result1 = detection.execute(game_state)
    
    assert result1.success
    assert detection.success
    assert game_state.detection_level == 1
    
    # Phase 2: Tanker tries visual but DL not high enough
    visual = MerchantVisualAction(ship_index=1, current_detection_level=1)
    can_check, _ = visual.validate(game_state)
    assert not can_check  # Needs DL 3


def test_multiple_escort_detection_increases_dl(hex_grid: Any, mock_dice: MockDice):
    """Test multiple escorts can each increase DL."""
    corvette = Ship(ship_type='corvette', position=HexCoord(5, 5), facing=Facing.NORTH)
    destroyer = Ship(ship_type='destroyer', position=HexCoord(6, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(5, 7), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.sonar_operator_alive = False  # Base threshold without modifiers
    
    game_state = MockGameState()
    game_state.ships = [corvette, destroyer]
    game_state.u_boat = u_boat
    game_state.hex_grid = hex_grid
    game_state.detection_level = 0
    game_state.dice_roller = mock_dice
    
    # Corvette detects (threshold 1)
    action1 = EscortDetectionAction(ship_index=0, current_detection_level=0)
    mock_dice.set_roll_sequence([1])
    action1.execute(game_state)
    assert game_state.detection_level == 1
    
    # Destroyer detects (threshold 1)
    action2 = EscortDetectionAction(ship_index=1, current_detection_level=1)
    mock_dice.set_roll_sequence([1])
    action2.execute(game_state)
    assert game_state.detection_level == 2
