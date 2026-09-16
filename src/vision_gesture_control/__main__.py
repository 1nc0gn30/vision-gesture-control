"""
Main entry point for executing module via python -m vision_gesture_control
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
