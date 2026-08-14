from enum import Enum
from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
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


@dataclass(frozen=True)
class Zone:
    name: str
    coordinates: Location
    type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, ge=1)
