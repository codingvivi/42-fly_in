from pathlib import Path

import pytest
from helpers import WriteMap

from fly_in.cost import ZERO, Cost, add, entry_cost, sub
from fly_in.graph import Arc, Graph, Node, Side
from fly_in.model import Network
from fly_in.parser import MapParser
from fly_in.pathfinding import (
    augment,
    decompose,
    residual_path,
    shortest_path,
)

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
ALL_MAPS = sorted(MAPS_DIR.glob("*/*.txt"))


def _names(network: Network) -> list[str] | None:
    path = shortest_path(network)
    return None if path is None else [z.name for z in path]


@pytest.fixture
def linear_network() -> Network:
    return MapParser(MAPS_DIR / "easy" / "01_linear_path.txt").parse_file()


def test_linear(linear_network: Network) -> None:
    path = shortest_path(linear_network)
    assert path is not None
    assert path[0] == linear_network.start
    assert path[-1] == linear_network.end


def test_restricted_costs_more(write_map: WriteMap) -> None:
    """Both branches have one hop, but r costs 2 turns to enter."""
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: r 1 1 [zone=restricted]
hub: n 1 -1
hub: x 2 0
end_hub: goal 3 0
connection: start-r
connection: start-n
connection: r-x
connection: n-x
connection: x-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "n", "x", "goal"]


def test_priority_breaks_ties(write_map: WriteMap) -> None:
    """Equal turns both ways; the priority branch should win."""
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: n 1 1
hub: p 1 -1 [zone=priority]
end_hub: goal 2 0
connection: start-n
connection: start-p
connection: n-goal
connection: p-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "p", "goal"]


def test_blocked_is_avoided(write_map: WriteMap) -> None:
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: b 1 0 [zone=blocked]
hub: a 1 1
hub: c 2 1
end_hub: goal 2 0
connection: start-b
connection: b-goal
connection: start-a
connection: a-c
connection: c-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert _names(network) == ["start", "a", "c", "goal"]


def test_unreachable_returns_none(write_map: WriteMap) -> None:
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: b 1 0 [zone=blocked]
end_hub: goal 2 0
connection: start-b
connection: b-goal
"""
    network = MapParser(write_map(map_txt)).parse_file()
    assert shortest_path(network) is None


# ~~~~~ residual_path ~~~~~
def _path_cost(path: list[Arc]) -> Cost:
    total = ZERO
    for arc in path:
        total = add(total, arc.cost)
    return total


def _zone_names(graph: Graph, path: list[Arc]) -> list[str]:
    """Zones a path visits, in order; z_in -> z_out arcs add nothing."""
    names = [graph.source.zone.name]
    names += [a.head.zone.name for a in path if a.head.zone != a.tail.zone]
    return names


# stand-in for the SSP loop's potential update
def _update(h: dict[Node, Cost], dist: dict[Node, Cost]) -> None:
    for node, d in dist.items():
        h[node] = add(h.get(node, ZERO), d)


@pytest.mark.parametrize(
    "path", ALL_MAPS, ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_first_search_matches_shortest_path(path: Path) -> None:
    """With no flow and h = 0 it is plain Dijkstra on the split graph.

    Compared by cost, not by route: equal-cost routes may tie-break
    differently between the two searches.
    """
    network = MapParser(path).parse_file()
    zones = shortest_path(network)
    assert zones is not None
    expected = ZERO
    for z in zones[1:]:
        expected = add(expected, entry_cost(z))

    graph = Graph(network)
    arcs, dist = residual_path(graph, {})
    assert arcs is not None
    assert arcs[0].tail == graph.source
    assert arcs[-1].head == graph.sink
    assert _path_cost(arcs) == expected
    # with h = 0 reduced distances are real distances
    assert dist[graph.sink] == expected


def test_path_arcs_are_chained() -> None:
    network = MapParser(MAPS_DIR / "easy" / "02_simple_fork.txt").parse_file()
    graph = Graph(network)
    arcs, _ = residual_path(graph, {})
    assert arcs is not None
    for prev, nxt in zip(arcs, arcs[1:]):
        assert prev.head == nxt.tail


def test_full_arcs_are_skipped() -> None:
    """Once the only exit from the source is full, there is no path."""
    network = MapParser(MAPS_DIR / "easy" / "01_linear_path.txt").parse_file()
    graph = Graph(network)
    for arc in graph.arcs_from(graph.source):
        arc.flow = arc.cap
    arcs, dist = residual_path(graph, {})
    assert arcs is None
    assert graph.sink not in dist


def test_unreachable_sink(write_map: WriteMap) -> None:
    map_txt = """nb_drones: 1
