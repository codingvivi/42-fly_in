from collections import defaultdict
from functools import cached_property

from pydantic import model_validator
from pydantic.dataclasses import dataclass

from fly_in.model.occupiable import Occupiable

from .connection import Connection
from .drones import Drone
from .zone import Zone


@dataclass
class Network:
    drones: frozenset[Drone]
    start: Zone
    end: Zone
    zones: frozenset[Zone]
    connections: frozenset[Connection]

    @property
    def all_occupiables(self) -> frozenset[Occupiable]:
        return self.zones | self.connections

    @cached_property
    def adjacent(self) -> dict[Zone, list[tuple[Zone, Connection]]]:
        adj: dict[Zone, list[tuple[Zone, Connection]]] = defaultdict(list)
        for c in self.connections:
            a, b = c.zones
            adj[a].append((b, c))
            adj[b].append((a, c))
        return dict(adj)

    @model_validator(mode="after")
    def _every_zone_is_connected(self) -> "Network":
        # for _ in self.connections:
        #     for z in c.zones:
        linked: set[Zone] = {z for c in self.connections for z in c.zones}
        orphans: list[str] = sorted(z.name for z in self.zones - linked)
        if orphans:
            raise ValueError(f"unconnected zone(s): {', '.join(orphans)}")

        return self
