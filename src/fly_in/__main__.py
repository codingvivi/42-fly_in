import sys
from enum import Enum
from pathlib import Path

from .parser import MapParser


class CliArgs(Enum):
    PATH = 1


def main(argv: list[str]) -> int:
    """Run simulation from a map file; return shell exit code."""
    if len(argv) != 2:
        print("usage: python -m fly_in <map-file>", file=sys.stderr)
        return 2

    try:
        network = MapParser(Path(argv[CliArgs.PATH])).parse_file()
        network.link()
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
