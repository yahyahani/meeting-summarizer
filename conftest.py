"""
Pytest configuration: makes the src/ directory importable from tests,
so test files can do `from summarize import ...` etc.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
