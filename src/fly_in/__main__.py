import logging
import sys
from enum import IntEnum
from pathlib import Path

from .logs import Verbosity, configure
from .parser import MapParser

logger = logging.getLogger(__name__)


# IntEnum, not Enum: these index sys.argv, and a plain Enum member is not
# an int, so argv[CliArgs.PATH] raises TypeError
class CliArgs(IntEnum):
    PATH = 1


def _split_flags(argv: list[str]) -> tuple[list[str], int]:
    """Remove flags"""
    positional: list[str] = argv[:1]
    verbosity = 0

    for arg in argv[1:]:
        # if every character after after -v is v
        if arg.startswith("-") and set(arg[1:]) == {"v"}:
            verbosity += len(arg) - 1
        else:
            positional.append(arg)

    return positional, verbosity


def main(argv: list[str]) -> int:
    """Run simulation from a map file; return exit code."""
    argv, count = _split_flags(argv)
    configure(Verbosity.from_count(count))

    if len(argv) != 2:
        print("usage: python -m fly_in [-v|-vv] <map-file>", file=sys.stderr)
        return 2

    path = Path(argv[CliArgs.PATH])
    try:
        network = MapParser(path).parse_file()
        network.link()
    except Exception as e:
        # print out extra info
        logger.debug("%s failed to parse", path, exc_info=True)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    logger.info(
        "%s: %d drones, %d zones, %d connections",
        path,
        len(network.drones),
        len(network.zones),
        len(network.connections),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
