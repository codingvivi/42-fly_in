import re
from collections.abc import Callable
from pathlib import Path

import pytest
from helpers import (
    color,
    end,
    hub,
    link,
    map,
    max_drones,
    max_link_capacity,
    named_arg,
    nb_drones,
    start,
    zone,
)

from fly_in.parser import MapParser, ParseError

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
SHIPPED_MAPS = sorted(MAPS_DIR.rglob("*.txt"))

# types for mypy
WriteMap = Callable[[str], Path]
LineBuilder = Callable[..., str]


# p = Path('data/maps/easy/01_linear_path.txt')
# p.stem     # '01_linear_path'
# p.name     # '01_linear_path.txt'
# p.suffix   # '.txt'
# p.parent   # Path('data/maps/easy')
@pytest.mark.parametrize("path", SHIPPED_MAPS, ids=lambda p: p.stem)
def test_42_maps_parse(path: Path) -> None:
    # should not raise, otherwise test stops and fails
    network = MapParser(path).parse_file()

    # start and end present
    assert network.start in network.zones
    assert network.end in network.zones
    assert network.start is not network.end

    # connection set is subset of zones
    # for sets <= means "is subset"
    for conn in network.connections:
        assert conn.zones <= network.zones, f"unknown zone in {conn.name}"

    # all drones placed (dict key set should be same as set of drones added)
    assert set(network.occupancy) == network.drones

    # all drones at start after read (set of drone locations == start)
    assert set(network.occupancy.values()) == {network.start}

    # check if drones are present (set of int ids == 1 indexed range set)
    tgt_drones = set(range(1, len(network.drones) + 1))
    assert {d.id for d in network.drones} == tgt_drones


def test_missing_map_text(write_map: WriteMap) -> None:
    with pytest.raises(ParseError, match="no nb_drones defined"):
        MapParser(write_map("")).parse_file()


@pytest.mark.parametrize(
    ("missing", "error_text"),
    [
        # dropping a hub also drops the default connection, which would
        # otherwise fail first on the zone that is no longer defined
        ({"nb_line": None}, "line 1: first line must define nb_drones"),
        (
            {"start_line": None, "link_line": None},
            "end of file: no start_hub defined",
        ),
        (
            {"end_line": None, "link_line": None},
            "end of file: no end_hub defined",
        ),
        (
            {"link_line": None},
            "end of file: unconnected zone(s): end, start",
        ),
    ],
    ids=["nb_drones", "start_hub", "end_hub", "connection"],
)
def test_missing_lines(
    write_map: WriteMap, missing: dict[str, None], error_text: str
) -> None:
    # re.escape to escape special chars
    with pytest.raises(ParseError, match=re.escape(error_text)):
        # unpack dict as kwargs
        MapParser(write_map(map(**missing))).parse_file()


def test_orphan(write_map: WriteMap) -> None:
    with pytest.raises(
        ParseError,
        match=re.escape("end of file: unconnected zone(s): testhub"),
    ):
        MapParser(write_map(map(hub()))).parse_file()


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        # add builders that reappend default map() params
        ((nb_drones(),), "line 5: nb_drones specified more than once"),
        ((start(),), "line 5: duplicate zone name 'start'"),
        ((start(name="other"),), "line 5: more than one start_hub"),
        ((end(),), "line 5: duplicate zone name 'end'"),
        ((end(name="other"),), "line 5: more than one end_hub"),
        ((link("start", "end"),), "line 5: duplicate connection 'start-end'"),
        ((link("end", "start"),), "line 5: duplicate connection 'end-start'"),
        (
            (hub("a"), link("start", "a"), hub("a")),
            "line 7: duplicate zone name 'a'",
        ),
        (
            (hub(meta=[max_drones(1), max_drones(2)]),),
            "line 5: 'max_drones' specified more than once",
        ),
    ],
    ids=[
        "nb_drones",
        "start_same_name",
        "start_new_name",
        "end_same_name",
        "end_new_name",
        "connection",
        "connection_reversed",
        "hub_name",
        "metadata_key",
    ],
)
def test_duplicate_definition(
    write_map: WriteMap, extra: tuple[str, ...], expected: str
) -> None:
    with pytest.raises(ParseError, match=re.escape(expected)):
        MapParser(write_map(map(*extra))).parse_file()


def test_late_nb_line(write_map: WriteMap) -> None:
    with pytest.raises(
        ParseError, match="line 1: first line must define nb_drones"
    ):
        MapParser(write_map(map(nb_drones(2), nb_line=None))).parse_file()


@pytest.mark.parametrize(
    ("count", "error_text"),
    [
        # nb_drones is the first line, so every fault here is line 1
        ("abc", "line 1: nb_drones must be an integer"),
        ("2 3", "line 1: nb_drones must be an integer"),
        (1.5, "line 1: nb_drones must be an integer"),
        # an empty value leaves a bare keyword, caught before _parse_drones
        ("", "line 1: Keyword needs an argument"),
        (0, "line 1: nb_drones must be positive"),
        (-5, "line 1: nb_drones must be positive"),
    ],
    ids=["text", "two_values", "float", "empty", "zero", "negative"],
)
def test_bad_drone_count(
    write_map: WriteMap, count: object, error_text: str
) -> None:
    map_txt = map(nb_line=nb_drones(count))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


