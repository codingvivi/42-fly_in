"""Cheapest route through the network, by Dijkstra's algorithm."""

import heapq
import logging
from itertools import count
from typing import NamedTuple

from .model import Network, Zone

logger = logging.getLogger(__name__)

# (turns, -priority zones visited)
# tuple comparison: fewer turns first, then more priority zones
Cost = tuple[int, int]


def entry_cost(zone: Zone) -> Cost:
    """Cost of moving into zone: its turns, -1 if it's a priority zone."""
    z_type = zone.attributes.type
    return (z_type.cost, -int(z_type.is_preferred))


class Zone_Pq(NamedTuple):
    """A heap entry. Field order is sort order."""

    cost_to: Cost
    # breaks key ties, so two Zones never get compared
    tie: int
    zone: Zone


class Visit(NamedTuple):
    """Cheapest known way into a zone."""

    cost_to: Cost
    prev: Zone | None


def shortest_path(
    network: Network, start: Zone | None = None, end: Zone | None = None
) -> list[Zone] | None:
    """Return the cheapest path from start to end, both included.

    A move costs the zone type of the zone moved into.
    Ties in turns go to the path through more priority zones.
    Returns None if end can't be reached.
    """
    if start is None:
        start = network.start
    if end is None:
        end = network.end
    logger.info("getting shortest path between %a and %a", start, end)

    best: dict[Zone, Visit] = {start: Visit((0, 0), None)}
    tie = count()
    heap = [Zone_Pq(best[start].cost_to, next(tie), start)]

    while heap:
        cost_to, _, zone = heapq.heappop(heap)
        logger.debug("inspect %s at %s", zone.name, cost_to)

        if cost_to > best[zone].cost_to:
            logger.debug("was stale! already saved with cost of %s", cost_to)
            continue

        if zone == end:
            logger.debug("reached end")
            return _rebuild(best, end)

        turns, prio_neg = cost_to
        for n, _conn in network.adjacent[zone]:
            logger.debug("%a - neighbor '%a' with cost", n, cost_to)

            if not n.attributes.type.is_passable:
                logger.debug("not passable, skipping", n)
                continue

            n_turns, n_prio = entry_cost(n)
            n_cost_to = (turns + n_turns, prio_neg + n_prio)
            # update best and push together, or the invariant breaks
            if n not in best or n_cost_to < best[n].cost_to:
                best[n] = Visit(n_cost_to, zone)
                heapq.heappush(heap, Zone_Pq(n_cost_to, next(tie), n))

    return None


def _rebuild(best: dict[Zone, Visit], end: Zone) -> list[Zone]:
    """Walk prev links back from end, return the path start-first."""
    path = [end]
    while (p := best[path[-1]].prev) is not None:
        path.append(p)
    return path[::-1]
