from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from .model import Connection, Drone, Location, Network, Zone, ZoneAttribute

_CONNECTION = TypeAdapter(Connection)


class ParseError(Exception):
    def __init__(self, line_nbr: int | None, cause: str) -> None:
        # line_nbr is None for whole-file faults, which belong to no line
        where = "end of file" if line_nbr is None else f"line {line_nbr}"
        super().__init__(f"{where}: {cause}")


class Keyword(StrEnum):
    DRONE_COUNT = "nb_drones"
    START = "start_hub"
    HUB = "hub"
    END = "end_hub"
    CONNECTION = "connection"


# ~~~~~ Text helpers ~~~~~
# ripped out since parser was growing big,
# and since they arent really about operating on class specific data


def _describe(exception: ValidationError) -> str:
    """Render pydantic's failures as "field: message" lines.

    Each error's "loc" locates the offending field, and is empty for a
    whole-model fault, so fall back to a label rather than indexing into
    an empty tuple. Aliased fields report their alias, which is the name
    the map file actually uses.
    """
    details: list[str] = []
    for error in exception.errors():
        loc = ".".join(str(part) for part in error["loc"])
        details.append(f"{loc or 'metadata'}: {error['msg']}")
    return "\n".join(details)


def _split_metadata(
    line_nbr: int, arg_string: str
) -> tuple[tuple[str, ...], tuple[str, ...] | None]:
    # split by metadata delim, if it exists
    args_str_list: list[str] = arg_string.split("[")

    # get positional args
    defs_strs: tuple[str, ...] = tuple(args_str_list[0].split())

    # return if no named
    if len(args_str_list) == 1:
        return (defs_strs, None)

    # get nameds
    meta_str: str = args_str_list[-1].strip()

    # check for correct syntax
    if not meta_str.endswith("]"):
        raise ParseError(line_nbr, "Unterminated [")

    # break down by whitespaces
    meta_strs: tuple[str, ...] = tuple(meta_str.removesuffix("]").split())

    return (defs_strs, meta_strs)


def _tokenize_metadata(
    line_nbr: int, meta_strs: tuple[str, ...]
) -> dict[str, str]:
    raw_metadata: dict[str, str] = {}

    for string in meta_strs:
        if "=" not in string:
            raise ParseError(line_nbr, "required metadata format: key=value")

        key, val = string.split("=", 1)

        if key in raw_metadata:
            raise ParseError(line_nbr, f"'{key}' specified more than once")
        raw_metadata[key] = val

    return raw_metadata


# ~~~~~ Zone helpers ~~~~~
def _parse_zone_defs(
    line_nbr: int, defs: tuple[str, ...]
) -> tuple[str, Location]:
    if len(defs) != 3:
        raise ParseError(line_nbr, "required format: name x y")

    name: str = defs[0]
    if "-" in name:
        raise ParseError(line_nbr, "'-' is not allowed in names")
    try:
        # slice off name, spread into Location
        location = Location(*(int(coord) for coord in defs[1:]))
    except ValueError as exc:
        raise ParseError(line_nbr, "coordinates must be integers") from exc

    return (name, location)


def _parse_zone_metadata(
    line_nbr: int, raw_metadata: dict[str, str]
) -> ZoneAttribute:
    try:
        # pydantic does all the type coercion
        return ZoneAttribute.model_validate(raw_metadata)
    except ValidationError as exc:
        # make newline seprated string with all errors
        raise ParseError(line_nbr, _describe(exc)) from exc


