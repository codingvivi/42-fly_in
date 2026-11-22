import pytest
from helpers import WriteMap

from fly_in.model import Network, Zone
from fly_in.parser import MapParser
from fly_in.planning import lane_length, score

# two routes to goal: s-a-goal (2 turns) and s-l1-...-l9-goal (10 turns),
# r is restricted and only on the third route s-r-goal (3 turns)
MAP = """nb_drones: 1
start_hub: s 0 0
hub: a 1 0
hub: r 1 1 [zone=restricted]
hub: l1 1 -1
hub: l2 2 -1
hub: l3 3 -1
hub: l4 4 -1
hub: l5 5 -1
hub: l6 6 -1
hub: l7 7 -1
hub: l8 8 -1
hub: l9 9 -1
end_hub: goal 2 0
connection: s-a
connection: a-goal
connection: s-r
connection: r-goal
connection: s-l1
connection: l1-l2
connection: l2-l3
connection: l3-l4
connection: l4-l5
connection: l5-l6
connection: l6-l7
connection: l7-l8
connection: l8-l9
connection: l9-goal
"""

SHORT = ["s", "a", "goal"]
RESTRICTED = ["s", "r", "goal"]
LONG = ["s", *(f"l{i}" for i in range(1, 10)), "goal"]


@pytest.fixture
def network(write_map: WriteMap) -> Network:
    return MapParser(write_map(MAP)).parse_file()


def _lane(network: Network, names: list[str]) -> list[Zone]:
    by_name = {z.name: z for z in network.zones}
    return [by_name[n] for n in names]


# ~~~~~ lane_length ~~~~~
def test_length_counts_zones_after_start(network: Network) -> None:
    assert lane_length(_lane(network, SHORT)) == 2


def test_length_restricted_costs_two(network: Network) -> None:
    assert lane_length(_lane(network, RESTRICTED)) == 3


def test_length_start_only(network: Network) -> None:
    assert lane_length(_lane(network, ["s"])) == 0


# ~~~~~ score ~~~~~
def test_one_lane_one_drone(network: Network) -> None:
    assert score([_lane(network, SHORT)], 1) == (2, [0])


def test_one_lane_queues_drones(network: Network) -> None:
    """First lands on turn L, then one more every turn."""
    assert score([_lane(network, SHORT)], 3) == (4, [0, 0, 0])


def test_equal_lanes_share_drones(network: Network) -> None:
    lanes = [_lane(network, SHORT), _lane(network, SHORT)]
    turns, assignment = score(lanes, 4)
    assert turns == 3
    assert sorted(assignment) == [0, 0, 1, 1]


def test_long_lane_unused_with_few_drones(network: Network) -> None:
    lanes = [_lane(network, SHORT), _lane(network, LONG)]
    turns, assignment = score(lanes, 3)
    assert turns == 4
    assert assignment == [0, 0, 0]


def test_long_lane_used_once_queue_is_long(network: Network) -> None:
    """Drone 10 would land on turn 11 on SHORT, on turn 10 on LONG."""
    lanes = [_lane(network, SHORT), _lane(network, LONG)]
    turns, assignment = score(lanes, 10)
    assert assignment.count(1) == 1
    assert turns == 10


def test_restricted_lane_is_longer(network: Network) -> None:
    lanes = [_lane(network, RESTRICTED), _lane(network, SHORT)]
    assert score(lanes, 1) == (2, [1])


def test_extra_lane_never_hurts(network: Network) -> None:
    short = _lane(network, SHORT)
    for nb in range(1, 15):
        alone, _ = score([short], nb)
        both, _ = score([short, _lane(network, LONG)], nb)
        assert both <= alone


def test_no_lanes_raises() -> None:
    with pytest.raises(ValueError, match="no lanes"):
        score([], 1)
