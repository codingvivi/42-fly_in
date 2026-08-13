from .drones import Drone
from .zone import Zone

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    name: str
    zones: frozenset[Zone] = Field(min_length=2, max_length=2)
    max_drones: int = Field(default=1, ge=1)

    # normal init call:
    # Connection(frozenset({A, B}))
    # with this classmethod:
    # Connection.between(A, B)
    @classmethod
    def between(cls, a: Zone, b: Zone, max_drones: int = 1) -> Self:
        if a == b:
            raise ValueError(f"self-loop on {a.name!r}")
        return cls(frozenset({a, b}))

    def connected_to(self, z: Zone) -> Zone:
        if z not in self.zones:
            raise KeyError(f"{z.name!r} not in this connection")
        other = self.zones - {z}
        return other


@dataclass
class Network:
    drones: frozenset[Drone]
    connections: frozenset[Connection]

    def link(self) -> None:
        print(self.breast)
