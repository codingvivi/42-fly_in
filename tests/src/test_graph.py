"""The residual graph SSP runs on: node splitting, arcs, twins."""

from pathlib import Path

import pytest
from helpers import (
    WriteMap,
    hub,
    link,
    map,
    max_drones,
    max_link_capacity,
    nb_drones,
    zone,
)

from fly_in.graph import Arc, Graph, Node, Side
from fly_in.model import Network
from fly_in.parser import MapParser
from fly_in.cost import entry_cost

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"
ALL_MAPS = sorted(MAPS_DIR.glob("*/*.txt"))


def _all_arcs(graph: Graph) -> list[Arc]:
    return [a for arcs in graph._arcs_from.values() for a in arcs]


def _is_forward(arc: Arc) -> bool:
    """True for arcs _add_arc was asked for, False for their twins.

    Forward arcs run z_in -> z_out inside a zone, or a_out -> b_in
    across a connection; twins run the other way round.
    """
    if arc.tail.zone == arc.head.zone:
        return arc.tail.side is Side.IN
    return arc.tail.side is Side.OUT


def _forward(graph: Graph) -> list[Arc]:
    return [a for a in _all_arcs(graph) if _is_forward(a)]


def _zone_arc(graph: Graph, name: str) -> Arc:
    """The z_in -> z_out arc of the zone called name."""
    (arc,) = [
        a
        for a in _forward(graph)
        if a.tail.zone == a.head.zone and a.tail.zone.name == name
    ]
    return arc


def _link_arc(graph: Graph, a: str, b: str) -> Arc:
    """The a_out -> b_in arc."""
    (arc,) = [
        x
        for x in _forward(graph)
        if x.tail.zone.name == a and x.head.zone.name == b
    ]
    return arc


def _graph(write_map: WriteMap, text: str) -> Graph:
    return Graph(MapParser(write_map(text)).parse_file())


def _passable(network: Network) -> tuple[int, int]:
    """Number of passable zones, and of connections between two of them."""
    zones = [z for z in network.zones if z.attributes.type.is_passable]
    conns = [
        c
        for c in network.connections
        if all(z.attributes.type.is_passable for z in c.zones)
    ]
    return len(zones), len(conns)


# ~~~~~ invariants, checked on every shipped map ~~~~~
@pytest.fixture(params=ALL_MAPS, ids=lambda p: f"{p.parent.name}/{p.stem}")
def network(request: pytest.FixtureRequest) -> Network:
    path: Path = request.param
    return MapParser(path).parse_file()


def test_arc_counts(network: Network) -> None:
    """One arc per zone, two per connection, and a twin for each."""
    graph = Graph(network)
    nb_zones, nb_conns = _passable(network)
    assert len(_forward(graph)) == nb_zones + 2 * nb_conns
    assert len(_all_arcs(graph)) == 2 * (nb_zones + 2 * nb_conns)


def test_twins_point_at_each_other(network: Network) -> None:
    for arc in _all_arcs(Graph(network)):
        assert arc.twin is not None
        assert arc.twin is not arc
        assert arc.twin.twin is arc
        assert (arc.twin.tail, arc.twin.head) == (arc.head, arc.tail)
        assert arc.twin.cost == (-arc.cost[0], -arc.cost[1])


def test_twins_start_closed(network: Network) -> None:
    for arc in _forward(Graph(network)):
        assert arc.twin is not None
        assert arc.flow == 0
        assert arc.residual == arc.cap
        assert arc.twin.cap == 0
        assert arc.twin.residual == 0


def test_arcs_stored_under_their_tail(network: Network) -> None:
    graph = Graph(network)
    for node, arcs in graph._arcs_from.items():
        for arc in arcs:
            assert arc.tail == node


def test_every_connection_goes_both_ways(network: Network) -> None:
    graph = Graph(network)
    for conn in network.connections:
        a, b = conn.zones
        if not all(z.attributes.type.is_passable for z in conn.zones):
            continue
        for tail, head in ((a, b), (b, a)):
            arc = _link_arc(graph, tail.name, head.name)
            assert arc.cap == conn.max_link_capacity
            assert arc.cost == entry_cost(head)


def test_capacities_never_exceed_fleet(network: Network) -> None:
    nb = len(network.drones)
    for arc in _forward(Graph(network)):
        if arc.tail.zone == arc.head.zone:
            assert 1 <= arc.cap <= nb