class MapParser:
    """Builds a Network from a map file, validating as it reads.

    Most of the map format's rules span several lines: names must be
    unique, connections may only join zones defined earlier, the same
    connection must not appear twice, and there must be exactly one start
    and one end. Those checks need the zones and connections seen so far,
    which is the state this object accumulates while parsing.

    Every method here touches that state; the text helpers above do not,
    which is why they are module-level functions rather than methods.
    """

    def __init__(self, path: Path) -> None:
        self._path: Path = path
        self._drones: frozenset[Drone] = frozenset()
        self._zones: dict[str, Zone] = {}
        # keyed by the unordered pair of names, so a-b and b-a collide
        self._connections: dict[frozenset[str], Connection] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    def _reset(self) -> None:
        """Clear accumulated state so one parser can be reused."""
        self._drones = frozenset()
        self._zones = {}
        self._connections = {}
        self._start = None
        self._end = None

    def _cleaned_data(self) -> Iterator[tuple[int, str]]:
        with open(self._path) as mapfile:
            file_data = mapfile.readlines()
            # 1-based: error messages name the line as a human counts it
            for line_nbr, raw_data in enumerate(file_data, start=1):
                # get everything before (possible) first # instance
                # strip the result of trailing whitespace
                clean_data: str = raw_data.split("#", 1)[0].strip()

                if not clean_data:
                    continue

                yield line_nbr, clean_data

    def _parse_drones(self, line_nbr: int, args_string: str) -> None:
        if self._drones:
            raise ParseError(line_nbr, "nb_drones specified more than once")

        try:
            count = int(args_string)
        except ValueError as exc:
            raise ParseError(line_nbr, "nb_drones must be an integer") from exc

        if count < 1:
            raise ParseError(line_nbr, "nb_drones must be positive")

        self._drones = frozenset(Drone(id=nbr) for nbr in range(1, count + 1))

    # ~~~~~ Parser functions ~~~~~
    def _parse_zone(
        self, line_nbr: int, keyword: Keyword, args_string: str
    ) -> None:
        defs_str, meta_str = _split_metadata(line_nbr, args_string)
        name, coordinates = _parse_zone_defs(line_nbr, defs_str)

        # init with default vals, overwrite if metadata options found
        attributes = ZoneAttribute()
        if meta_str is not None:
            raw_meta = _tokenize_metadata(line_nbr, meta_str)
            attributes = _parse_zone_metadata(line_nbr, raw_meta)

        if name in self._zones:
            raise ParseError(line_nbr, f"duplicate zone name {name!r}")

        if keyword is Keyword.START and self._start is not None:
            raise ParseError(line_nbr, "more than one start_hub")
        if keyword is Keyword.END and self._end is not None:
            raise ParseError(line_nbr, "more than one end_hub")

        zone = Zone(name=name, coordinates=coordinates, attributes=attributes)
        self._zones[name] = zone

        if keyword is Keyword.START:
            self._start = zone
        elif keyword is Keyword.END:
            self._end = zone

    def _parse_connection(self, line_nbr: int, args_string: str) -> None:
        defs_str, meta_str = _split_metadata(line_nbr, args_string)

        if len(defs_str) != 1:
            raise ParseError(line_nbr, "required format: zone1-zone2")

        names = defs_str[0].split("-")
        if len(names) != 2 or not all(names):
            raise ParseError(line_nbr, "required format: zone1-zone2")

        pair = frozenset(names)
        if len(pair) != 1 and pair in self._connections:
            raise ParseError(line_nbr, f"duplicate connection {defs_str[0]!r}")

        try:
            zones = frozenset(self._zones[name] for name in names)
        except KeyError as exc:
            raise ParseError(
                line_nbr, f"connection to undefined zone {exc.args[0]!r}"
            ) from exc

        if len(zones) != 2:
            raise ParseError(line_nbr, "a zone cannot connect to itself")

        raw_meta = (
            {} if meta_str is None else _tokenize_metadata(line_nbr, meta_str)
        )
        # validate through an adapter so the max_link_capacity alias, the
        # str->int coercion and extra="forbid" all apply to file metadata
        try:
            connection = _CONNECTION.validate_python(
                {"name": defs_str[0], "zones": zones, **raw_meta}
            )
        except ValidationError as exc:
            raise ParseError(line_nbr, _describe(exc)) from exc

        self._connections[pair] = connection

    # ~~~~~ Main parser and return wrapper ~~~~~
    def parse_file(self) -> Network:
        self._reset()

        for index, (line_nbr, line_string) in enumerate(self._cleaned_data()):
            # split into keyword and rest
            parts = line_string.split(maxsplit=1)
            keyword = parts[0]
            if not keyword.endswith(":"):
                raise ParseError(
                    line_nbr, 'Required format: "keyword: config"'
                )
            if len(parts) != 2:
                raise ParseError(line_nbr, "Keyword needs an argument")

            keyword = keyword.removesuffix(":")
            args_string = parts[1]

            if index == 0 and keyword != Keyword.DRONE_COUNT:
                raise ParseError(line_nbr, "first line must define nb_drones")

            # match keywords and create values
            match keyword:
                case Keyword.DRONE_COUNT:
                    self._parse_drones(line_nbr, args_string)
                case Keyword.START | Keyword.HUB | Keyword.END:
                    self._parse_zone(line_nbr, Keyword(keyword), args_string)
                case Keyword.CONNECTION:
                    self._parse_connection(line_nbr, args_string)
                case _:
                    raise ParseError(line_nbr, "Unknown syntax")

        return self._build_network()

    def _build_network(self) -> Network:
        if not self._drones:
            raise ParseError(None, "no nb_drones defined")
        if self._start is None:
            raise ParseError(None, "no start_hub defined")
        if self._end is None:
            raise ParseError(None, "no end_hub defined")

        return Network(
            drones=self._drones,
            start=self._start,
            end=self._end,
            zones=frozenset(self._zones.values()),
            connections=frozenset(self._connections.values()),
            # all drones begin in the start zone
            occupancy={drone: self._start for drone in self._drones},
        )
