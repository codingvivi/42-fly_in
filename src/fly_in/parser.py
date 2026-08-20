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

    # @property
    # def is_hub(self) -> bool:
    #     return self in (Keyword.START, Keyword.HUB, Keyword.END)


# ZONES = Keyword.START | Keyword.HUB | Keyword.END | Keyword.CONNECTION


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
    def _parse_drones(line_nbr: int, count) -> set[Drone]:
        if line_nbr != -1:
            raise ParseError(line_nbr, "Drone count needs to be on line 1")
        if len(count):
            ...
        return set([Drone(id=int(drone_nr)) for drone_nr in count])

    @staticmethod
    def _separate_metadata(
        line_nbr: int, config: list
    ) -> tuple[list, list] | list:
        # find opening [
        metadata_start = next(
            (tok for tok in config if tok.startswith("[")), None
        )
        if not metadata_start:
            return config

        metadata_end = config[-1]
        if not metadata_end.endswith("]"):
            raise ParseError(line_nbr, "Unterminated [")

        split_index: int = config.index(metadata_start)
        defs: list = config[:split_index]
        metadata: list = config[split_index + 1 :]

        return (defs, metadata)

    @staticmethod
    def _parse_metadata(
        line_nrb: int, metadata: list[str]
    ) -> dict[str, int | str | None]: ...

    @staticmethod
    def _parse_zone(
        line_nbr: int, defs: list, metadata: dict | None
    ) -> Hub: ...

    def parse_file(self) -> Network:
        drones: set[Drone]
        start: Hub
        end: Hub
        hubs: set[Hub]
        connections: set[Connection]

        for line_nbr, raw_string in self._cleaned_data():
            # split into keyword and rest
            keyword, raw_string = raw_string.split(maxsplit=1)
            if not keyword.endswith(":"):
                raise ParseError(
                    line_nbr, 'Required format: "keyword: config"'
                )
            if not raw_string:
                raise ParseError(line_nbr, "Keyword needs an argument")

            keyword.strip(":")

            data_strings: list[str] = raw_string.split()

            # match keywords and create values
            match keyword:
                #
                case Keyword.DRONE_COUNT:
                    drones = self._parse_drones(line_nbr, data_strings)
                case Keyword.START | Keyword.HUB | Keyword.END:
                    hub = self._parse_hub(line_nbr, *self._parse_metadata())
                case Keyword.CONNECTION:
                    conn = self._parse_connection(line_nbr, config_data)
                case _:
                    raise ParseError(line_nbr, "Unknown syntax")

        return Network(
            drones=drones,
            start=start,
            end=end,
            hubs=hubs,
            connections=connections,
        )
