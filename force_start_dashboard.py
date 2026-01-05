#!/usr/bin/env python3
"""
Force start Balaji's Tools dashboard - bypasses single instance check
"""

import sys
import os
from pathlib import Path

# Add current directory to path so we can import balaji_tools
sys.path.insert(0, os.path.dirname(__file__))

# Import and run with force flag
if __name__ == '__main__':
    # Set force flag in sys.argv
    sys.argv.append('--force')

    # Import and run main
    from balaji_tools import main
    main()