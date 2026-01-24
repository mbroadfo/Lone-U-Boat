"""
Main Menu Screen - Mission selection and game start.
"""

import pygame
from typing import List, Dict, Any
from .base_screen import BaseScreen


class MainMenuScreen(BaseScreen):
    """Main menu screen with mission selection."""
    
    def __init__(self, screen_manager: Any, config: Any):
        """Initialize the main menu."""
        super().__init__(screen_manager, config)
        
        # Define available missions
        self.missions: List[Dict[str, Any]] = [
            {
                'number': 1,
                'name': 'Supply Ship Attack: North of Scotland',
                'unlocked': True,
                'description': 'Destroy the merchant ship and escape'
            },
            # Future missions will be added here
            {'number': 2, 'name': 'Convoy Raid', 'unlocked': False, 'description': 'Coming soon...'},
            {'number': 3, 'name': 'Escort Hunter', 'unlocked': False, 'description': 'Coming soon...'},
            {'number': 4, 'name': 'Wolf Pack', 'unlocked': False, 'description': 'Coming soon...'},
        ]
        
        self.selected_mission = 1
        self.button_rects: List[pygame.Rect] = []
    
    def handle_events(self, event: pygame.event.Event) -> None:
        """Handle menu events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
                self.next_screen = 'quit'
            
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Start selected mission if unlocked
                if self.missions[self.selected_mission - 1]['unlocked']:
                    self.transition_to('game', mission_number=self.selected_mission)
            
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                # Move selection up
                if self.selected_mission > 1:
                    self.selected_mission -= 1
            
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                # Move selection down
                if self.selected_mission < len(self.missions):
                    self.selected_mission += 1
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_pos = pygame.mouse.get_pos()
                
                # Check mission button clicks
                for i, rect in enumerate(self.button_rects):
                    if rect.collidepoint(mouse_pos) and self.missions[i]['unlocked']:
                        self.selected_mission = i + 1
                        self.transition_to('game', mission_number=self.selected_mission)
                        break
    
    def update(self) -> None:
        """Update menu state."""
        pass  # Static menu, no updates needed
    
    def render(self) -> None:
        """Render the main menu."""
        # Clear screen with dark blue background
        self.screen.fill((15, 30, 50))
        
        # Draw title
        self.draw_text(
            'LONE U-BOAT',
            self.config.SCREEN_WIDTH // 2,
            80,
            self.font_title,
            color=(200, 220, 255),
            center=True
        )
        
        # Draw subtitle
        self.draw_text(
            'A Solitaire Submarine Warfare Game',
            self.config.SCREEN_WIDTH // 2,
            140,
            self.font_small,
            color=(150, 170, 200),
            center=True
        )
        
        # Draw mission selection panel
        panel_width = 600
        panel_height = 500
        panel_x = (self.config.SCREEN_WIDTH - panel_width) // 2
        panel_y = 200
        
        self.draw_panel(panel_x, panel_y, panel_width, panel_height)
        
        # Draw "SELECT MISSION" header
        self.draw_text(
            'SELECT MISSION',
            self.config.SCREEN_WIDTH // 2,
            panel_y + 30,
            self.font_large,
            color=(220, 220, 255),
            center=True
        )
        
        # Draw mission buttons
        self.button_rects = []
        button_y = panel_y + 90
        button_height = 70
        button_spacing = 10
        button_width = panel_width - 80
        button_x = panel_x + 40
        
        for i, mission in enumerate(self.missions):
            is_selected = (i + 1 == self.selected_mission)
            is_unlocked = mission['unlocked']
            
            # Button colors
            if not is_unlocked:
                color = (50, 50, 60)
                hover_color = (50, 50, 60)
                text_color = (100, 100, 120)
            elif is_selected:
                color = (70, 130, 180)
                hover_color = (90, 150, 200)
                text_color = (255, 255, 255)
            else:
                color = (50, 90, 130)
                hover_color = (70, 110, 150)
                text_color = (200, 220, 255)
            
            # Draw button
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            self.button_rects.append(button_rect)
            
            # Check hover
            mouse_pos = pygame.mouse.get_pos()
            is_hover = button_rect.collidepoint(mouse_pos) and is_unlocked
            
            # Draw button background
            pygame.draw.rect(
                self.screen,
                hover_color if is_hover else color,
                button_rect,
                border_radius=5
            )
            pygame.draw.rect(self.screen, text_color, button_rect, 2, border_radius=5)
            
            # Draw mission number and name
            mission_text = f"Mission {mission['number']}: {mission['name']}"
            text_y = button_y + 15
            
            self.draw_text(
                mission_text,
                button_x + 20,
                text_y,
                self.font_medium,
                color=text_color
            )
            
            # Draw description
            desc_color = (150, 150, 170) if not is_unlocked else (180, 200, 220)
            self.draw_text(
                mission['description'],
                button_x + 20,
                text_y + 30,
                self.font_small,
                color=desc_color
            )
            
            # Draw lock icon for locked missions
            if not is_unlocked:
                lock_text = "🔒 LOCKED"
                self.draw_text(
                    lock_text,
                    button_x + button_width - 120,
                    button_y + button_height // 2 - 10,
                    self.font_small,
                    color=(100, 100, 120)
                )
            
            button_y += button_height + button_spacing
        
        # Draw controls info at bottom
        controls_y = self.config.SCREEN_HEIGHT - 60
        self.draw_text(
            'UP/DOWN: Select Mission  |  ENTER: Start Mission  |  ESC: Quit',
            self.config.SCREEN_WIDTH // 2,
            controls_y,
            self.font_small,
            color=(150, 170, 200),
            center=True
        )
        
        pygame.display.flip()
