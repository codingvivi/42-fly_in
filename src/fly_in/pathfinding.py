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


def shortest_path(
    network: Network, start: Zone | None = None, end: Zone | None = None
) -> tuple[Zone]:
    if start is None:
        start = network.start
    if end is None:
        end = network.end

    costs: dict[Zone, int] = {start: 0}

    candidates_pq: list[Zone_Pq] = []
    counter = count()
    # initalize
    candidates_pq = [Zone_Pq(0, 0, next(counter), start)]
    logger.debug("inited solving queue with %a", candidates_pq)

    while candidates_pq:
        curr = heapq.heappop(candidates_pq)
        neighbors = (
            c.connected_to(curr.zone)
            for c in network.connections
            if curr.zone in c.zones
        )

    return None
