import heapq
import logging
from itertools import count
from typing import NamedTuple

from .model import Network, Zone

logger = logging.getLogger(__name__)


class Zone_Pq(NamedTuple):
    cost: int
    bias: int
    id: int
    zone: Zone
    prev: Zone | None


class VisitStats(NamedTuple):
    cost: int
    prev: Zone | None


def shortest_path(
    network: Network, start: Zone | None = None, end: Zone | None = None
) -> tuple[Zone]:
    if start is None:
        start = network.start
    if end is None:
        end = network.end
    logger.info("getting shortest path between %a and %a", start, end)

    costs: dict[Zone, int] = {start: 0}

    candidates_pq: list[Zone_Pq] = []

    visited: set[Zone_Pq] = set()
    counter = count()
    # initalize
    candidates_pq = [Zone_Pq(0, 0, next(counter), start, None)]
    logger.debug("inited solving queue with %a", candidates_pq)

    while candidates_pq:
        curr = heapq.heappop(candidates_pq)
        visited.add(curr)
        logger.debug("curr: %a", curr)

        neighbors = (
            c.connected_to(curr.zone)
            for c in network.connections
            if curr.zone in c.zones
        )
        logger.debug("neighbors: %s", curr)

        for n in neighbors:
            if n in visited:
                # compare cost
                ...
            else:
                n

    return None
