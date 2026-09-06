from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass

from .occupiable import Capacity, Occupiable
from .zone import Zone


@dataclass(
    frozen=True,
    config=ConfigDict(extra="forbid", populate_by_name=True),
)
class Connection(Occupiable):
    name: str
    zones: frozenset[Zone] = Field(min_length=2, max_length=2)
    max_drones: Capacity = Field(
        default=1, validation_alias="max_link_capacity"
    )

    @property
    def capacity(self) -> Capacity:
        return self.max_drones

    def connected_to(self, zone: Zone) -> Zone:
        if zone not in self.zones:
            raise KeyError(f"{zone.name!r} not in this connection")
        # (element,) unpacks one element iterable
        # should complain if more than one member
        (other,) = self.zones - {zone}
        return other
