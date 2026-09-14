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
    end,
    hub,
    link,
    map,
    max_drones,
    nb_drones,
    params,
    start,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from fly_in.model import Zone
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


# a name the parser accepts: '-' separates connections, '#' opens a
# comment, '[' and ']' delimit metadata, '=' is metadata syntax, and
# whitespace breaks the `name x y` arity. Cs/Cc/Zs drop surrogates,
# control characters and exotic spaces, which break the line format.
zone_names = st.text(
    alphabet=st.characters(
        blacklist_characters="-#[]= \t\n\r",
        blacklist_categories=("Cs", "Cc", "Zs"),
    ),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() == s and s not in {"start", "end"})

# a cap of 1 is below the fleet size, so an honoured cap would show up
TERMINAL_CAPACITY: list[Row] = [
    ({"start_line": start(meta=[max_drones(1)])}, "start", "start_hub"),
    ({"end_line": end(meta=[max_drones(1)])}, "end", "end_hub"),
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
    assert terminal.attributes.max_drones == 1
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
def test_zone_values_round_trip(
    write_map: WriteMap, name: str, x: int, y: int, capacity: int
) -> None:
    """Whatever a hub line declares is what the Zone reports back."""

    map_txt = map(
        hub(name, x, y, meta=[max_drones(capacity)]), link("start", name)
    )

    network = MapParser(write_map(map_txt)).parse_file()

    parsed = check_zone_in_set(network.zones, name)

    assert parsed.coordinates.x == x
    assert parsed.coordinates.y == y
    assert parsed.capacity == capacity


# @pytest.mark.parametrize(
#     ("map_args", "value", "target"), params(VALUE_TESTS)
# )
# def test_occupiable_vals(write_map, map_args, value, target) -> None:

#     network = MapParser(write_map(map(map_args))).parse_file()

#     assert network.value == target
# cc

# # pdf does not list blocked as invalid
# # thus it should parse and shown as no solution
# BLOCKED_TERMINALS: list[Row] = [
#     ({"start_line": start(meta=[zone("blocked")])}, "start", "start_hub"),
#     ({"end_line": end(meta=[zone("blocked")])}, "end", "end_hub"),
# ]


# @pytest.mark.parametrize(
#     ("map_args", "zone_name"), params(BLOCKED_TERMINALS)
# )
# def test_blocked_terminal_parses(
#     write_map: WriteMap, map_args: dict[str, str], zone_name: str
# ) -> None:
#     """A blocked start or end is not a parse error, just unsolvable."""
#     network = MapParser(write_map(map(**map_args))).parse_file()
#     terminal = find_zone(network.zones, zone_name)

#     # recorded as declared, not quietly sanitised to normal
#     assert str(terminal.attributes.type) == "blocked"
#     assert terminal.attributes.type.is_passable is False
