"""
Simple animation system for visual effects.
Game state updates immediately - animations are purely visual overlays.
"""

import time
from typing import Optional, Tuple, Dict
from .models import HexCoord, Facing


class Animation:
    """Base class for animations."""
    
    def __init__(self, duration: float):
        """
        Initialize animation.
        
        Args:
            duration: Animation duration in seconds
        """
        self.start_time = time.time()
        self.duration = duration
    
    def get_progress(self) -> float:
        """
        Get animation progress (0.0 to 1.0).
        
        Returns:
            Progress value, clamped to [0.0, 1.0]
        """
        elapsed = time.time() - self.start_time
        progress = elapsed / self.duration
        return min(progress, 1.0)
    
    def is_finished(self) -> bool:
        """Check if animation has completed."""
        return self.get_progress() >= 1.0


class RotateAnimation(Animation):
    """Animation for unit rotation."""
    
    def __init__(self, old_facing: Facing, new_facing: Facing, duration: float = 0.3):
        """
        Initialize rotation animation.
        
        Args:
            old_facing: Starting facing direction
            new_facing: Target facing direction
            duration: Animation duration in seconds
        """
        super().__init__(duration)
        self.old_facing = old_facing
        self.new_facing = new_facing
        
        # Calculate angle delta (choose shortest rotation path)
        old_angle = old_facing.to_degrees()
        new_angle = new_facing.to_degrees()
        
        # Normalize angle difference to [-180, 180]
        delta = new_angle - old_angle
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360
        
        self.start_angle = old_angle
        self.angle_delta = delta
    
    def get_current_angle(self) -> float:
        """
        Get current interpolated angle in degrees.
        
        Returns:
            Angle in degrees [0, 360)
        """
        progress = self.get_progress()
        # Ease-in-out for smoother rotation
        eased = self._ease_in_out(progress)
        angle = self.start_angle + (self.angle_delta * eased)
        return angle % 360
    
    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Smooth easing function."""
        return t * t * (3.0 - 2.0 * t)


class MoveAnimation(Animation):
    """Animation for unit movement."""
    
    def __init__(self, old_pos: HexCoord, new_pos: HexCoord, duration: float = 0.5):
        """
        Initialize movement animation.
        
        Args:
            old_pos: Starting hex coordinate
            new_pos: Target hex coordinate
            duration: Animation duration in seconds
        """
        super().__init__(duration)
        self.old_pos = old_pos
        self.new_pos = new_pos
    
    def get_current_position(self) -> Tuple[float, float]:
        """
        Get current interpolated position in axial coordinates.
        
        Returns:
            Tuple of (q, r) as floats
        """
        progress = self.get_progress()
        # Ease-in-out for smoother movement
        eased = self._ease_in_out(progress)
        
        q = self.old_pos.q + (self.new_pos.q - self.old_pos.q) * eased
        r = self.old_pos.r + (self.new_pos.r - self.old_pos.r) * eased
        
        return (q, r)
    
    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Smooth easing function."""
        return t * t * (3.0 - 2.0 * t)


