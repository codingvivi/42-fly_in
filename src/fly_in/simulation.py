from typing import NamedTuple

from .model import (
    Connection,
    Drone,
    Network,
    Occupiable,
    Zone,
    ZoneType,
)
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
    departure_turn: int


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


Turn = dict[Drone, Occupiable]
"""One turn's moves: where each drone that moved ended up."""


class Simulation:
    """Replay a plan turn by turn, enforcing every capacity rule.

    Drones follow their flights exactly: no waiting, no rerouting. Each
    drone takes off on its departs turn and then moves every turn until
    it lands. If the plan is sound nothing ever collides; if it isn't,
    the turn that breaks a rule raises ValueError.
    """

    def __init__(self, network: Network, plan: Plan) -> None:
        self.network = network
        self.flights = flights(network, plan)
        self.occupancy = Occupancy(network.drones, network.start)
        # index into its lane of the last zone each drone reached
        self._pos: dict[Drone, int] = {f.drone: 0 for f in self.flights}
        # the connection between two zones, either way round
        self._link: dict[frozenset[Zone], Connection] = {
            c.zones: c for c in network.connections
        }

    def done(self) -> bool:
        """True once every drone has reached the end of its lane."""
        return all(self._pos[f.drone] == len(f.lane) - 1 for f in self.flights)

    def run(self) -> list[Turn]:
        """Step until every drone is delivered; return the turn log."""
        log: list[Turn] = []
        while not self.done():
            log.append(self.step(len(log) + 1))
        return log

    def step(self, turn: int) -> Turn:
        """Play one turn: decide every move, check links, commit together."""
        moves: Turn = {}
        # drones using each connection this turn
        link_use: dict[Connection, int] = {}

        for f in self.flights:
            pos = self._pos[f.drone]

            # if not at departure turn
            # or delivered already
            if turn < f.departure_turn or pos == len(f.lane) - 1:
                continue

            nxt = f.lane[pos + 1]
            link = self._link[frozenset((f.lane[pos], nxt))]
            # if drone is sitting on a connection
            # (only happens for restricted)
            if self.occupancy[f.drone] is link:
                moves[f.drone] = nxt
                continue

            # update link user number
            link_use[link] = link_use.get(link, 0) + 1

            if nxt.attributes.type is ZoneType.RESTRICTED:
                # move into link to extend turn
                moves[f.drone] = link
            else:
                # normal into next
                moves[f.drone] = nxt

        for link, n in link_use.items():
            if n > link.capacity:
                raise ValueError(
                    f"turn {turn}: {link.name} carries {n} drones, "
                    f"max {link.capacity}"
                )
        # move all drones according to previous code
        self.occupancy.move_all(moves)

        # if entered zone, advance in flight plan
        for drone, target in moves.items():
            if isinstance(target, Zone):
                self._pos[drone] += 1

        # return moves for printing and logging
        return moves
