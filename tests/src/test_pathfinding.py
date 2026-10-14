from pathlib import Path

import pytest
from helpers import WriteMap

from fly_in.model import Network
from fly_in.parser import MapParser
from fly_in.pathfinding import shortest_path

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"


def _names(network: Network) -> list[str] | None:
    path = shortest_path(network)
    return None if path is None else [z.name for z in path]


@pytest.fixture
def linear_network() -> Network:
    return MapParser(MAPS_DIR / "easy" / "01_linear_path.txt").parse_file()


def test_linear(linear_network: Network) -> None:
    path = shortest_path(linear_network)
    assert path is not None
    assert path[0] == linear_network.start
    assert path[-1] == linear_network.end


def test_restricted_costs_more(write_map: WriteMap) -> None:
    """Both branches have one hop, but r costs 2 turns to enter."""
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: r 1 1 [zone=restricted]
hub: n 1 -1
hub: x 2 0
end_hub: goal 3 0
connection: start-r
connection: start-n
connection: r-x
connection: n-x
connection: x-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "n", "x", "goal"]


def test_priority_breaks_ties(write_map: WriteMap) -> None:
    """Equal turns both ways; the priority branch should win."""
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: n 1 1
hub: p 1 -1 [zone=priority]
end_hub: goal 2 0
connection: start-n
connection: start-p
connection: n-goal
connection: p-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "p", "goal"]


def test_blocked_is_avoided(write_map: WriteMap) -> None:
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: b 1 0 [zone=blocked]
hub: a 1 1
hub: c 2 1
end_hub: goal 2 0
connection: start-b
connection: b-goal
connection: start-a
connection: a-c
connection: c-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "a", "c", "goal"]


def test_unreachable_returns_none(write_map: WriteMap) -> None:
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: b 1 0 [zone=blocked]
end_hub: goal 2 0
connection: start-b
connection: b-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert shortest_path(network) is None
