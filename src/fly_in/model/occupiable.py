from abc import ABC, abstractmethod
from typing import Annotated

from pydantic import Field

Capacity = Annotated[int, Field(ge=1)]
"""A simultaneous-occupancy limit: always a positive integer.

Spelled ``max_drones`` on zones and ``max_link_capacity`` on connections in
the map format, but the same concept either way.
"""


class Occupiable(ABC):
    """A capacity-limited place a drone can occupy during a turn.

    A drone is either resting in a zone or sitting on a connection while in
    transit toward a restricted zone, so both are valid occupancy targets.
    Turn scheduling needs only a name to report and a capacity to respect,
    which is the whole of the shared contract.

    Attributes:
        name: Identifier used in simulation output.
    """

    name: str

    @property
    @abstractmethod
    def capacity(self) -> Capacity:
        """Maximum number of drones that may occupy this simultaneously."""
