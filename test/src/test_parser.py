from pathlib import Path

import pytest

from fly_in.parser import MapParser

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
SHIPPED_MAPS = sorted(MAPS_DIR.rglob("*.txt"))


# p = Path('data/maps/easy/01_linear_path.txt')
# p.stem     # '01_linear_path'
# p.name     # '01_linear_path.txt'
# p.suffix   # '.txt'
# p.parent   # Path('data/maps/easy')
@pytest.mark.parametrize("path", SHIPPED_MAPS, ids=lambda p: p.stem)
def test_42_maps_parse(path: Path) -> None:
    # should not raise
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
