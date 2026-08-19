from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from .drones import Drone
from .hub import Hub, Location, ZoneType
from .network import Connection, Network


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

    def _cleaned_data(self) -> Iterator[tuple[int, str]]:
        with open(self._path) as mapfile:
            file_data = mapfile.readlines()
            for line_nbr, raw_data in enumerate(file_data):
                # get everything before (possible) first # instance
                # strip the result of trailing whitespace
                clean_data: str = raw_data.split("#", 1)[0].strip()

                if not clean_data:
                    continue

                yield line_nbr, clean_data

    @staticmethod
    def _parse_hub(
        line_nr: int,
        name: str,
        coordinates: Location,
        type: ZoneType,
        color: str,
        max_drones: int,
    ) -> Hub: ...

    def parse_file(self) -> Network:
        drones: set[Drone]
        start: Hub
        end: Hub
        hubs: set[Hub]
        connections: set[Connection]

        for line_nbr, data in self._cleaned_data():
            # split into keyword and rest
            keyword, config_data = data.split(maxsplit=1)
            if not keyword.endswith(":"):
                raise ParseError(
                    line_nbr, 'Required format: "keyword: config"'
                )
            if not config_data:
                raise ParseError(line_nbr, "Keyword needs an argument")

            # match keywords and create values
            match [keyword, config_data.split()]:
                #
                case [Keyword.DRONE_COUNT, *count]:
                    if line_nbr != -1:
                        raise ParseError(
                            line_nbr, "Drone count needs to be on line 1"
                        )
                    drones = set(
                        [Drone(id=int(drone_nr)) for drone_nr in count]
                    )

                case [Keyword.START | Keyword.HUB | Keyword.END, config]:
                    _parse_hub(
                        line_nbr,
                    )

                case _:
                    raise ParseError(line_nbr, "Unknown syntax")

        return Network(
            drones=drones,
            start=start,
            end=end,
            hubs=hubs,
            connections=connections,
        )