class AnimationManager:
    """Manages active animations."""
    
    def __init__(self):
        """Initialize animation manager."""
        self.u_boat_rotation: Optional[RotateAnimation] = None
        self.u_boat_movement: Optional[MoveAnimation] = None
        
        # Ship animations: dict mapping ship ID to (rotation_anim, movement_anim)
        self.ship_animations: Dict[int, Tuple[Optional[RotateAnimation], Optional[MoveAnimation]]] = {}
    
    def start_u_boat_rotation(self, old_facing: Facing, new_facing: Facing) -> None:
        """
        Start U-boat rotation animation.
        
        Args:
            old_facing: Starting facing
            new_facing: Target facing
        """
        self.u_boat_rotation = RotateAnimation(old_facing, new_facing)
    
    def start_u_boat_movement(self, old_pos: HexCoord, new_pos: HexCoord) -> None:
        """
        Start U-boat movement animation.
        
        Args:
            old_pos: Starting position
            new_pos: Target position
        """
        self.u_boat_movement = MoveAnimation(old_pos, new_pos)
    
    def start_ship_rotation(self, ship_id: int, old_facing: Facing, new_facing: Facing) -> None:
        """
        Start ship rotation animation.
        
        Args:
            ship_id: ID of the ship (index in game.ships list)
            old_facing: Starting facing
            new_facing: Target facing
        """
        if ship_id not in self.ship_animations:
            self.ship_animations[ship_id] = (None, None)
        
        rotation_anim = RotateAnimation(old_facing, new_facing)
        _, movement_anim = self.ship_animations[ship_id]
        self.ship_animations[ship_id] = (rotation_anim, movement_anim)
    
    def start_ship_movement(self, ship_id: int, old_pos: HexCoord, new_pos: HexCoord) -> None:
        """
        Start ship movement animation.
        
        Args:
            ship_id: ID of the ship (index in game.ships list)
            old_pos: Starting position
            new_pos: Target position
        """
        if ship_id not in self.ship_animations:
            self.ship_animations[ship_id] = (None, None)
        
        movement_anim = MoveAnimation(old_pos, new_pos)
        rotation_anim, _ = self.ship_animations[ship_id]
        self.ship_animations[ship_id] = (rotation_anim, movement_anim)
    
    def update(self) -> None:
        """Update all animations, removing finished ones."""
        if self.u_boat_rotation and self.u_boat_rotation.is_finished():
            self.u_boat_rotation = None
        
        if self.u_boat_movement and self.u_boat_movement.is_finished():
            self.u_boat_movement = None
        
        # Update ship animations
        finished_ships: list[int] = []
        for ship_id, (rotation_anim, movement_anim) in self.ship_animations.items():
            rotation_finished = rotation_anim is None or rotation_anim.is_finished()
            movement_finished = movement_anim is None or movement_anim.is_finished()
            
            if rotation_finished and movement_finished:
                finished_ships.append(ship_id)  # type: ignore[arg-type]
            else:
                # Update the tuple if either animation finished
                new_rotation = None if rotation_finished else rotation_anim
                new_movement = None if movement_finished else movement_anim
                self.ship_animations[ship_id] = (new_rotation, new_movement)
        
        # Remove ships with no active animations
        for ship_id in finished_ships:
            del self.ship_animations[ship_id]
    
    def is_animating(self) -> bool:
        """Check if any animations are active."""
        return (self.u_boat_rotation is not None or 
                self.u_boat_movement is not None or 
                len(self.ship_animations) > 0)
    
    def get_u_boat_render_state(self, actual_pos: HexCoord, actual_facing: Facing) -> Tuple[Tuple[float, float], float]:
        """
        Get U-boat's current visual state for rendering.
        
        Args:
            actual_pos: U-boat's actual game state position
            actual_facing: U-boat's actual game state facing
        
        Returns:
            Tuple of ((q, r), angle_degrees) for rendering
        """
        # Start with actual game state
        render_pos = (float(actual_pos.q), float(actual_pos.r))
        render_angle = actual_facing.to_degrees()
        
        # Override with animation if active
        if self.u_boat_movement:
            render_pos = self.u_boat_movement.get_current_position()
        
        if self.u_boat_rotation:
            render_angle = self.u_boat_rotation.get_current_angle()
        
        return (render_pos, render_angle)
    
    def get_ship_render_state(self, ship_id: int, actual_pos: HexCoord, 
                              actual_facing: Facing) -> Tuple[Tuple[float, float], float]:
        """
        Get ship's current visual state for rendering.
        
        Args:
            ship_id: ID of the ship (index in game.ships list)
            actual_pos: Ship's actual game state position
            actual_facing: Ship's actual game state facing
        
        Returns:
            Tuple of ((q, r), angle_degrees) for rendering
        """
        # Start with actual game state
        render_pos = (float(actual_pos.q), float(actual_pos.r))
        render_angle = actual_facing.to_degrees()
        
        # Override with animation if active
        if ship_id in self.ship_animations:
            rotation_anim, movement_anim = self.ship_animations[ship_id]
            
            if movement_anim:
                render_pos = movement_anim.get_current_position()
            
            if rotation_anim:
                render_angle = rotation_anim.get_current_angle()
        
        return (render_pos, render_angle)
    
    def clear_all(self) -> None:
        """Clear all active animations."""
        self.u_boat_rotation = None
        self.u_boat_movement = None
        self.ship_animations.clear()
