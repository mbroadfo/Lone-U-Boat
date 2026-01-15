"""
Scripted U-Boat Captain - Follows predetermined instructions.
Currently uses same logic as UBoatAI but allows for future scripting.
"""

from typing import TYPE_CHECKING, Optional
from .uboat_ai import UBoatAI

if TYPE_CHECKING:
    from .game_state import Game

class ScriptedCaptain(UBoatAI):
    """
    A captain based on UBoatAI for now.
    Future: Add scripted behavior for deterministic testing.
    """
    
    def __init__(self, game: 'Game', action_catalog: Optional[object] = None):
        super().__init__(game)
        self.script_phase = "default"  # For future scripting

