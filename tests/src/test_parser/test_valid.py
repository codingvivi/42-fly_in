"""Metadata the parser must accept, and what it stores when it does.

Every test here is a round trip: a value written into a map line has to
come back off the parsed Zone unchanged. The one exception is §VII.4's
stated rule that `max_drones` is *ignored* on `start_hub`/`end_hub` --
accepted, kept on .attributes, but not reported by .capacity.
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
    max_link_capacity,
    nb_drones,
    params,
    start,
    zone,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from fly_in.model import Connection, Zone, ZoneType
from fly_in.parser import MapParser


# ~~~~~ lookup helpers ~~~~~
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


def check_conn_in_set(
    connections: frozenset[Connection], name: str
) -> Connection:
    """Same for connections, whose name is the "a-b" text as written."""
    index = {c.name: c for c in connections}
    assert name in index, f"no connection {name!r}, have {sorted(index)}"
    return index[name]


# ~~~~~ strategies ~~~~~
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


# ~~~~~ map shapes ~~~~~
# connections use zone *names* ("start"), not the file keywords
# ("start_hub:"); the builders' defaults are start / end / testhub
def _chain(hub_line: str, **preamble: str | None) -> str:
    """start -> testhub -> end, with map()'s default zone names."""
    return map(
        hub_line,
        link("start", "testhub"),
        link("testhub", "end"),
        link_line=None,
        **preamble,
    )


def _map_around(name: str, x: object, y: object, capacity: object) -> str:
    """Create three-zone map test string whose middle hub is `name`.
    Appends _start and _end to the terminal zones to avoid name collision"""
    start_name, end_name = f"{name}_start", f"{name}_end"
    return map(
        hub(name, x, y, meta=[max_drones(capacity)]),
        link(start_name, name),
        link(name, end_name),
        start_line=start(start_name),
        end_line=end(end_name),
        link_line=None,
    )


# ~~~~~ zone definition: name and coordinates ~~~~~
@settings(
    max_examples=200,
    # write_map is function-scoped, so one temp dir is shared by every
    # example; each overwrites the same file, which is what we want
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


# ~~~~~ metadata: zone type ~~~~~
@pytest.mark.parametrize("zone_type", ZoneType)
def test_zone_meta_round_trip(
    write_map: WriteMap, zone_type: ZoneType
) -> None:
    """Every ZoneType is stored as declared, terminals included."""
    map_txt = _chain(
        hub(meta=[zone(zone_type)]),
        start_line=start(meta=[zone(zone_type)]),
        end_line=end(meta=[zone(zone_type)]),
    )
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, "testhub")
    assert parsed.attributes.type == zone_type
    assert network.start.attributes.type == zone_type
    assert network.end.attributes.type == zone_type


# ~~~~~ metadata: color ~~~~~
@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(value=metadata_values)
def test_color_round_trips(write_map: WriteMap, value: str) -> None:
    """Check if color string gets read accurately.
    Since there is no fixed list,
    arbitrary non whitespaced strings get checked
    """
    map_txt = _chain(
        hub(meta=[color(value)]),
        start_line=start(meta=[color(value)]),
        end_line=end(meta=[color(value)]),
    )
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, "testhub")
    assert parsed.attributes.color == value
    assert network.start.attributes.color == value
    assert network.end.attributes.color == value


def test_color_defaults_to_none(write_map: WriteMap) -> None:
    """Page 11: color is optional, "default: none"."""
    network = MapParser(write_map(_chain(hub()))).parse_file()

    assert check_zone_in_set(network.zones, "testhub").attributes.color is None
    assert network.start.attributes.color is None
    assert network.end.attributes.color is None


# ~~~~~ metadata: capacity ~~~~~
@settings(
    max_examples=500,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(capacity=st.integers(min_value=1))
def test_max_drone_round_trips(write_map: WriteMap, capacity: int) -> None:
    """On a plain hub the declared cap is what .capacity reports."""
    map_txt = _chain(hub(meta=[max_drones(capacity)]))
    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, "testhub")
    assert parsed.attributes.max_drones == capacity
    assert parsed.capacity == capacity


FLEET = 5

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


# ~~~~~ connection metadata: link capacity ~~~~~
@settings(
    max_examples=500,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(capacity=st.integers(min_value=1))
def test_max_link_capacity_round_trips(
    write_map: WriteMap, capacity: int
) -> None:
    """The declared cap is what Connection.capacity reports."""
    map_txt = map(
        hub(),
        link("start", "testhub", meta=[max_link_capacity(capacity)]),
        link("testhub", "end"),
        link_line=None,
    )
    network = MapParser(write_map(map_txt)).parse_file()

    capped = check_conn_in_set(network.connections, "start-testhub")
    assert capped.max_link_capacity == capacity
    assert capped.capacity == capacity

    assert check_conn_in_set(network.connections, "testhub-end").capacity == 1


def test_link_capacity_defaults_to_one(write_map: WriteMap) -> None:
    """Check for optional max_link_capacity defaulting: to 1."""
    network = MapParser(write_map(_chain(hub()))).parse_file()

    for name in ("start-testhub", "testhub-end"):
        assert check_conn_in_set(network.connections, name).capacity == 1
