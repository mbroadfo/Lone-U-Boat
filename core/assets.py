"""
Asset loading and management for images, fonts, and other game resources.
"""

import pygame
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .models import Depth


class AssetManager:
    """Manages loading and caching of game assets (images, fonts, sounds)."""
    
    def __init__(self, config: Any):
        """Initialize asset manager with configuration.
        
        Args:
            config: Configuration module (e.g., board_config)
        """
        self.config = config
        self.u_boat_images: Dict[Depth, pygame.Surface] = {}
        self.ship_images: Dict[str, pygame.Surface] = {}
        self.marker_images: Dict[str, pygame.Surface] = {}
        self.font: Optional[pygame.font.Font] = None
        self.font_large: Optional[pygame.font.Font] = None
        
    def load_all_assets(self):
        """Load all game assets at once."""
        self.u_boat_images = self.load_u_boat_images()
        self.ship_images = self.load_ship_images()
        self.marker_images = self.load_marker_images()
        self.font, self.font_large = self.load_fonts()
        
    def load_u_boat_images(self) -> Dict[Depth, pygame.Surface]:
        """Load U-Boat images for each depth level."""
        images: Dict[Depth, pygame.Surface] = {}
        depth_files: Dict[Depth, str] = {
            Depth.SURFACED: self.config.ASSETS['u_boat_surfaced'],
            Depth.PERISCOPE: self.config.ASSETS['u_boat_periscope'],
            Depth.MEDIUM: self.config.ASSETS['u_boat_medium'],
            Depth.DEEP: self.config.ASSETS['u_boat_deep'],
        }
        
        # Target size to fit in hex
        target_size = self.config.UI['u_boat_image_size']
        
        for depth, filepath in depth_files.items():
            path = Path(filepath)
            if path.exists():
                image = pygame.image.load(path).convert_alpha()
                # Scale down significantly to fit in hex
                original_size = max(image.get_width(), image.get_height())
                scale = target_size / original_size
                new_width = int(image.get_width() * scale)
                new_height = int(image.get_height() * scale)
                images[depth] = pygame.transform.smoothscale(image, (new_width, new_height))
            else:
                # Create placeholder if image doesn't exist
                surface = pygame.Surface((40, 40), pygame.SRCALPHA)
                # Use ship color or default gray for placeholder
                color = self.config.COLORS.get('u_boat', self.config.COLORS.get('ship', (128, 128, 128)))
                pygame.draw.circle(surface, color, (20, 20), 15)
                images[depth] = surface
        
        return images
    
    def load_ship_images(self) -> Dict[str, pygame.Surface]:
        """Load ship images for each ship type."""
        images: Dict[str, pygame.Surface] = {}
        ship_types = ['merchant', 'corvette', 'destroyer']
        
        # Target size to fit in hex
        target_size = self.config.UI['u_boat_image_size']
        
        for ship_type in ship_types:
            # Load normal and damaged versions
            for suffix in ['', '_damaged']:
                key = f"{ship_type}{suffix}"
                asset_key = key if suffix else ship_type
                filepath = self.config.ASSETS.get(asset_key)
                
                if filepath:
                    path = Path(filepath)
                    if path.exists():
                        image = pygame.image.load(path).convert_alpha()
                        # Scale to fit in hex
                        image = pygame.transform.smoothscale(image, (target_size, target_size))
                        images[key] = image
                    else:
                        # Create placeholder
                        surface = pygame.Surface((target_size, target_size), pygame.SRCALPHA)
                        pygame.draw.circle(surface, self.config.COLORS['ship'], 
                                         (target_size//2, target_size//2), target_size//3)
                        images[key] = surface
        
        # Load B-24 aircraft image
        b24_path = Path(self.config.ASSETS.get('b24', 'assets/B24.png'))
        if b24_path.exists():
            image = pygame.image.load(b24_path).convert_alpha()
            image = pygame.transform.smoothscale(image, (target_size, target_size))
            images['b24'] = image
        else:
            # Create placeholder
            surface = pygame.Surface((target_size, target_size), pygame.SRCALPHA)
            pygame.draw.circle(surface, (100, 100, 255), 
                             (target_size//2, target_size//2), target_size//3)
            images['b24'] = surface
        
        return images
    
    def load_marker_images(self) -> Dict[str, pygame.Surface]:
        """Load marker images for status boxes."""
        markers: Dict[str, pygame.Surface] = {}
        marker_files: Dict[str, str] = {
            'detection': self.config.ASSETS['detection_marker'],
            'damaged': self.config.ASSETS['damaged_marker'],
            'kia': self.config.ASSETS['kia_marker'],
            'torpedo': self.config.ASSETS['torpedo_marker']
        }
        
        for marker_type, filename in marker_files.items():
            path = Path(filename)
            if path.exists():
                markers[marker_type] = pygame.image.load(path).convert_alpha()
            else:
                # Create placeholder if image doesn't exist
                surface = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(surface, (255, 255, 0), (10, 10), 8)
                markers[marker_type] = surface
        
        return markers
    
    def load_fonts(self) -> Tuple[pygame.font.Font, pygame.font.Font]:
        """Load game fonts."""
        font = pygame.font.Font(None, self.config.UI['font_size'])
        font_large = pygame.font.Font(None, self.config.UI['font_size_large'])
        return font, font_large
    
    @staticmethod
    def load_mission_map(map_path: str, max_width: int = 900, max_height: int = 700) -> pygame.Surface:
        """Load and scale a mission map image.
        
        Args:
            map_path: Path to the mission map image
            max_width: Maximum width for scaling
            max_height: Maximum height for scaling
            
        Returns:
            Pygame surface with the loaded (and possibly scaled) map
        """
        path = Path(map_path)
        if not path.exists():
            # Create placeholder if map doesn't exist
            surface = pygame.Surface((800, 600))
            surface.fill((100, 150, 200))
            return surface
        
        image = pygame.image.load(path)
        # Scale down if too large
        if image.get_width() > max_width or image.get_height() > max_height:
            scale = min(max_width / image.get_width(), 
                       max_height / image.get_height())
            new_size = (int(image.get_width() * scale), 
                       int(image.get_height() * scale))
            image = pygame.transform.smoothscale(image, new_size)
        
        return image
