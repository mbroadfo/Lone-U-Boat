"""
Base screen class for all game screens.
Provides common functionality for rendering, event handling, and transitions.
"""

import pygame
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class BaseScreen(ABC):
    """Abstract base class for all game screens."""
    
    def __init__(self, screen_manager: Any, config: Any):
        """
        Initialize the base screen.
        
        Args:
            screen_manager: Reference to the ScreenManager
            config: Configuration module (typically board_config)
        """
        self.screen_manager = screen_manager
        self.screen = screen_manager.screen
        self.config = config
        self.running = True
        self.next_screen: Optional[str] = None
        self.next_screen_data: Dict[str, Any] = {}
        
        # Load fonts
        try:
            self.font_small = pygame.font.Font(None, 24)
            self.font_medium = pygame.font.Font(None, 36)
            self.font_large = pygame.font.Font(None, 48)
            self.font_title = pygame.font.Font(None, 72)
        except Exception:
            # Fallback to system default
            self.font_small = pygame.font.SysFont('arial', 24)
            self.font_medium = pygame.font.SysFont('arial', 36)
            self.font_large = pygame.font.SysFont('arial', 48)
            self.font_title = pygame.font.SysFont('arial', 72)
    
    def update_screen(self, screen: pygame.Surface) -> None:
        """Update screen reference when display mode changes."""
        self.screen = screen
    
    @abstractmethod
    def handle_events(self, event: pygame.event.Event) -> None:
        """
        Handle pygame events.
        
        Args:
            event: Pygame event to handle
        """
        pass
    
    @abstractmethod
    def update(self) -> None:
        """Update screen state (called each frame)."""
        pass
    
    @abstractmethod
    def render(self) -> None:
        """Render the screen."""
        pass
    
    def transition_to(self, screen_name: str, **kwargs: Any) -> None:
        """
        Transition to another screen.
        
        Args:
            screen_name: Name of the screen to transition to
            **kwargs: Additional data to pass to the next screen
        """
        self.next_screen = screen_name
        self.next_screen_data = kwargs
        self.running = False
    
    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        color: tuple[int, int, int] = (255, 255, 255),
        center: bool = False,
        bg_color: Optional[tuple[int, int, int]] = None
    ) -> pygame.Rect:
        """
        Draw text on the screen.
        
        Args:
            text: Text to draw
            x: X coordinate
            y: Y coordinate
            font: Pygame font to use
            color: Text color (RGB tuple)
            center: If True, center text at x,y
            bg_color: Optional background color
            
        Returns:
            Rectangle of the rendered text
        """
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        
        if center:
            text_rect.center = (x, y)
        else:
            text_rect.topleft = (x, y)
        
        if bg_color:
            bg_rect = text_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, bg_color, bg_rect)
            pygame.draw.rect(self.screen, color, bg_rect, 2)
        
        self.screen.blit(text_surface, text_rect)
        return text_rect
    
    def draw_button(
        self,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int] = (50, 100, 150),
        hover_color: tuple[int, int, int] = (70, 130, 180),
        text_color: tuple[int, int, int] = (255, 255, 255),
        font: Optional[pygame.font.Font] = None
    ) -> pygame.Rect:
        """
        Draw a button and return its rect for click detection.
        
        Args:
            text: Button text
            x: X coordinate (top-left)
            y: Y coordinate (top-left)
            width: Button width
            height: Button height
            color: Button color
            hover_color: Color when mouse hovers
            text_color: Text color
            font: Font to use (defaults to font_medium)
            
        Returns:
            Button rectangle
        """
        if font is None:
            font = self.font_medium
        
        button_rect = pygame.Rect(x, y, width, height)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)
        
        # Draw button
        pygame.draw.rect(self.screen, hover_color if is_hover else color, button_rect)
        pygame.draw.rect(self.screen, text_color, button_rect, 2)
        
        # Draw text
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=button_rect.center)
        self.screen.blit(text_surface, text_rect)
        
        return button_rect
    
    def draw_panel(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        bg_color: tuple[int, int, int, int] = (30, 30, 40, 220),
        border_color: tuple[int, int, int] = (100, 100, 120),
        border_width: int = 2
    ) -> pygame.Rect:
        """
        Draw a semi-transparent panel.
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Panel width
            height: Panel height
            bg_color: Background color (RGBA)
            border_color: Border color
            border_width: Border width in pixels
            
        Returns:
            Panel rectangle
        """
        panel_rect = pygame.Rect(x, y, width, height)
        
        # Create surface with alpha
        panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        panel_surface.fill(bg_color)
        
        self.screen.blit(panel_surface, (x, y))
        
        if border_width > 0:
            pygame.draw.rect(self.screen, border_color, panel_rect, border_width)
        
        return panel_rect
