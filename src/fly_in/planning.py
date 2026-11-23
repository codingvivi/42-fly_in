"""Turning lanes into a schedule: how many turns, which drone flies where."""

import heapq
import logging
from typing import NamedTuple

from .cost import Cost, entry_cost
from .graph import Graph, Node
from .model import Network, Zone
from .pathfinding import augment, decompose, residual_path, update_potentials

logger = logging.getLogger(__name__)


def lane_length(lane: list[Zone]) -> int:
    """Turns for one drone to fly lane, start to end.

    Every zone after start costs its entry turns (restricted = 2).
    """
    return sum(entry_cost(zone)[0] for zone in lane[1:])


def score(lanes: list[list[Zone]], nb_drones: int) -> tuple[int, list[int]]:
    """Turns until every drone is delivered, and the lane of each drone.

    Drones go out one at a time, each to the lane where it lands soonest:
    a lane of length L with n drones already on it delivers the next one
    on turn L + n. The score is the turn the last drone lands.
    A lane that would only slow things down gets no drones.
    """
    if not lanes:
        raise ValueError("no lanes to score")

    # lane length and lane (given number as ID)
    heap = [(lane_length(lane), i) for i, lane in enumerate(lanes)]
    # sort the heap
    heapq.heapify(heap)

    turns = 0
    assignment: list[int] = []

    #
    for _ in range(nb_drones):
        # get length and lane of that length
        lands, i = heapq.heappop(heap)
        # add drone (index of assignment) to lane no. i
        assignment.append(i)
        # update total turns
        turns = lands
        # add used lane to queue
        # with increase length (since occupied by +1 drones)
        heapq.heappush(heap, (lands + 1, i))
    return turns, assignment


class Plan(NamedTuple):
    """The chosen lanes and who flies them.

    turns      -- predicted turn the last drone lands
    lanes      -- each a list of zones, start to end
    assignment -- assignment[k] is the lane index of the k-th drone sent
    """

    turns: int
    lanes: list[list[Zone]]
    assignment: list[int]


def plan(network: Network) -> Plan:
    """Pick the set of lanes that delivers every drone in the fewest turns.

    Successive shortest paths: each round adds one unit of flow along the
    cheapest residual path (possibly rerouting earlier lanes through
    twins), then the flow is read back as lanes and scored. More lanes
    are not always better -- a long lane can be slower than queueing on a
    short one -- so every round is scored and the best one kept.

    Stops when the graph is saturated or there is one lane per drone.
    Raises ValueError if end can't be reached at all.
    """
    nb_drones = len(network.drones)
    graph = Graph(network)
    h: dict[Node, Cost] = {}
    best: Plan | None = None

    for round_ in range(1, nb_drones + 1):
        # dijkstra, but on graph (with arcs)
        # fails if everything full
        path, dist = residual_path(graph, h)
        if path is None:
            logger.info("graph saturated after %d lane(s)", round_ - 1)
            break
        # add +1 to flow
        augment(path)
        # update johnson potentials
        update_potentials(h, dist)

        opposing = graph.opposing_flows()
        if opposing:
            raise AssertionError(f"opposing flow on {opposing}")

        lanes = decompose(graph)
        turns, assignment = score(lanes, nb_drones)
        logger.debug("%d lane(s): %d turns", len(lanes), turns)
        # strict <: on a tie, fewer lanes is the simpler plan
        if best is None or turns < best.turns:
            best = Plan(turns, lanes, assignment)

    if best is None:
        raise ValueError(
            f"no route from {network.start.name} to {network.end.name}"
        )
    logger.info("plan: %d lane(s), %d turns", len(best.lanes), best.turns)
    return best
