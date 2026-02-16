"""
Quick launcher to test Interactive AI Mode UI.

Launches the game to test the purple "EXECUTE AI ACTION" button.
The game uses queue-based execution for solitaire gameplay.

This script is not needed for normal play - just run main.py.
Interactive mode is now the only mode!
"""

from core.screen_manager import ScreenManager

def main():
    """Start the game with screen manager (queue-based AI execution)."""
    # The game now uses interactive mode by default (queue-based execution)
    screen_manager = ScreenManager()
    screen_manager.run()

if __name__ == "__main__":
    main()
