"""
Centralized event logging system with turn/phase context.

Provides standardized logging format with:
- Turn and phase markers [T2:ESCORT]
- Dice roll formatting [4] or [1,6]  
- Indentation for readability
- Turn separators
"""

from typing import List


class EventLogger:
    """Centralized event logger with turn/phase context."""
    
    def __init__(self):
        """Initialize event logger."""
        self.current_turn: int = 0
        self.current_phase: str = ""
        self.mission_started: bool = False
        self.indent_level: int = 0
    
    def set_turn_phase(self, turn: int, phase: str):
        """
        Set current turn and phase for logging context.
        
        Args:
            turn: Current turn number
            phase: Current phase name (e.g., "ESCORT", "MERCHANT")
        """
        self.current_turn = turn
        self.current_phase = phase.upper().replace(" PHASE", "").replace(" ", "_")
    
    def format_event(self, message: str, indent: int = 0) -> str:
        """
        Format an event message with turn/phase context and indentation.
        
        Args:
            message: Event message
            indent: Additional indentation level (0-3)
            
        Returns:
            Formatted event string with [T#:PHASE] prefix and indentation
        """
        # Create context marker
        if self.current_turn > 0 and self.current_phase:
            marker = f"[T{self.current_turn}:{self.current_phase}]"
        else:
            marker = "[EVENT]"
        
        # Calculate total indentation (2 spaces per level)
        total_indent = (self.indent_level + indent) * 2
        indent_str = " " * total_indent
        
        return f"{marker} {indent_str}{message}"
    
    def get_turn_separator(self) -> str:
        """Get separator line for turn boundaries."""
        return "[TURN] " + ("-" * 60)
    
    def get_mission_restart_marker(self) -> str:
        """Get mission restart marker with separator."""
        lines: List[str] = []
        lines.append("")
        lines.append("=" * 64)
        lines.append("[MISSION RESTARTED]")
        lines.append("=" * 64)
        lines.append("")
        return "\n".join(lines)
    
    @staticmethod
    def format_dice_1d6(result: int) -> str:
        """Format single d6 roll: [4]"""
        return f"[{result}]"
    
    @staticmethod
    def format_dice_2d6(die1: int, die2: int) -> str:
        """Format 2d6 roll: [3,5] = 8"""
        return f"[{die1},{die2}] = {die1 + die2}"
    
    @staticmethod
    def format_dice_3d6(results: List[int]) -> str:
        """Format 3d6 roll: [1,3,4]"""
        return f"[{','.join(str(r) for r in results)}]"
    
    @staticmethod
    def format_dice_list(results: List[int]) -> str:
        """Format list of dice results: [2,4,6]"""
        return f"[{','.join(str(r) for r in results)}]"


# Global singleton instance
_event_logger = EventLogger()


def get_event_logger() -> EventLogger:
    """Get global event logger instance."""
    return _event_logger
