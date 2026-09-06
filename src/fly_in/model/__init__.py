"""The domain model: what a map file describes once parsed.

The modules layer strictly downward, so nothing here can form a cycle:

    occupiable  the contract shared by anything a drone can occupy
    zone        a node, plus its coordinates and metadata
    connection  an edge joining exactly two zones
    network     the whole graph, its drones and their occupancy

Import from this package rather than its modules -- the names below are
the domain's public surface.
"""

from .connection import Connection
from .drones import Drone
from .network import Network
from .occupiable import Capacity, Occupiable
from .zone import Location, Zone, ZoneAttribute, ZoneType

__all__ = [
    "Capacity",
    "Connection",
    "Drone",
    "Location",
    "Network",
    "Occupiable",
    "Zone",
    "ZoneAttribute",
    "ZoneType",
]
