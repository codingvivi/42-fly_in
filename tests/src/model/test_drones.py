import pytest
from helpers import Row, params

from fly_in.model import Drone

LABELS: list[Row] = [
    (1, "D1", "first"),
    (2, "D2", "second"),
    (42, "D42", "two_digits"),
]


@pytest.mark.parametrize(("drone_id", "expected"), params(LABELS))
def test_str_is_the_output_label(drone_id: int, expected: str) -> None:
    """Output label is correct"""
    assert str(Drone(id=drone_id)) == expected


def test_drones_are_hashable_and_compare_by_id() -> None:
    """Drones are as differentiable as they should be"""
    assert Drone(id=1) == Drone(id=1)
    assert Drone(id=1) != Drone(id=2)
    assert len({Drone(id=1), Drone(id=1), Drone(id=2)}) == 2
