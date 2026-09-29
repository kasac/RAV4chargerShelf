"""Run the pure-Python CLI without installing anything:

    python tools/rav4shelf.py all
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "src"))

from rav4shelf.cli import main  # noqa: E402

sys.exit(main())
