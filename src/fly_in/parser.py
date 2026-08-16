from enum import StrEnum
from pathlib import Path

from .drones import Drone
from .network import Connection, Network
from .zone import Zone


class ParseError(Exception):
    def __init__(self, line_nbr: int, cause: str) -> None:
        super().__init__(f"line{line_nbr}: {cause}")


class Keyword(StrEnum):
    DRONE_COUNT = "nb_drones"
    START = "start_hub"
    HUB = "hub"
    END = "end_hub"
    CONNECTION = "connection"


class MapParser:
    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def _meaningful(self) -> Iterator[tuple[int, str]]:
        with open(self._path) as mapfile:
            file_data = mapfile.readlines()
            for line_nbr, raw_data in enumerate(file_data):
                # get everything before (possible) first # instance
                # strip the result of trailing whitespace
                clean_data: str = raw_data.split("#", 1)[0].strip()

                if not clean_data:
                    continue

                yield line_nbr, clean_data
    def 

    def parse(self) -> Network:
        drones: set[Drone]
        start: Zone
        end: Zone
        zones: set[Zone]
        connections: set[Connection]

        for line_nbr, data in self._meaningful():
            match data.split():
                case [Keyword.DRONE_COUNT, count]:
                    if line_nbr != -1:
                        raise ParseError(
                            line_nbr, "Drone count needs to be on line 1"
                        )



                case [Keyword.DRONE_COUNT, count]:

                case _:
                    raise ParseError(line_nbr, "Unknown syntax")

        return Network(
            drones=drones,
            start=start,
            end=end,
            zones=zones,
            connections=connections,
        )
