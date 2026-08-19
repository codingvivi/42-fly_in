from pydantic import Field
from pydantic.dataclasses import dataclass

from .drones import Drone
from .hub import Hub


@dataclass(frozen=True)
class Connection:
    name: str
    hubs: frozenset[Hub] = Field(min_length=2, max_length=2)
    max_drones: int = Field(default=1, ge=1)

    def connected_to(self, hub: Hub) -> Hub:
        if hub not in self.hubs:
            raise KeyError(f"{hub.name!r} not in this connection")
        # (element,) unpacks one element iterable
        # should complain if more than one member
        (other,) = self.hubs - {hub}
        return other


@dataclass
class Network:
    drones: frozenset[Drone]
    start: Hub
    end: Hub
    hubs: frozenset[Hub]
    connections: frozenset[Connection]
    occupancy: dict[Drone, Hub | Connection]

    def link(self) -> None: ...
