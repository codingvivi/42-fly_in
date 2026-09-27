import logging
from pathlib import Path

import pytest

from fly_in.model import Network
from fly_in.parser import MapParser
from fly_in.pathfinding import Zone_Pq, shortest_path

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"


@pytest.fixture
def linear_network() -> Network:
    return MapParser(MAPS_DIR / "easy" / "01_linear_path.txt").parse_file()


def test_init(caplog: pytest.LogCaptureFixture, linear_network) -> None:
    with caplog.at_level(logging.DEBUG, logger="fly_in.pathfinding"):
        shortest_path(linear_network)

    assert (
        f"inited solving queue with {[Zone_Pq(0, 0, 0, linear_network.start)]}"
        in caplog.text
    )
