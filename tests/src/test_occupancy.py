"""Placement and capacity, the state a Network no longer carries."""

import pytest

from fly_in.model import (
    Drone,
    Location,
    TerminalZone,
    Zone,
    ZoneAttribute,
)
from fly_in.occupancy import Occupancy

FLEET = 3
DRONES = frozenset(Drone(id=nbr) for nbr in range(1, FLEET + 1))


def _zone(name: str, max_drones: int = 1) -> Zone:
    return Zone(
        name=name,
        coordinates=Location(0, 0),
        attributes=ZoneAttribute(max_drones=max_drones),
    )


def _start() -> TerminalZone:
    return TerminalZone(
        name="start", coordinates=Location(0, 0), attributes=ZoneAttribute()
    )


def test_all_drones_begin_at_start() -> None:
    """Whole fleet starts in the start zone."""
    start = _start()
    occupancy = Occupancy(DRONES, start)

    assert all(occupancy[drone] is start for drone in DRONES)
    assert occupancy.occupants(start) == FLEET


def test_start_is_uncapped() -> None:
    """A fleet larger than any max_drones still fits at the start."""
    start = _start()
    assert Occupancy(DRONES, start).has_room(start)


def test_move_tracks_both_ends() -> None:
    start, target = _start(), _zone("corridor")
    occupancy = Occupancy(DRONES, start)
    drone = next(iter(DRONES))

    occupancy.move(drone, target)

    assert occupancy[drone] is target
    assert occupancy.occupants(target) == 1
    assert occupancy.occupants(start) == FLEET - 1


def test_move_into_full_zone_is_refused() -> None:
    """max_drones=1 means the second arrival has nowhere to go."""
    start, target = _start(), _zone("corridor")
    occupancy = Occupancy(DRONES, start)
    first, second = sorted(DRONES, key=lambda d: d.id)[:2]

    occupancy.move(first, target)

    assert not occupancy.has_room(target)
    with pytest.raises(ValueError, match="corridor is full"):
        occupancy.move(second, target)


def test_capacity_is_the_declared_one() -> None:
    """Zones honor their limits."""
    start, target = _start(), _zone("wide", max_drones=2)
    occupancy = Occupancy(DRONES, start)
    first, second, third = sorted(DRONES, key=lambda d: d.id)

    occupancy.move(first, target)
    occupancy.move(second, target)

    assert occupancy.occupants(target) == 2
    with pytest.raises(ValueError, match="wide is full"):
        occupancy.move(third, target)
