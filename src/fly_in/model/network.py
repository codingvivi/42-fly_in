from typing import Self

from pydantic import ConfigDict, model_validator
from pydantic.dataclasses import dataclass

from .connection import Connection
from .drones import Drone
from .occupiable import Occupiable
from .zone import Zone


# Occupiable is an ABC,
# so pydantic cannot derive a schema for it.
# Validate occupancy values by isinstance instead
@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class Network:
    drones: frozenset[Drone]
    start: Zone
    end: Zone
    zones: frozenset[Zone]
    connections: frozenset[Connection]
    occupancy: dict[Drone, Occupiable]

    def link(self) -> None: ...

    @model_validator(mode="after")
    def _every_zone_is_connected(self) -> Self:

        # for _ in self.connections:
        #     for z in c.zones:
        linked: set[Zone] = {z for c in self.connections for z in c.zones}
        orphans: list[str] = sorted(z.name for z in self.zones - linked)
        if orphans:
            raise ValueError(f"unconnected zone(s): {', '.join(orphans)}")

        return self
