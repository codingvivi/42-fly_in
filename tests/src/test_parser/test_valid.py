"""Metadata the parser must accept, including the awkward cases.

Two §VII.4 readings are pinned here. The first is stated outright: the
`max_drones` capacity is ignored on `start_hub`/`end_hub`, "and is not a
validation error". The second is an interpretation, because the subject
is silent on it -- see `test_blocked_terminal_parses`.
"""

import pytest
from helpers import (
    Row,
    WriteMap,
    color,
    end,
    hub,
    link,
    map,
    max_drones,
    nb_drones,
    params,
    start,
    zone,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from fly_in.model import Zone, ZoneType
from fly_in.parser import MapParser

FLEET = 5


def by_name(zones: frozenset[Zone]) -> dict[str, Zone]:
    """Index a Network's zones by name.

    Network stores them in a frozenset, so there is no lookup by name;
    every caller that wants one has to build this.
    """
    return {z.name: z for z in zones}


def check_zone_in_set(zones: frozenset[Zone], name: str) -> Zone:
    """Find the zone called `name`, failing with a message if absent."""
    index = by_name(zones)
    assert name in index, f"no zone named {name!r}, have {sorted(index)}"
    return index[name]


# `.split() == [s]` mirrors what the parser does: a zone line is split on
# whitespace and must yield exactly `name x y`, so any string that splits
# into more than one piece cannot be a name. Doing it this way also
# covers U+00A0 and U+2028, which a category blacklist would miss.
def _unsplittable(value: str) -> bool:
    return value.split() == [value]


zone_names = st.text(
    alphabet=st.characters(
        # '-' separates connection endpoints, '#' opens a comment,
        # '[' starts the metadata block, surrogates cannot be encoded
        blacklist_characters="-#[",
        blacklist_categories=["Cs"],
    ),
    min_size=1,
    max_size=20,
).filter(_unsplittable)

# a metadata value is a freer grammar than a name: '-', '=' and even ']'
# all survive, because _split_metadata only strips the final ']'
metadata_values = st.text(
    alphabet=st.characters(
        blacklist_characters="#[",
        blacklist_categories=["Cs"],
    ),
    min_size=1,
    max_size=20,
).filter(_unsplittable)


def _map_around(name: str, x: object, y: object, capacity: object) -> str:
    """A three-zone map whose middle hub is `name`.
    used to avoid name collsion if user choses to name a hub start or end.
    """
    start_name, end_name = f"{name}_start", f"{name}_end"
    return map(
        hub(name, x, y, meta=[max_drones(capacity)]),
        link(start_name, name),
        link(name, end_name),
        start_line=start(start_name),
        end_line=end(end_name),
        link_line=None,
    )


# a cap of 1 is below the fleet size, so an honoured cap would show up
TERMINAL_CAPACITY: list[Row] = [
    ({"start_line": start(meta=[max_drones(42)])}, "start", "start_hub"),
    ({"end_line": end(meta=[max_drones(42)])}, "end", "end_hub"),
]


@pytest.mark.parametrize(("map_args", "zone_name"), params(TERMINAL_CAPACITY))
def test_terminal_capacity_ignored(
    write_map: WriteMap, map_args: dict[str, str], zone_name: str
) -> None:
    """VII.4: max_drones on a terminal is accepted, then ignored."""
    map_txt = map(nb_line=nb_drones(FLEET), **map_args)
    network = MapParser(write_map(map_txt)).parse_file()
    terminal = check_zone_in_set(network.zones, zone_name)

    # declared value is still on the attributes
    assert terminal.attributes.max_drones == 42
    # whole fleet has to fit regardless
    assert terminal.capacity >= FLEET
    assert len(network.drones) == FLEET


@settings(
    max_examples=200,
    # write_map is function-scoped, so one temp dir is shared by every example;
    # each overwrites same file
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    name=zone_names,
    x=st.integers(),
    y=st.integers(),
    capacity=st.integers(min_value=1),
)
def test_zone_def_round_trip(
    write_map: WriteMap, name: str, x: int, y: int, capacity: int
) -> None:
    """Whatever a hub line declares is what the Zone reports back."""

    map_txt = _map_around(name, x, y, capacity)
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, name)
    # as per the _map_around defaults
    assert network.start.name == name + "_start"
    assert network.end.name == name + "_end"

    assert parsed.coordinates.x == x
    assert parsed.coordinates.y == y
    assert parsed.capacity == capacity


@pytest.mark.parametrize("zone_type", ZoneType)
def test_zone_meta_round_trip(
    write_map: WriteMap, zone_type: ZoneType
) -> None:
    """Whatever a hub line declares is what the Zone reports back."""

    # connections use zone *names* ("start"), not the file keywords
    # ("start_hub:"); the builders' defaults are start / end / testhub
    map_txt = map(
        hub(meta=[zone(zone_type)]),
        link("start", "testhub"),
        link("testhub", "end"),
        start_line=start(meta=[zone(zone_type)]),
        end_line=end(meta=[zone(zone_type)]),
        link_line=None,
    )
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, "testhub")
    assert parsed.attributes.type == zone_type
    assert network.start.attributes.type == zone_type
    assert network.end.attributes.type == zone_type


@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(value=metadata_values)
def test_color_round_trips(write_map: WriteMap, value: str) -> None:
    """color is stored verbatim: the parser gives it no meaning at all.

    Page 11: "any valid single-word strings ... There is no fixed list",
    so survival is the whole contract -> property rather than a table
    of named colors.
    """
    # connections use zone *names* ("start"), not the file keywords
    # ("start_hub:"); the builders' defaults are start / end / testhub
    map_txt = map(
        hub(meta=[color(value)]),
        link("start", "testhub"),
        link("testhub", "end"),
        start_line=start(meta=[color(value)]),
        end_line=end(meta=[color(value)]),
        link_line=None,
    )
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, "testhub")
    assert parsed.attributes.color == value
    assert network.start.attributes.color == value
    assert network.end.attributes.color == value


def test_color_defaults_to_none(write_map: WriteMap) -> None:
    """Page 11: color is optional, "default: none"."""
    map_txt = map(
        hub(),
        link("start", "testhub"),
        link("testhub", "end"),
        link_line=None,
    )
    network = MapParser(write_map(map_txt)).parse_file()

    assert check_zone_in_set(network.zones, "testhub").attributes.color is None
    assert network.start.attributes.color is None
    assert network.end.attributes.color is None


@settings(
    max_examples=500,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(capacity=st.integers(min_value=1))
def test_max_drone_round_trips(write_map: WriteMap, capacity: int):

    map_txt = map(
        hub(meta=[max_drones(capacity)]),
        link("start", "testhub"),
        link("testhub", "end"),
        link_line=None,
    )
    network = MapParser(write_map(map_txt)).parse_file()
    parsed = check_zone_in_set(network.zones, "testhub")

    assert parsed.attributes.max_drones == capacity
