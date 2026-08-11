import sys
from pathlib import Path

from .parser import MapParser


def main(argv: list[str]) -> int:
    """Run simulation from a map file; return shell exit code."""
    if len(argv) != 2:
        print(f"usage: python -m fly_in <map-file>", file=sys.stderr)
        return 2

    try:
        network = MapParser.parse(Path(argv[1]))
