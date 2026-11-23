from typing import NamedTuple

from .model import Drone, Network, Zone
from .occupancy import Occupancy
from .planning import Plan


class Flight(NamedTuple):
    """One drone's part of the plan.

    drone   -- who flies
    lane    -- the zones it visits, start to end
    departs -- the turn it leaves start (turns count from 1)
    """

    drone: Drone
    lane: list[Zone]
    departs: int


def flights(network: Network, plan: Plan) -> list[Flight]:
    """Give every drone its lane and the turn it takes off.

    Drones are sent in id order, the k-th one on lane plan.assignment[k].
    A lane takes one new drone per turn, so the n-th drone on a lane
    (counting from 0) departs on turn n + 1 and lands on turn L + n,
    the same number score() predicted.
    """

    # The drone name is genned by ID but if it wasn't this would fix it
    drones = sorted(network.drones, key=lambda d: d.id)
    if len(drones) != len(plan.assignment):
        raise ValueError(
            f"{len(drones)} drones but {len(plan.assignment)} assigned"
        )

    # init list with 0s for every lane
    # numbers represent drones on a lane
    sent = [0] * len(plan.lanes)
    result: list[Flight] = []
    # zip up tuples with drones and their lane
    # assignment is indexed by sending order
    # we are sending by ID upwards so this is fine
    for drone, i in zip(drones, plan.assignment, strict=True):
        result.append(Flight(drone, plan.lanes[i], sent[i] + 1))
        sent[i] += 1
    return result


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
