from pathlib import Path

import pytest
from helpers import WriteMap

from fly_in.model import Network, Zone
from fly_in.parser import MapParser
from fly_in.planning import lane_length, plan, score

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


# ~~~~~ plan ~~~~~
MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"

# subject targets: the turn count each map must be solved within
TARGETS = {
    "easy/01_linear_path": 6,
    "easy/02_simple_fork": 8,
    "easy/03_basic_capacity": 6,
    "medium/01_dead_end_trap": 12,
    "medium/02_circular_loop": 15,
    "medium/03_priority_puzzle": 12,
    "hard/01_maze_nightmare": 30,
    "hard/02_capacity_hell": 35,
    "hard/03_ultimate_challenge": 45,
    # strictly under 45
    "challenger/01_the_impossible_dream": 44,
}


def _plan_map(name: str) -> tuple[Network, list[list[str]], int]:
    network = MapParser(MAPS_DIR / f"{name}.txt").parse_file()
    p = plan(network)
    return network, [[z.name for z in lane] for lane in p.lanes], p.turns


def test_plan_simple_fork_uses_both_branches() -> None:
    _, lanes, turns = _plan_map("easy/02_simple_fork")
    assert sorted(lane[2] for lane in lanes) == ["path_a", "path_b"]
    assert turns == 4


def test_plan_bottleneck_caps_lanes() -> None:
    """bottleneck has max_drones=2: no more than 2 lanes fit through."""
    _, lanes, _ = _plan_map("easy/03_basic_capacity")
    assert len(lanes) == 2
    assert all("bottleneck" in lane for lane in lanes)


def test_plan_one_drone_takes_shortest(network: Network) -> None:
    p = plan(network)
    assert [[z.name for z in lane] for lane in p.lanes] == [SHORT]
    assert p.turns == 2


def test_plan_assignment_covers_every_drone() -> None:
    network, lanes, _ = _plan_map("medium/03_priority_puzzle")
    p = plan(network)
    assert len(p.assignment) == len(network.drones)
    assert set(p.assignment) <= set(range(len(lanes)))


def test_plan_unreachable_raises(write_map: WriteMap) -> None:
    path = write_map(
        "nb_drones: 1\n"
        "start_hub: s 0 0\n"
        "hub: b 1 0 [zone=blocked]\n"
        "end_hub: t 2 0\n"
        "connection: s-b\n"
        "connection: b-t\n"
    )
    with pytest.raises(ValueError, match="no route"):
        plan(MapParser(path).parse_file())


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_plan_meets_target(name: str) -> None:
    """Predicted turns only; the simulation still has to confirm them."""
    _, _, turns = _plan_map(name)
    assert turns <= TARGETS[name]
