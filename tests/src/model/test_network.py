from pathlib import Path

import pytest

from fly_in.model import Connection, Network, Zone
from fly_in.parser import MapParser

MAPS_DIR = Path(__file__).parents[3] / "data" / "maps"
MAP_FILES = sorted(MAPS_DIR.glob("*/*.txt"))


def _get_neighbours(
    network: Network, zone: Zone
) -> set[tuple[Zone, Connection]]:
    """Reference answer: scan every connection for ones touching `zone`."""
    return {
        (c.connected_to(zone), c)
        for c in network.connections
        if zone in c.zones
    }


@pytest.fixture(
    params=MAP_FILES, ids=[f"{p.parent.name}/{p.stem}" for p in MAP_FILES]
)
def network(request: pytest.FixtureRequest) -> Network:
    return MapParser(request.param).parse_file()


def test_adjacent_matches_naive_scan(network: Network) -> None:
    """Every zone's neighbours match a full scan of the connections"""
    for zone in network.zones:
        assert set(network.adjacent[zone]) == _get_neighbours(network, zone)


def test_adjacent_keys_are_exactly_the_zones(network: Network) -> None:
    """No zone missing, no stray keys"""
    assert network.adjacent.keys() == network.zones


def test_adjacent_is_cached(network: Network) -> None:
    """Second access returns the same object, not a rebuilt map"""
    assert network.adjacent is network.adjacent
