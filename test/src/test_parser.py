import re
from pathlib import Path

import pytest
from helpers import *

from fly_in.parser import MapParser, ParseError

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
SHIPPED_MAPS = sorted(MAPS_DIR.rglob("*.txt"))


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


def test_missing_map_contents(write_map):
    with pytest.raises(ParseError, match="no nb_drones defined"):
        MapParser(write_map("")).parse_file()


@pytest.mark.parametrize(
    ("missing", "error_type", "error_text"),
    [
        # dropping a hub also drops the default connection, which would
        # otherwise fail first on the zone that is no longer defined
        (
            {"nb_line": None},
            ParseError,
            "line 1: first line must define nb_drones",
        ),
        (
            {"start_line": None, "link_line": None},
            ParseError,
            "end of file: no start_hub defined",
        ),
        (
            {"end_line": None, "link_line": None},
            ParseError,
            "end of file: no end_hub defined",
        ),
        ({"link_line": None}, ValueError, "unconnected zone(s)"),
    ],
    ids=["nb_drones", "start_hub", "end_hub", "connection"],
)
def test_missing_lines(write_map, missing, error_type, error_text):
    with pytest.raises(error_type, match=re.escape(error_text)):
        # unpack dict as kwargs
        MapParser(write_map(map(**missing))).parse_file()


@pytest.mark.parametrize(
    ("missing", "error_type", "error_text"),
    [
        # dropping a hub also drops the default connection, which would
        # otherwise fail first on the zone that is no longer defined
        (
            {"nb_line": None},
            ParseError,
            "line 1: first line must define nb_drones",
        ),
        (
            {"start_line": None, "link_line": None},
            ParseError,
            "end of file: no start_hub defined",
        ),
        (
            {"end_line": None, "link_line": None},
            ParseError,
            "end of file: no end_hub defined",
        ),
        ({"link_line": None}, ValueError, "unconnected zone(s)"),
    ],
    ids=["nb_drones", "start_hub", "end_hub", "connection"],
)
def test_missing_params(write_map, missing, error_type, error_text):
    with pytest.raises(error_type, match=re.escape(error_text)):
        MapParser(write_map(map(**missing))).parse_file()
