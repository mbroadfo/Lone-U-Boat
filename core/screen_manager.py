"""
Screen Manager - Handles screen transitions and the main game loop.
"""

import pygame
from typing import Any, Optional
from config import board_config as cfg
from .screens import MainMenuScreen, UnifiedGameScreen


class ScreenManager:
    """Manages screen transitions and the main game loop."""
    
    def __init__(self):
        """Initialize the screen manager."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), 
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Lone U-Boat")
        self.clock = pygame.time.Clock()
        
        self.current_screen_name = 'menu'
        self.current_screen: Optional[Any] = None
        self.running = True
        self.fullscreen = False
        self.windowed_size = (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)  # Remember last windowed size
        
        # Start with main menu
        self._transition_to('menu')
    
    def toggle_fullscreen(self) -> None:
        if not self.fullscreen:
            # Entering fullscreen - save current window size
            self.windowed_size = self.screen.get_size()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.fullscreen = True
        else:
            # Exiting fullscreen - restore previous window size
            self.screen = pygame.display.set_mode(
                self.windowed_size,
                pygame.RESIZABLE
            )
            self.fullscreen = False
        
        # Propagate new screen to current screen and its components
        if self.current_screen:
            self.current_screen.update_screen(self.screen)
    
    def _transition_to(self, screen_name: str, **kwargs: Any) -> None:
        """
        Transition to a new screen.
        
        Args:
            screen_name: Name of screen to transition to
            **kwargs: Arguments to pass to the new screen
        """
        self.current_screen_name = screen_name
        
        if screen_name == 'menu':
            self.current_screen = MainMenuScreen(self, cfg)
        
        elif screen_name == 'game':
            mission_number: int = int(kwargs.get('mission_number', 1))
            self.current_screen = UnifiedGameScreen(self, cfg, mission_number)
        
        elif screen_name == 'quit':
            self.running = False
        
        else:
            raise ValueError(f"Unknown screen: {screen_name}")
    
    def run(self) -> None:
        """Main game loop."""
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                
                if self.current_screen:
                    self.current_screen.handle_events(event)
            
            # Update
            if self.current_screen:
                self.current_screen.update()
            
            # Render
            if self.current_screen:
                self.current_screen.render()
            
            # Check for screen transitions
            if self.current_screen and not self.current_screen.running:
                next_screen = self.current_screen.next_screen
                next_data = self.current_screen.next_screen_data
                
                if next_screen:
                    self._transition_to(next_screen, **next_data)
                else:
                    self.running = False
            
            self.clock.tick(60)
        
        pygame.quit()
