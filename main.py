"""
Lone U-Boat Game - Entry Point
A hex-based submarine warfare game using actual mission maps.

For board editing and alignment, use editor.py instead.
"""

from core.screen_manager import ScreenManager


def main():
    """Start the Lone U-Boat game with menu system."""
    screen_manager = ScreenManager()
    screen_manager.run()


if __name__ == "__main__":
    main()
