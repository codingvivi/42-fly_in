from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from fly_in.model import Network, Zone
from fly_in.pathfinding import Cost, entry_cost


class Side(Enum):
    IN = "in"
    OUT = "out"


class Node(NamedTuple):
    """One half of a split zone."""

    zone: Zone
    side: Side


@dataclass
class Arc:
    tail: Node
    head: Node
    cap: int
    cost: Cost
    flow: int = 0
    # dont print the twin arc to avoid infinite loop
    twin: "Arc|None" = field(default=None, repr=False)

    @property
    def residual(self) -> int:
        return self.cap - self.flow

    def __post_init__(self) -> None:
        if self.cap < 0:
            raise ValueError(f"negative capacity on {self.tail}->{self.head}")


class Graph:
    def __init__(self, network: Network):
        self._arcs_from: dict[Node, list[Arc]] = defaultdict(list)

        for zone in network.zones:
            if not zone.attributes.type.is_passable:
                continue

            # leaving thru tail of A, OUT
            tail = Node(zone, Side.OUT)
            neighbors = {n[0]: n[1] for n in network.adjacent[zone]}

            arcs: list[Arc] = []

            for n in neighbors:
                # comin from A, entering thru head of B, IN
                head = Node(n, Side.IN)
                cost = entry_cost(n)

                arc = Arc(tail, head, zone.attributes.max_drones, cost)

                twin_cost = (-cost[0], -cost[1])
                twin_arc = Arc(head, tail, n.attributes.max_drones, twin_cost)
                arc.twin = twin_arc
                arc.twin.twin = arc

                arcs.append(arc)

            self._arcs_from[tail] = arcs

    def _add_arc(self, tail: Node, head: Node, cap: int, cost: Cost) -> Arc:
        """Add an arc tail -> head and its twin, return the arc."""
        arc = Arc(tail, head, cap, cost)
        # twin starts with no room: it only opens up once arc carries flow
        twin = Arc(head, tail, 0, (-cost[0], -cost[1]))
        arc.twin = twin
        twin.twin = arc

        # each arc is stored under its own tail, so the twin goes under head
        self._arcs_from[tail].append(arc)
        self._arcs_from[head].append(twin)
        return arc
