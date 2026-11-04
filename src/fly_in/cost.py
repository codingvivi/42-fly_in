"""What a move costs, and the arithmetic on costs.

Kept apart from pathfinding and graph so both can import it without
importing each other.
"""

from .model import Zone

# (turns, -priority zones visited)
# fewer turns first, then more priority zones
Cost = tuple[int, int]

ZERO: Cost = (0, 0)


def add(a: Cost, b: Cost) -> Cost:
    """Component-wise a + b. (a + b on tuples would concatenate.)"""
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Cost, b: Cost) -> Cost:
    """Component-wise a - b."""
    return (a[0] - b[0], a[1] - b[1])


def neg(a: Cost) -> Cost:
    """Component-wise -a: the cost of a twin arc."""
    return (-a[0], -a[1])


def entry_cost(zone: Zone) -> Cost:
    """Cost of moving into zone: its turns, -1 if it's a priority zone."""
    z_type = zone.attributes.type
    return (z_type.cost, -int(z_type.is_preferred))
