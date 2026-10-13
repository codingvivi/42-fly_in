from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass

from .occupiable import Capacity, Occupiable
from .zone import Zone


@dataclass(
    frozen=True,
    config=ConfigDict(extra="forbid"),
)
class Connection(Occupiable):
    name: str
    zones: frozenset[Zone] = Field(min_length=2, max_length=2)
    # can't alias cuz alias needs populate_by_name,
    # which would also accept the field's own name,
    # letting a connection take the zone-only 'max_drones'
    max_link_capacity: Capacity = 1

    @property
    def capacity(self) -> Capacity:
        return self.max_link_capacity

    def connected_to(self, zone: Zone) -> Zone:
        if zone not in self.zones:
            raise KeyError(f"{zone.name!r} not in this connection")
        # (element,) unpacks one element iterable
        # should complain if more than one member
        (other,) = self.zones - {zone}
        return other
