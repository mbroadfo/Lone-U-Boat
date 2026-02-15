"""
Quick launcher to test Interactive AI Mode UI.

Launches the game with interactive_ai_mode=True so you can see
the purple "EXECUTE AI ACTION" button in action.

This script is not needed for normal play - just run main.py.
Interactive mode is now the default!
"""

from core.screen_manager import ScreenManager

def main():
    """Start the game with screen manager (interactive AI mode is now default)."""
    # The game now defaults to interactive_ai_mode=True in unified_game.py
    screen_manager = ScreenManager()
    screen_manager.run()

if __name__ == "__main__":
    main()
