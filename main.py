"""
Lone U-Boat Game - Entry Point
A hex-based submarine warfare game using actual mission maps.

For board editing and alignment, use editor.py instead.
"""

import argparse
from core import Game


def main():
    """Start the Lone U-Boat game."""
    parser = argparse.ArgumentParser(description='Lone U-Boat - Submarine Warfare Game')
    parser.add_argument('--mission', type=int, default=1, help='Mission number to play (default: 1)')
    args = parser.parse_args()
    
    game = Game(mission_number=args.mission)
    game.run()


if __name__ == "__main__":
    main()