start_hub: start 0 0
hub: b 1 0 [zone=blocked]
end_hub: goal 2 0
connection: start-b
connection: b-goal
"""
    graph = Graph(MapParser(write_map(map_txt)).parse_file())
    arcs, dist = residual_path(graph, {})
    assert arcs is None
    assert set(dist) == {graph.source}


# s-a-b-t is shortest, but taking it blocks b for s-x1-x2-b and leaves
# a-y1-y2-t stranded. The second search has to undo a->b via its twin.
REROUTE_MAP = """nb_drones: 2
start_hub: s 0 0
hub: a 1 0
hub: b 2 0
end_hub: t 3 0
hub: x1 0 1
hub: x2 1 1
hub: y1 2 -1
hub: y2 3 -1
connection: s-a
connection: a-b
connection: b-t
connection: s-x1
connection: x1-x2
connection: x2-b
connection: a-y1
connection: y1-y2
connection: y2-t
"""


def _a_to_b(graph: Graph) -> Arc:
    """The a_out -> b_in arc (not its twin, which has cap 0)."""
    (arc,) = [
        arc
        for node in graph._arcs_from
        if node.zone.name == "a" and node.side is Side.OUT
        for arc in graph.arcs_from(node)
        if arc.head.zone.name == "b"
    ]
    return arc


def test_reroute_through_twin(write_map: WriteMap) -> None:
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    h: dict[Node, Cost] = {}

    first, dist = residual_path(graph, h)
    assert first is not None
    assert _zone_names(graph, first) == ["s", "a", "b", "t"]
    augment(first)
    _update(h, dist)

    second, _ = residual_path(graph, h)
    assert second is not None
    assert _zone_names(graph, second) == [
        "s", "x1", "x2", "b", "a", "y1", "y2", "t",
    ]
    augment(second)
    # the two lanes cross a->b in opposite directions: they cancel out
    assert _a_to_b(graph).flow == 0
    # 4 + 4 turns for s-a-y1-y2-t and s-x1-x2-b-t
    assert add(_path_cost(first), _path_cost(second)) == (8, 0)


def test_reduced_costs_stay_non_negative(write_map: WriteMap) -> None:
    """After h += dist, every arc with room has reduced cost >= 0."""
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    h: dict[Node, Cost] = {}
    first, dist = residual_path(graph, h)
    assert first is not None
    augment(first)
    _update(h, dist)

    for node in list(graph._arcs_from):
        for arc in graph.arcs_from(node):
            # unreached nodes can't be reached later either: skip them
            if arc.residual > 0 and arc.tail in dist:
                reduced = sub(
                    add(arc.cost, h.get(arc.tail, ZERO)),
                    h.get(arc.head, ZERO),
                )
                assert reduced >= ZERO


def test_stale_potentials_raise(write_map: WriteMap) -> None:
    """Skipping the potential update lets a twin's negative cost through."""
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    first, _ = residual_path(graph, {})
    assert first is not None
    augment(first)
    with pytest.raises(ValueError, match="negative reduced cost"):
        residual_path(graph, {})


# ~~~~~ augment ~~~~~
def test_augment_moves_one_unit(linear_network: Network) -> None:
    graph = Graph(linear_network)
    path, _ = residual_path(graph, {})
    assert path is not None
    augment(path)
    for arc in path:
        assert arc.twin is not None
        assert arc.flow == 1
        assert arc.twin.flow == -1
        # the twin now has room to undo this unit
        assert arc.twin.residual == 1


def test_augment_until_full(linear_network: Network) -> None:
    """Every augment uses up one unit of the bottleneck."""
    graph = Graph(linear_network)
    path, _ = residual_path(graph, {})
    assert path is not None
    bottleneck = min(arc.cap for arc in path)
    for _ in range(bottleneck):
        path, _ = residual_path(graph, {})
        assert path is not None
        augment(path)
    assert residual_path(graph, {})[0] is None


def test_augment_twin_undoes_arc(write_map: WriteMap) -> None:
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    a_to_b = _a_to_b(graph)
    assert a_to_b.twin is not None
    augment([a_to_b])
    augment([a_to_b.twin])
    assert a_to_b.flow == 0
    assert a_to_b.twin.flow == 0


