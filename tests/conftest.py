"""
Pytest configuration for LoneUBoat test suite.

Sets SDL to use headless (dummy) drivers before any test module is imported.
Without this, pygame.init() inside test_combat_resolution.py et al. will
initialize the SDL display subsystem on Windows.

Also reconfigures stdout/stderr to UTF-8 so that test output containing
Unicode checkmarks (✓ ✅) doesn't trigger UnicodeEncodeError on Windows
(which defaults to cp1252 and cascades into "underlying buffer has been
detached" in pytest's teardown).
"""
import io
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Reconfigure in-place (same object — pytest's TerminalWriter keeps its
# cached reference valid) so Unicode test output survives the cp1252 default.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, io.UnsupportedOperation):
        pass  # already replaced or not a real TextIOWrapper
