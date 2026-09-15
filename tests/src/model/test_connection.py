import pytest
from helpers import Row, params

from fly_in.model import Connection, Location, Zone, ZoneAttribute


def _zone(name: str) -> Zone:
    return Zone(
        name=name, coordinates=Location(0, 0), attributes=ZoneAttribute()
    )


LEFT, RIGHT, OUTSIDE = _zone("left"), _zone("right"), _zone("outside")
EDGE = Connection(name="left-right", zones=frozenset({LEFT, RIGHT}))


TRAVERSALS: list[Row] = [
    (LEFT, RIGHT, "from_left"),
    (RIGHT, LEFT, "from_right"),
]


@pytest.mark.parametrize(("actual", "target"), params(TRAVERSALS))
def test_connection_both_dirs(actual: Zone, target: Zone) -> None:
    """Zones are reachable from either side"""
    assert EDGE.connected_to(actual) is target


def test_rejection_of_non_connected_zone() -> None:
    """Outside zone throws correct error"""
    with pytest.raises(KeyError, match="'outside' not in this connection"):
        EDGE.connected_to(OUTSIDE)


def test_involution() -> None:
    """Following the edge twice returns to where you started."""
    for zone in (LEFT, RIGHT):
        assert EDGE.connected_to(EDGE.connected_to(zone)) is zone


def test_member_ammount() -> None:
    """Only two members per connection"""
    for zones in (frozenset({LEFT}), frozenset({LEFT, RIGHT, OUTSIDE})):
        with pytest.raises(ValueError):
            Connection(name="bad", zones=zones)
