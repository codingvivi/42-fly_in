from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from fly_in.cost import Cost, entry_cost, neg
from fly_in.model import Network, Zone


class Side(Enum):
    IN = "in"
    OUT = "out"


class Node(NamedTuple):
    """One half of a split zone."""

    zone: Zone
    side: Side


# doesn't create __eq__ function
# without == is True if same object
# ==  would compare all fields otherwise
# and endlessly recurse on twin
@dataclass(eq=False)
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

        self.source = Node(network.start, Side.OUT)
        self.sink = Node(network.end, Side.IN)
        # no zone can ever hold more than every drone at once
        nb_drones = len(network.drones)

        # add arcs
        for zone in network.zones:
            if not zone.attributes.type.is_passable:
                continue

            zone_tail = Node(zone, Side.OUT)
            # add inta-zone arc
            self._add_arc(
                Node(zone, Side.IN),
                zone_tail,
                min(zone.capacity, nb_drones),
                (0, 0),
            )

            # add zone.out -> neighbor.in arc
            for n, conn in network.adjacent[zone]:
                if not n.attributes.type.is_passable:
                    continue

                self._add_arc(
                    zone_tail,
                    Node(n, Side.IN),
                    conn.max_link_capacity,
                    entry_cost(n),
                )

    def arcs_from(self, node: Node) -> list[Arc]:
        """Every arc leaving node, twins included; [] if there are none."""
        # .get, not []: a lookup must not add keys to the defaultdict
        return self._arcs_from.get(node, [])

    def _add_arc(self, tail: Node, head: Node, cap: int, cost: Cost) -> Arc:
        """Add an arc tail -> head and its twin, return the arc."""
        arc = Arc(tail, head, cap, cost)
        # twin starts with no room
        # only opens up once arc carries flow
        twin = Arc(head, tail, 0, neg(cost))
        arc.twin = twin
        twin.twin = arc

        # each arc is stored under its own tail, so the twin goes under head
        self._arcs_from[tail].append(arc)
        self._arcs_from[head].append(twin)
        return arc