# ~~~~~ opposing flow ~~~~~
def _run_ssp(graph: Graph, nb_drones: int) -> int:
    """Stand-in for the SSP loop: augment until full or one lane a drone.

    Returns how many lanes were added.
    """
    h: dict[Node, Cost] = {}
    for added in range(nb_drones):
        path, dist = residual_path(graph, h)
        if path is None:
            return added
        augment(path)
        _update(h, dist)
    return nb_drones


@pytest.mark.parametrize(
    "path", ALL_MAPS, ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_no_opposing_flow(path: Path) -> None:
    network = MapParser(path).parse_file()
    graph = Graph(network)
    _run_ssp(graph, len(network.drones))
    assert graph.opposing_flows() == []


def test_no_opposing_flow_after_reroute(write_map: WriteMap) -> None:
    """The map built to make a lane run a->b backwards still ends clean."""
    network = MapParser(write_map(REROUTE_MAP)).parse_file()
    graph = Graph(network)
    _run_ssp(graph, len(network.drones))
    assert graph.opposing_flows() == []


def test_opposing_flow_is_found(write_map: WriteMap) -> None:
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    a_to_b = _a_to_b(graph)
    (b_to_a,) = [
        arc
        for arc in graph.arcs()
        if arc.cap > 0
        and arc.tail.zone.name == "b"
        and arc.head.zone.name == "a"
    ]
    augment([a_to_b, b_to_a])
    assert graph.opposing_flows() == [(a_to_b, b_to_a)]


# ~~~~~ decompose ~~~~~
def _lane_names(graph: Graph) -> list[list[str]]:
    return [[z.name for z in lane] for lane in decompose(graph)]


def test_decompose_no_flow(linear_network: Network) -> None:
    assert decompose(Graph(linear_network)) == []


def test_decompose_one_lane_is_shortest_path(
    linear_network: Network,
) -> None:
    graph = Graph(linear_network)
    _run_ssp(graph, 1)
    assert decompose(graph) == [shortest_path(linear_network)]


def test_decompose_fork_uses_both_branches() -> None:
    network = MapParser(MAPS_DIR / "easy" / "02_simple_fork.txt").parse_file()
    graph = Graph(network)
    assert _run_ssp(graph, 2) == 2
    lanes = _lane_names(graph)
    assert {lane[2] for lane in lanes} == {"path_a", "path_b"}


def test_decompose_repeats_shared_lane() -> None:
    """The bottleneck holds 2: the same route comes back as 2 lanes."""
    network = MapParser(
        MAPS_DIR / "easy" / "03_basic_capacity.txt"
    ).parse_file()
    graph = Graph(network)
    assert _run_ssp(graph, len(network.drones)) == 2
    route = ["start", "bottleneck", "wide_area", "goal"]
    assert _lane_names(graph) == [route, route]


def test_decompose_after_reroute(write_map: WriteMap) -> None:
    """Lanes are the swapped halves, not the routes the searches found."""
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    _run_ssp(graph, 2)
    assert sorted(_lane_names(graph)) == [
        ["s", "a", "y1", "y2", "t"],
        ["s", "x1", "x2", "b", "t"],
    ]


def test_decompose_leaves_flow_alone(write_map: WriteMap) -> None:
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    _run_ssp(graph, 2)
    before = [arc.flow for arc in graph.arcs()]
    decompose(graph)
    assert [arc.flow for arc in graph.arcs()] == before


def test_decompose_dead_end_raises(write_map: WriteMap) -> None:
    """Flow out of the source that goes nowhere breaks flow in = out."""
    graph = Graph(MapParser(write_map(REROUTE_MAP)).parse_file())
    (s_to_a,) = [
        arc
        for arc in graph.arcs_from(graph.source)
        if arc.cap > 0 and arc.head.zone.name == "a"
    ]
    augment([s_to_a])
    with pytest.raises(ValueError, match="flow stops"):
        decompose(graph)


@pytest.mark.parametrize(
    "path", ALL_MAPS, ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_decompose_all_maps(path: Path) -> None:
    network = MapParser(path).parse_file()
    graph = Graph(network)
    added = _run_ssp(graph, len(network.drones))
    lanes = decompose(graph)
    assert len(lanes) == added
    for lane in lanes:
        assert lane[0] == network.start
        assert lane[-1] == network.end
