from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError

from .drones import Drone
from .hub import Hub, HubAttribute, Location
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
    def _parse_zone_defs(
        line_nbr: int, defs: tuple[str, ...]
    ) -> tuple[str, Location]:
        if len(defs) != 3:
            raise ParseError(line_nbr, "required format: name x y")

        id: str = defs[0]
        if "-" in id:
            raise ParseError(line_nbr, "'-' is not allowed in names")
        location = Location(*(int(coord) for coord in defs[1:]))

        return (id, location)

    @staticmethod
    def _split_metadata(
        line_nbr: int, arg_string: str
    ) -> tuple[tuple[str, ...], tuple[str, ...] | None]:
        args_str_list: list[str] = arg_string.split("[")

        defs_strs: tuple[str, ...] = tuple(args_str_list[0].split())

        if len(args_str_list) == 1:
            return (defs_strs, None)

        meta_str: str = args_str_list[-1].strip()

        if not meta_str.endswith("]"):
            raise ParseError(line_nbr, "Unterminated [")

        meta_strs: tuple[str, ...] = tuple(meta_str.removesuffix("]").split())

        return (defs_strs, meta_strs)

    @staticmethod
    def tokenize_metadata(
        line_nbr: int, meta_strs: tuple[str, ...]
    ) -> dict[str, str]:
        raw_metadata: dict[str, str] = {}

        for string in meta_strs:
            if "=" not in string:
                raise ParseError(
                    line_nbr, "required metadata format: key=value"
                )
            key, val = string.split("=", 1)
            if key in raw_metadata:
                raise ParseError(line_nbr, f"'{key}' specified more than once")
            raw_metadata[key] = val

        return raw_metadata

    @staticmethod
    def _parse_hub_metadata(
        line_nbr: int, raw_metadata: dict[str, str]
    ) -> HubAttribute:
        try:
            return HubAttribute.model_validate(raw_metadata)
        except ValidationError as exc:
            detail = "\n".join(
                f"{error['loc'][0]}: {error['msg']}" for error in exc.errors()
            )
            raise ParseError(line_nbr, detail) from exc

    @staticmethod
    def _parse_hub(
        line_nbr: int, raw_def_data: str, metadata: HubAttribute
    ) -> Hub: ...

    def parse_file(self) -> Network:
        drones: set[Drone]
        start: Hub
        end: Hub
        hubs: set[Hub]
        connections: set[Connection]

        for line_nbr, line_string in self._cleaned_data():
            # split into keyword and rest
            keyword, args_string = line_string.split(maxsplit=1)
            if not keyword.endswith(":"):
                raise ParseError(
                    line_nbr, 'Required format: "keyword: config"'
                )
            if not args_string:
                raise ParseError(line_nbr, "Keyword needs an argument")

            keyword.strip(":")

            # match keywords and create values
            match keyword:
                #
                case Keyword.DRONE_COUNT:
                    count: int = int(*args_string)
                    drones = self._parse_drones(line_nbr, count)
                case Keyword.START | Keyword.HUB | Keyword.END:
                    defs_str, meta_str = self._split_metadata(
                        line_nbr, args_string
                    )
                    defs = self._parse_zone_defs(line_nbr, defs_str)
                    # init with defaul vals
                    meta = HubAttribute()
                    # overwrite if metadata options found
                    if meta_str is not None:
                        raw_meta = self.tokenize_metadata(line_nbr, meta_str)
                        meta = self._parse_hub_metadata(line_nbr, raw_meta)
                    # write 1i
                    hub = self._parse_hub(line_nbr, defs, meta)
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
