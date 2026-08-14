from .drones import Drone
from .zone import Zone

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    name: str
    zones: frozenset[Zone] = Field(min_length=2, max_length=2)
    max_drones: int = Field(default=1, ge=1)

    def connected_to(self, z: Zone) -> Zone:
        if z not in self.zones:
            raise KeyError(f"{z.name!r} not in this connection")
        # (element,) unpacks one element iterable
        # should complain if more than one member
        (other,) = self.zones - {z}
        return other


@dataclass
class Network:
    drones: frozenset[Drone]
    start: Zone
    end: Zone
    zones: frozenset[Zone]
    connections: frozenset[Connection]
    occupancy: dict[Drone, Zone | Connection]

    def link(self) -> None: ...
