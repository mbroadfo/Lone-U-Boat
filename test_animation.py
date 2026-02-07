"""Test animation system."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.animation import AnimationManager, RotateAnimation, MoveAnimation
from core.models import Facing, HexCoord
import time


def test_rotate_animation():
    """Test rotation animation."""
    print("\n=== Test: Rotation Animation ===")
    
    anim = RotateAnimation(Facing.NORTH, Facing.NORTHEAST, duration=0.5)
    
    # Check initial state
    assert not anim.is_finished()
    assert anim.get_progress() == 0.0
    assert anim.get_current_angle() == 0.0  # North = 0°
    
    # Wait a bit
    time.sleep(0.25)
    progress = anim.get_progress()
    angle = anim.get_current_angle()
    print(f"Progress at 0.25s: {progress:.2f}, Angle: {angle:.1f}°")
    assert 0.4 < progress < 0.6  # Should be around 50%
    assert 20 < angle < 40  # Should be between 0° and 60°
    
    # Wait for completion
    time.sleep(0.3)
    assert anim.is_finished()
    assert anim.get_current_angle() == 60.0  # Northeast = 60°
    
    print("✓ Rotation animation works correctly")


def test_move_animation():
    """Test movement animation."""
    print("\n=== Test: Movement Animation ===")
    
    start = HexCoord(5, 5)
    end = HexCoord(6, 5)
    anim = MoveAnimation(start, end, duration=0.5)
    
    # Check initial state
    assert not anim.is_finished()
    q, r = anim.get_current_position()
    assert q == 5.0 and r == 5.0
    
    # Wait a bit
    time.sleep(0.25)
    q, r = anim.get_current_position()
    print(f"Position at 0.25s: ({q:.2f}, {r:.2f})")
    assert 5.4 < q < 5.6  # Should be around 50% of the way
    assert r == 5.0  # r doesn't change
    
    # Wait for completion
    time.sleep(0.3)
    assert anim.is_finished()
    q, r = anim.get_current_position()
    assert q == 6.0 and r == 5.0
    
    print("✓ Movement animation works correctly")


def test_animation_manager():
    """Test animation manager."""
    print("\n=== Test: Animation Manager ===")
    
    manager = AnimationManager()
    
    # Start rotation
    manager.start_u_boat_rotation(Facing.NORTH, Facing.SOUTH)
    assert manager.is_animating()
    assert manager.u_boat_rotation is not None
    
    # Check render state
    pos, angle = manager.get_u_boat_render_state(HexCoord(5, 5), Facing.SOUTH)
    assert pos == (5.0, 5.0)  # No movement animation
    assert angle == 0.0  # Animation just started, still at 0°
    
    # Wait for animation to finish
    time.sleep(0.35)
    manager.update()
    assert not manager.is_animating()
    assert manager.u_boat_rotation is None
    
    # Test movement
    manager.start_u_boat_movement(HexCoord(5, 5), HexCoord(6, 5))
    assert manager.is_animating()
    
    time.sleep(0.6)
    manager.update()
    assert not manager.is_animating()
    
    print("✓ Animation manager works correctly")


def test_angle_wrapping():
    """Test angle wrapping for shortest path."""
    print("\n=== Test: Angle Wrapping ===")
    
    # Test wrapping: NW (300°) to N (0°) should go through 330° not back through 180°
    anim = RotateAnimation(Facing.NORTHWEST, Facing.NORTH, duration=0.3)
    time.sleep(0.15)
    angle = anim.get_current_angle()
    print(f"NW->N midpoint angle: {angle:.1f}° (should be ~330°)")
    assert 320 < angle < 350  # Should go through 330° (shortest path)
    
    print("✓ Angle wrapping works correctly")


if __name__ == "__main__":
    test_rotate_animation()
    test_move_animation()
    test_animation_manager()
    test_angle_wrapping()
    print("\n✅ All animation tests passed!")
