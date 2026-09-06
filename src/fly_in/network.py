from pydantic import ConfigDict
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
