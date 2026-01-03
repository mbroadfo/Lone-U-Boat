"""
Board Layout Runtime Engine - Resolution-independent positioning.

This module computes screen-space positions for the map, hex grid, and status boxes
based on calibration data and current screen size. It acts as the single source of
truth for "where things are" at runtime.

The layout engine:
1. Takes calibration data (from board_layout_config.py) 
2. Computes available board area based on UI panels
3. Fits the map into that area with uniform scaling
4. Derives hex grid and status box positions by scaling calibration data

All rendering code should query this engine instead of doing manual positioning.
"""

import pygame
from dataclasses import dataclass
from typing import Tuple, Dict, Any

from config.board_layout_config import MissionLayoutConfig


@dataclass
class BoardRects:
    """Screen-space rectangles for major board areas."""
    map_rect: pygame.Rect  # Where the map image is drawn
    # Future: left_panel_rect, right_panel_rect, top_bar_rect, etc.


class BoardLayoutRuntime:
    """Runtime layout engine that computes positions based on screen size and calibration.
    
    This class is the bridge between:
    - Static calibration data (in map coordinates)
    - Dynamic screen size (window can be resized)
    - Renderer needs (screen pixel coordinates)
    """
    
    def __init__(self, screen_size: Tuple[int, int], layout_cfg: MissionLayoutConfig, ui_cfg: Dict[str, Any]):
        """Initialize the layout engine.
        
        Args:
            screen_size: Current screen size (width, height)
            layout_cfg: Mission layout configuration with calibration data
            ui_cfg: UI configuration dict from board_config (panels, margins, etc.)
        """
        self.screen_w, self.screen_h = screen_size
        self.cfg = layout_cfg
        self.ui_cfg = ui_cfg
        
        # Computed values (updated by recompute)
        self.scale = 1.0  # Uniform scale factor from calibration to screen
        self.board_rects: BoardRects = BoardRects(map_rect=pygame.Rect(0, 0, 1, 1))
        
        # Hex grid runtime values
        self.hex_size: float = layout_cfg.hex_grid_calib.hex_size
        self.hex_origin_screen: Tuple[float, float] = (0.0, 0.0)
        
        # Status box runtime values
        self.status_box_rects: Dict[str, pygame.Rect] = {}
        
        # Initial computation
        self.recompute(screen_size)
    
    def recompute(self, screen_size: Tuple[int, int]) -> None:
        """Recompute all layout positions for a new screen size.
        
        This is a thin wrapper that creates a full-screen board rect.
        For more control, use recompute_for_board() directly.
        
        Args:
            screen_size: New screen size (width, height)
        """
        self.screen_w, self.screen_h = screen_size
        
        # Create a full-screen board rect (no panels)
        top_bar_h = self.ui_cfg.get('top_bar_height', 40)
        bottom_margin = 40
        board_rect = pygame.Rect(
            0,
            top_bar_h,
            self.screen_w,
            self.screen_h - top_bar_h - bottom_margin
        )
        
        self.recompute_for_board(board_rect)
    
    def recompute_for_board(self, board_rect: pygame.Rect) -> None:
        """Recompute all layout positions for a specific board area.
        
        This is the core layout algorithm. All positions are computed relative
        to the provided board_rect, making the layout independent of screen panels.
        
        Args:
            board_rect: The board area in screen coordinates (x, y, width, height)
        """
        board_w = board_rect.width
        board_h = board_rect.height
        
        # 1) Fit map into board area, preserving aspect ratio
        map_calib = self.cfg.map_calib
        scale_w = board_w / map_calib.width
        scale_h = board_h / map_calib.height
        self.scale = min(scale_w, scale_h)
        
        map_render_w = int(map_calib.width * self.scale)
        map_render_h = int(map_calib.height * self.scale)
        
        # Center map in board area
        map_x = board_rect.x + (board_w - map_render_w) // 2
        map_y = board_rect.y + (board_h - map_render_h) // 2
        
        self.board_rects = BoardRects(
            map_rect=pygame.Rect(map_x, map_y, map_render_w, map_render_h)
        )
        
        # 3) Compute hex grid screen position
        hg = self.cfg.hex_grid_calib
        self.hex_size = hg.hex_size * self.scale
        self.hex_origin_screen = (
            map_x + hg.origin_in_map[0] * self.scale,
            map_y + hg.origin_in_map[1] * self.scale,
        )
        
        # 4) Compute status box screen rectangles
        self.status_box_rects = {}
        for name, (x, y, w, h) in self.cfg.status_calib.boxes_in_map.items():
            self.status_box_rects[name] = pygame.Rect(
                int(map_x + x * self.scale),
                int(map_y + y * self.scale),
                int(w * self.scale),
                int(h * self.scale),
            )
    
    def screen_to_map(self, screen_pos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert screen coordinates to map-relative coordinates.
        
        Useful for editor mode when adjusting calibration based on mouse clicks.
        
        Args:
            screen_pos: Position in screen space (x, y)
            
        Returns:
            Position in map space at calibration size (x, y)
        """
        screen_x, screen_y = screen_pos
        map_rect = self.board_rects.map_rect
        
        # Relative to map top-left in screen space
        rel_x = screen_x - map_rect.x
        rel_y = screen_y - map_rect.y
        
        # Scale back to calibration size
        map_x = rel_x / self.scale
        map_y = rel_y / self.scale
        
        return (map_x, map_y)
    
    def map_to_screen(self, map_pos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert map-relative coordinates to screen coordinates.
        
        Args:
            map_pos: Position in map space at calibration size (x, y)
            
        Returns:
            Position in screen space (x, y)
        """
        map_x, map_y = map_pos
        map_rect = self.board_rects.map_rect
        
        screen_x = map_rect.x + map_x * self.scale
        screen_y = map_rect.y + map_y * self.scale
        
        return (screen_x, screen_y)
    
    def hit_test_status_box(self, screen_pos: Tuple[float, float]) -> str | None:
        """Find which status box (if any) contains a screen position.
        
        Useful for editor mode to select status boxes for adjustment.
        
        Args:
            screen_pos: Position in screen space (x, y)
            
        Returns:
            Name of the status box, or None if no hit
        """
        x, y = screen_pos
        for name, rect in self.status_box_rects.items():
            if rect.collidepoint(x, y):
                return name
        return None
