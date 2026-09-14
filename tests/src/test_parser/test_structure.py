"""Rules that span the whole map: required lines, duplicates, drone count.

These are the §VII.4 rules `MapParser` accumulates state for, plus the
`Network` model validators that only run once the file is fully read.
"""

import re
from pathlib import Path

import pytest
from helpers import (
    Row,
    WriteMap,
    end,
    hub,
    link,
    map,
    max_drones,
    nb_drones,
    params,
    start,
)

from fly_in.parser import MapParser, ParseError

MAPS_DIR = Path(__file__).parents[3] / "data" / "maps"
SHIPPED_MAPS = sorted(MAPS_DIR.rglob("*.txt"))


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


# dropping a hub also drops the default connection, which would otherwise
# fail first on the zone that is no longer defined
MISSING_LINES: list[Row] = [
    (
        {"nb_line": None},
        "line 1: first line must define nb_drones",
        "nb_drones",
    ),
    (
        {"start_line": None, "link_line": None},
        "end of file: no start_hub defined",
        "start_hub",
    ),
    (
        {"end_line": None, "link_line": None},
        "end of file: no end_hub defined",
        "end_hub",
    ),
    (
        {"link_line": None},
        "end of file: unconnected zone(s): end, start",
        "connection",
    ),
]


@pytest.mark.parametrize(("missing", "error_text"), params(MISSING_LINES))
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


# builders that re-append what map() already put in the preamble
DUPLICATE_DEFINITIONS: list[Row] = [
    (
        (nb_drones(),),
        "line 5: nb_drones specified more than once",
        "nb_drones",
    ),
    ((start(),), "line 5: duplicate zone name 'start'", "start_same_name"),
    (
        (start(name="other"),),
        "line 5: more than one start_hub",
        "start_new_name",
    ),
    ((end(),), "line 5: duplicate zone name 'end'", "end_same_name"),
    ((end(name="other"),), "line 5: more than one end_hub", "end_new_name"),
    (
        (link("start", "end"),),
        "line 5: duplicate connection 'start-end'",
        "connection",
    ),
    (
        (link("end", "start"),),
        "line 5: duplicate connection 'end-start'",
        "connection_reversed",
    ),
    (
        (hub("a"), link("start", "a"), hub("a")),
        "line 7: duplicate zone name 'a'",
        "hub_name",
    ),
    (
        (hub(meta=[max_drones(1), max_drones(2)]),),
        "line 5: 'max_drones' specified more than once",
        "metadata_key",
    ),
]


@pytest.mark.parametrize(
    ("extra", "expected"), params(DUPLICATE_DEFINITIONS)
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


# nb_drones is the first line, so every fault here is line 1.
# an empty value leaves a bare keyword, caught before _parse_drones
BAD_DRONE_COUNTS: list[Row] = [
    ("abc", "line 1: nb_drones must be an integer", "text"),
    ("2 3", "line 1: nb_drones must be an integer", "two"),
    (1.5, "line 1: nb_drones must be an integer", "float"),
    ("", "line 1: Keyword needs an argument", "empty"),
    (0, "line 1: nb_drones must be positive", "zero"),
    (-5, "line 1: nb_drones must be positive", "negative"),
]


@pytest.mark.parametrize(("count", "error_text"), params(BAD_DRONE_COUNTS))
def test_bad_drone_count(
    write_map: WriteMap, count: object, error_text: str
) -> None:
    map_txt = map(nb_line=nb_drones(count))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()
