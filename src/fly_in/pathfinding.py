"""Cheapest route through the network, by Dijkstra's algorithm."""

import heapq
import logging
from itertools import count
from typing import NamedTuple

from .cost import ZERO, Cost, add, entry_cost, sub
from .graph import Arc, Graph, Node
from .model import Network, Zone

logger = logging.getLogger(__name__)


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

    best: dict[Zone, Visit] = {start: Visit(ZERO, None)}
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


# ~~~~~ residual graph, for successive shortest paths ~~~~~
class Node_Pq(NamedTuple):
    """A heap entry for the residual search. Field order is sort order."""

    cost_to: Cost
    # breaks key ties, so two Nodes never get compared
    tie: int
    node: Node


class ArcVisit(NamedTuple):
    """Cheapest known way into a node, and the arc it came in on."""

    cost_to: Cost
    via: Arc | None


def residual_path(
    graph: Graph, h: dict[Node, Cost]
) -> tuple[list[Arc] | None, dict[Node, Cost]]:
    """Cheapest source -> sink path over arcs that still have room.

    Arcs are weighed by reduced cost, arc.cost + h[tail] - h[head], which
    the potentials h keep >= 0 even on twins with negative cost. Nodes
    missing from h count as potential 0.

    Returns (path, dist):
      path -- the arcs from source to sink, or None if sink is unreachable
      dist -- reduced distance to every node reached, for the caller to
              fold into h (h[v] += dist[v]) before the next search
    The search does not stop at the sink: every reachable node needs its
    final distance, or the next search can meet negative reduced costs.
    """
    source = graph.source
    best: dict[Node, ArcVisit] = {source: ArcVisit(ZERO, None)}
    tie = count()
    heap = [Node_Pq(ZERO, next(tie), source)]

    while heap:
        cost_to, _, node = heapq.heappop(heap)
        if cost_to > best[node].cost_to:
            continue

        h_node = h.get(node, ZERO)
        for arc in graph.arcs_from(node):
            if arc.residual <= 0:
                continue

            reduced = sub(add(arc.cost, h_node), h.get(arc.head, ZERO))
            # if johnsoning didnt work
            if reduced < ZERO:
                raise ValueError(
                    f"negative reduced cost {reduced} on "
                    f"{arc.tail} -> {arc.head}"
                )

            n_cost_to = add(cost_to, reduced)
            if arc.head not in best or n_cost_to < best[arc.head].cost_to:
                best[arc.head] = ArcVisit(n_cost_to, arc)
                heapq.heappush(heap, Node_Pq(n_cost_to, next(tie), arc.head))

    dist = {node: visit.cost_to for node, visit in best.items()}
    if graph.sink not in best:
        logger.debug("sink unreachable in residual graph")
        return None, dist
    return _rebuild_arcs(best, graph.sink), dist


def _rebuild_arcs(best: dict[Node, ArcVisit], end: Node) -> list[Arc]:
    """Walk the via arcs back from end, return them source-first."""
    path: list[Arc] = []
    while (arc := best[end].via) is not None:
        path.append(arc)
        end = arc.tail
    return path[::-1]
