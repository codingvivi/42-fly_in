from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.dataclasses import dataclass

from .occupiable import Capacity, Occupiable


@dataclass(frozen=True)
class Location:
    x: int
    y: int


class ZoneType(Enum):
    PRIORITY = "priority"
    NORMAL = "normal"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"

    @property
    def cost(self) -> int:
        return 2 if self is ZoneType.RESTRICTED else 1

    @property
    def is_passable(self) -> bool:
        return self is not ZoneType.BLOCKED

    @property
    def is_preferred(self) -> bool:
        return self is ZoneType.PRIORITY

    def __str__(self) -> str:
        return self.value


class ZoneAttribute(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True
    )

    type: ZoneType = Field(default=ZoneType.NORMAL, alias="zone")
    color: str | None = None
    max_drones: Capacity = 1


@dataclass(frozen=True)
class Zone(Occupiable):
    name: str
    coordinates: Location
    attributes: ZoneAttribute

    @property
    def capacity(self) -> Capacity:
        return self.attributes.max_drones
