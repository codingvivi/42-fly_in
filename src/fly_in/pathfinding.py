import heapq
import logging
from collections.abc import Iterator
from itertools import count
from typing import NamedTuple

from .model import Network, Zone

logger = logging.getLogger(__name__)


class Zone_Pq(NamedTuple):
    cost_to: int
    bias: int
    id: int
    zone: Zone
    prev: Zone | None


class VisitStats(NamedTuple):
    cost_to: int
    prev: Zone | None


def shortest_path(
    network: Network, start: Zone | None = None, end: Zone | None = None
) -> tuple[Zone]:
    if start is None:
        start = network.start
    if end is None:
        end = network.end
    logger.info("getting shortest path between %a and %a", start, end)

    candidates_pq: list[Zone_Pq] = []

    best: dict[Zone, VisitStats] = {start: VisitStats(0, None)}
    counter = count()
    # initalize
    candidates_pq = [Zone_Pq(0, 0, next(counter), start, None)]
    logger.debug("inited solving queue with %a", candidates_pq)

    while candidates_pq:
        curr = heapq.heappop(candidates_pq)
        logger.debug("curr: %a", curr)

        # NOT a tuple!
        # instead: object to lazy querry zones
        neighbors: Iterator[Zone] = (
            c.connected_to(curr.zone)
            for c in network.connections
            if curr.zone in c.zones
        )
        logger.debug("neighbors: %s", curr)

        for n in neighbors:
            logger.debug("process neighbor '%s'", curr)
            # cost to current + thru current + thru connection
            n_cost = curr.cost_to + curr.zone.attributes.type.cost + 1
            logger.debug("cost from start: %i", curr)

            if n not in best:
                bias: int = 0
                if curr.zone.attributes.type.is_preferred:
                    bias += 1
                heapq.heappush(
                    candidates_pq,
                    Zone_Pq(n_cost, bias, next(counter), n, curr.zone),
                )
            # if already visited and curr worse or equal without priority, skip
            else:
                tobeat = best[n].cost_to
                if (
                    n_cost > tobeat
                    or n_cost == tobeat
                    and n.attributes.type.is_preferred is False
                ):
                    continue

            # else update
            best[n] = VisitStats(n_cost, curr.zone)

    return None
