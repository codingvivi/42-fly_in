"""Loggin setup for CLI"""

import logging
import sys
from enum import IntEnum


# logging doesn't unwrap enums
# so i would have to .value during every usage:
# logging.basicConfig(level=Verbosity.QUIET.value)
# IntEnum fixes this
class Verbosity(IntEnum):
    """A log level, named for how many -v flags select it"""

    QUIET = logging.WARNING
    VERBOSE = logging.INFO
    DEBUG = logging.DEBUG

    @classmethod
    def from_count(cls, count: int) -> "Verbosity":
        """Clamp to loudest log level"""
        levels = (cls.QUIET, cls.VERBOSE, cls.DEBUG)
        return levels[min(count, len(levels) - 1)]


def configure(verbosity: Verbosity) -> None:
    """Set logging config"""
    logging.basicConfig(
        level=verbosity,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