def test_source_and_sink(network: Network) -> None:
    graph = Graph(network)
    assert graph.source == Node(network.start, Side.OUT)
    assert graph.sink == Node(network.end, Side.IN)
    assert graph.arcs_from(graph.source)
    assert graph.arcs_from(graph.sink)


def test_arcs_from_unknown_node(network: Network) -> None:
    """No arcs means [], and asking must not add the node to the graph."""
    graph = Graph(network)
    before = len(graph._arcs_from)
    ghost = Node(network.start, Side.IN)
    graph._arcs_from.pop(ghost)
    assert graph.arcs_from(ghost) == []
    assert len(graph._arcs_from) == before - 1


# ~~~~~ hand-made maps ~~~~~
def test_zone_capacity_is_max_drones(write_map: WriteMap) -> None:
    graph = _graph(
        write_map,
        map(
            hub("mid", meta=[max_drones(2)]),
            link("start", "mid"),
            link("mid", "end"),
            nb_line=nb_drones(5),
        ),
    )
    assert _zone_arc(graph, "mid").cap == 2


def test_capacities_clamped_to_fleet(write_map: WriteMap) -> None:
    """Terminals are UNLIMITED and mid holds more than the fleet."""
    graph = _graph(
        write_map,
        map(
            hub("mid", meta=[max_drones(10)]),
            link("start", "mid"),
            link("mid", "end"),
            nb_line=nb_drones(3),
        ),
    )
    for name in ("start", "mid", "end"):
        assert _zone_arc(graph, name).cap == 3


def test_link_capacity(write_map: WriteMap) -> None:
    graph = _graph(
        write_map,
        map(
            link_line=link("start", "end", meta=[max_link_capacity(4)]),
        ),
    )
    assert _link_arc(graph, "start", "end").cap == 4
    assert _link_arc(graph, "end", "start").cap == 4


@pytest.mark.parametrize(
    ("kind", "turns", "bonus"),
    [("normal", 1, 0), ("restricted", 2, 0), ("priority", 1, -1)],
)
def test_link_cost_is_entry_cost_of_head(
    write_map: WriteMap, kind: str, turns: int, bonus: int
) -> None:
    graph = _graph(
        write_map,
        map(
            hub("mid", meta=[zone(kind)]),
            link("start", "mid"),
            link("mid", "end"),
        ),
    )
    assert _link_arc(graph, "start", "mid").cost == (turns, bonus)
    # leaving mid costs whatever entering the head costs, not mid's type
    assert _link_arc(graph, "mid", "start").cost == entry_cost(
        graph.source.zone
    )


def test_zone_arc_is_free(write_map: WriteMap) -> None:
    graph = _graph(
        write_map,
        map(
            hub("mid", meta=[zone("restricted")]),
            link("start", "mid"),
            link("mid", "end"),
        ),
    )
    assert _zone_arc(graph, "mid").cost == (0, 0)


def test_blocked_zone_left_out(write_map: WriteMap) -> None:
    graph = _graph(
        write_map,
        map(
            hub("wall", meta=[zone("blocked")]),
            link("start", "wall"),
            link("wall", "end"),
        ),
    )
    names = {
        n.zone.name for a in _all_arcs(graph) for n in (a.tail, a.head)
    }
    assert "wall" not in names
    # only the start-end link and the two terminals remain
    assert len(_forward(graph)) == 2 + 2


def test_unconnected_start_end(write_map: WriteMap) -> None:
    """Source and sink exist even when no arc joins them."""
    graph = _graph(
        write_map,
        map(
            hub("wall", meta=[zone("blocked")]),
            link("start", "wall"),
            link("wall", "end"),
            link_line=None,
        ),
    )
    # only the two terminals' own z_in -> z_out arcs are left
    assert len(_forward(graph)) == 2
    assert graph.source.zone.name == "start"
    assert graph.sink.zone.name == "end"


def test_negative_capacity_rejected() -> None:
    network = MapParser(MAPS_DIR / "easy" / "01_linear_path.txt").parse_file()
    node = Node(network.start, Side.IN)
    with pytest.raises(ValueError, match="negative capacity"):
        Arc(node, node, -1, (0, 0))
