import sys
from math import inf

from .model import Network, Zone
from .occupancy import Occupancy

INF_INT =


class Simulation:
    def __init__(
        self,
        network: Network,
        occupancy: Occupancy,
    ) -> None:

        self.network: Network = network
        self.occupancy: Occupancy = occupancy

        self.costs: dict[Zone, int] = {}
        self.costs[network.start] = 0