@pytest.mark.parametrize(
    ("builder", "map_argname", "line_nbr"),
    [
        (start, "start_line", 2),
        (end, "end_line", 3),
        (hub, None, 5),
    ],
    ids=["start", "end", "hub"],
)
@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"x": None}, "coordinates must be integers"),
        ({"y": None}, "coordinates must be integers"),
        ({"x": "abc"}, "coordinates must be integers"),
        ({"x": 1.5}, "coordinates must be integers"),
        ({"name": "a-b"}, "'-' is not allowed in names"),
        ({"name": "a b"}, "required format: name x y"),
    ],
    ids=[
        "x_none",
        "y_none",
        "x_text",
        "x_float",
        "name_dash",
        "name_space",
    ],
)
def test_bad_positional_zone(
    write_map: WriteMap,
    builder: LineBuilder,
    map_argname: str | None,
    line_nbr: int,
    kwargs: dict[str, object],
    reason: str,
) -> None:
    # generate text from current line and arg tested
    line = builder(**kwargs)
    # if line_builder is one of the ones with defaults, override
    # else stick it into the positionals
    map_txt = map(line) if map_argname is None else map(**{map_argname: line})
    expected = f"line {line_nbr}: {reason}"

    with pytest.raises(ParseError, match=re.escape(expected)):
        MapParser(write_map(map_txt)).parse_file()


@pytest.mark.parametrize(
    ("connections", "error_text"),
    [
        (("start", "start"), "line 5: a zone cannot connect to itself"),
        (("start", "test"), "line 5: connection to undefined zone 'test'"),
    ],
    ids=["self connect", "unknown connect"],
)
def test_bad_connections(
    write_map: WriteMap, connections: tuple[str, str], error_text: str
) -> None:
    map_txt = map(link(*connections))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


@pytest.mark.parametrize(
    ("zone_line", "error_text"),
    [
        # the builders always close the bracket, so delimiter faults are
        # written out in full
        ("hub: a 0 0 [zone=normal", "line 5: Unterminated ["),
        ("hub: a 0 0 [", "line 5: Unterminated ["),
        # no '[' at all, so the fragment reads as a fourth positional
        ("hub: a 0 0 zone=normal]", "line 5: required format: name x y"),
        # key=value shape, which the meta list can express
        (
            hub("a", meta=["zone"]),
            "line 5: required metadata format: key=value",
        ),
        (
            hub("a", meta=["=normal"]),
            "line 5: Extra inputs are not permitted",
        ),
    ],
    ids=[
        "unterminated",
        "unterminated_empty",
        "closed_never_opened",
        "no_equals",
        "empty_key",
    ],
)
def test_bad_metadata_format(
    write_map: WriteMap, zone_line: str, error_text: str
) -> None:
    map_txt = map(zone_line, link("start", "a"))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


ZONE_CHOICES = "'priority', 'normal', 'restricted' or 'blocked'"


@pytest.mark.parametrize(
    ("meta", "error_text"),
    [
        (zone("bogus"), f"line 5: zone: Input should be {ZONE_CHOICES}"),
        (zone(""), f"line 5: zone: Input should be {ZONE_CHOICES}"),
        # 'zone=a=b' splits once, so the value keeps the second '='
        ("zone=a=b", f"line 5: zone: Input should be {ZONE_CHOICES}"),
        (
            max_drones(0),
            "line 5: max_drones: Input should be greater than or equal to 1",
        ),
        (
            max_drones(-1),
            "line 5: max_drones: Input should be greater than or equal to 1",
        ),
        (
            max_drones("abc"),
            "line 5: max_drones: Input should be a valid integer",
        ),
        (
            max_drones(1.5),
            "line 5: max_drones: Input should be a valid integer",
        ),
        (
            named_arg("bogus", 1),
            "line 5: bogus: Extra inputs are not permitted",
        ),
        (
            named_arg("max_link_capacity", 2),
            "line 5: max_link_capacity: Extra inputs are not permitted",
        ),
    ],
    ids=[
        "zone_unknown",
        "zone_empty",
        "zone_two_equals",
        "max_drones_zero",
        "max_drones_negative",
        "max_drones_text",
        "max_drones_float",
        "unknown_key",
        "connection_key_on_zone",
    ],
)
def test_bad_zone_metadata_value(
    write_map: WriteMap, meta: str, error_text: str
) -> None:
    map_txt = map(hub("a", meta=[meta]), link("start", "a"))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


@pytest.mark.parametrize(
    ("meta", "error_text"),
    [
        (
            max_link_capacity(0),
            "line 4: max_link_capacity: Input should be greater than or "
            "equal to 1",
        ),
        (
            max_link_capacity("abc"),
            "line 4: max_link_capacity: Input should be a valid integer",
        ),
        (zone("normal"), "line 4: zone: Unexpected keyword argument"),
        (color("green"), "line 4: color: Unexpected keyword argument"),
        # the zone spelling of capacity should not work on a connection
        (max_drones(2), "line 4: max_drones: Unexpected keyword argument"),
    ],
    ids=["cap_zero", "cap_text", "zone_key", "color_key", "zone_capacity_key"],
)
def test_bad_connection_metadata_value(
    write_map: WriteMap, meta: str, error_text: str
) -> None:
    map_txt = map(link_line=link("start", "end", meta=[meta]))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()
