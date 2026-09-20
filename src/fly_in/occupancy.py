"""Where every drone is, right now."""

from .model import Drone, Occupiable, Zone


class Occupancy:
    """A drone -> place mapping"""

    def __init__(self, drones: frozenset[Drone], start: Zone) -> None:
        # build initial dict with all drones at start
        self._at: dict[Drone, Occupiable] = dict.fromkeys(drones, start)
        # so i dont have to scan each drone per count querry
        # _at[Occupiable, Drone] would solve this but allow for drone dupes
        self._counts: dict[Occupiable, int] = {start: len(drones)}

    # allows for occupancy[drone]
    def __getitem__(self, drone: Drone) -> Occupiable:
        return self._at[drone]

    def occupants(self, place: Occupiable) -> int:
        return self._counts.get(place, 0)

    def has_room(self, place: Occupiable) -> bool:
        return self.occupants(place) < place.capacity

    def move(self, drone: Drone, target: Occupiable) -> None:
        """Relocate one drone, refusing a move that would overfill."""
        if not self.has_room(target):
            raise ValueError(f"{target.name} is full")

        origin = self._at[drone]
        self._counts[origin] -= 1
        self._counts[target] = self._counts.get(target, 0) + 1
        self._at[drone] = target
