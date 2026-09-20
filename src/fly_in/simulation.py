from .model import Network, Occupiable
from .occupancy import Occupancy


class Simulation:
    def __init__(
        self,
        network: Network,
        occupancy: Occupancy,
    ) -> None:

        self._network: Network = network
        self._occupancy: Occupancy
        self._costs: dict[Occupiable, int]
