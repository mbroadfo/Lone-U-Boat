"""
Board Layout Configuration - Resolution-independent layout system.

This module defines the configuration structure for map, hex grid, and status box
calibration. All positions are stored in map-relative coordinates at a reference
calibration size, allowing for resolution-independent scaling.

The layout system separates:
1. Calibration (this module) - "where things are on the map image"
2. Runtime Layout (board_layout.py) - "where things are on screen at current resolution"
3. Rendering (renderer.py) - "draw things at computed positions"
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Any
import json
from pathlib import Path


@dataclass
class MapCalibration:
    """Native map image size used for calibration.
    
    This represents the size of the map image at the time when hex grid and
    status boxes were aligned. All other calibration coordinates are relative
    to this size.
    """
    width: int   # Map width in pixels at calibration time
    height: int  # Map height in pixels at calibration time


@dataclass
class HexGridCalibration:
    """Hex grid calibration data.
    
    All coordinates are in map pixels (at calibration map size), not screen pixels.
    """
    hex_size: float  # Hex radius at calibration size
    origin_in_map: Tuple[float, float]  # (x, y) offset from map top-left corner
    

@dataclass
class StatusBoxCalibration:
    """Status box positions relative to the map.
    
    All coordinates are in map pixels (at calibration map size), not screen pixels.
    Each box is: (x, y, width, height) from map top-left corner.
    """
    boxes_in_map: Dict[str, Tuple[float, float, float, float]]


@dataclass
class MissionLayoutConfig:
    """Complete layout configuration for a mission.
    
    This bundles all the calibration data needed to position the map, hex grid,
    and status boxes at any screen resolution.
    """
    map_calib: MapCalibration
    hex_grid_calib: HexGridCalibration
    status_calib: StatusBoxCalibration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'map_calibration': {
                'width': self.map_calib.width,
                'height': self.map_calib.height
            },
            'hex_grid_calibration': {
                'hex_size': self.hex_grid_calib.hex_size,
                'origin_in_map': list(self.hex_grid_calib.origin_in_map)
            },
            'status_box_calibration': {
                'boxes_in_map': {
                    name: list(rect) for name, rect in self.status_calib.boxes_in_map.items()
                }
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MissionLayoutConfig':
        """Create from dictionary loaded from JSON."""
        map_calib = MapCalibration(
            width=data['map_calibration']['width'],
            height=data['map_calibration']['height']
        )
        
        hex_grid_calib = HexGridCalibration(
            hex_size=data['hex_grid_calibration']['hex_size'],
            origin_in_map=tuple(data['hex_grid_calibration']['origin_in_map'])
        )
        
        status_calib = StatusBoxCalibration(
            boxes_in_map={
                name: tuple(rect) for name, rect in data['status_box_calibration']['boxes_in_map'].items()
            }
        )
        
        return MissionLayoutConfig(
            map_calib=map_calib,
            hex_grid_calib=hex_grid_calib,
            status_calib=status_calib
        )


def load_mission_layout(mission_number: int) -> MissionLayoutConfig:
    """Load mission layout from JSON file.
    
    Args:
        mission_number: Mission number to load
        
    Returns:
        MissionLayoutConfig with calibration data
        
    Raises:
        FileNotFoundError: If layout file doesn't exist
    """
    path = Path("missions") / f"mission_{mission_number}_layout.json"
    
    if not path.exists():
        raise FileNotFoundError(
            f"Layout file not found: {path}\n"
            f"Run the game in alignment mode (F2) to create initial calibration."
        )
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return MissionLayoutConfig.from_dict(data)


def save_mission_layout(mission_number: int, config: MissionLayoutConfig) -> None:
    """Save mission layout to JSON file.
    
    Args:
        mission_number: Mission number
        config: Layout configuration to save
    """
    path = Path("missions") / f"mission_{mission_number}_layout.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    print(f"Saved layout configuration to: {path}")
