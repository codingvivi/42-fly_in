from pathlib import Path

import pytest

from fly_in.parser import MapParser
from fly_in.planning import lane_length, plan
from fly_in.simulation import flights

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
ALL_MAPS = sorted(MAPS_DIR.glob("*/*.txt"))


def test_flights_simple_fork() -> None:
    """4 drones, 2 equal branches: 2 per branch, leaving turns 1 and 2."""
    network = MapParser(MAPS_DIR / "easy/02_simple_fork.txt").parse_file()
    result = flights(network, plan(network))

    assert [f.drone.id for f in result] == [1, 2, 3, 4]
    assert sorted(f.departs for f in result) == [1, 1, 2, 2]
    by_branch: dict[str, list[int]] = {}
    for f in result:
        by_branch.setdefault(f.lane[2].name, []).append(f.departs)
    assert sorted(by_branch) == ["path_a", "path_b"]
    assert all(sorted(d) == [1, 2] for d in by_branch.values())


@pytest.mark.parametrize("path", ALL_MAPS, ids=lambda p: p.stem)
def test_flights_land_when_planned(path: Path) -> None:
    """The last landing, L + departs - 1, is the planner's score."""
    network = MapParser(path).parse_file()
    p = plan(network)
    result = flights(network, p)

    assert len(result) == len(network.drones)
    assert max(lane_length(f.lane) + f.departs - 1 for f in result) == p.turns
