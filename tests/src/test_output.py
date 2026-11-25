import re
from pathlib import Path

import pytest
from helpers import WriteMap

from fly_in.model import Drone, Location, Zone, ZoneAttribute
from fly_in.output import (
    RESET,
    format_stats,
    format_turn,
    paint,
    stats,
)
from fly_in.parser import MapParser
from fly_in.planning import plan
from fly_in.simulation import Simulation, Turn

MAPS_DIR = Path(__file__).parents[2] / "data" / "maps"

RESTRICTED_MAP = """nb_drones: 2
start_hub: s 0 0
hub: r 1 0 [zone=restricted color=red]
end_hub: goal 2 0 [color=mystery]
connection: s-r
connection: r-goal
"""


def _zone(name: str, color: str | None = None) -> Zone:
    return Zone(
        name=name,
        coordinates=Location(0, 0),
        attributes=ZoneAttribute(color=color),
    )


def _run(write_map: WriteMap) -> list[str]:
    network = MapParser(write_map(RESTRICTED_MAP)).parse_file()
    log = Simulation(network, plan(network)).run()
    return [format_turn(turn) for turn in log]


# ~~~~~ paint ~~~~~
def test_paint_known_color() -> None:
    assert paint("a", "red") == f"\033[38;5;196ma{RESET}"


def test_paint_is_case_insensitive() -> None:
    assert paint("a", "RED") == paint("a", "red")


@pytest.mark.parametrize("color", [None, "mystery"])
def test_paint_unknown_or_none_unchanged(color: str | None) -> None:
    assert paint("a", color) == "a"


def test_paint_rainbow_colors_each_letter() -> None:
    out = paint("abc", "rainbow")
    assert out.count("\033[38;5;") == 3
    assert out.endswith(RESET)


# ~~~~~ format_turn ~~~~~
def test_format_subject_example() -> None:
    """The subject's example line."""
    turn: Turn = {Drone(2): _zone("corridorA"), Drone(1): _zone("roof1")}
    assert format_turn(turn) == "D1-roof1 D2-corridorA"


def test_format_sorts_by_id_not_name() -> None:
    turn: Turn = {Drone(10): _zone("a"), Drone(2): _zone("b")}
    assert format_turn(turn) == "D2-b D10-a"


def test_format_empty_turn() -> None:
    assert format_turn({}) == ""


def test_format_restricted_run(write_map: WriteMap) -> None:
    """In flight toward r, a drone shows the connection name."""
    assert _run(write_map) == [
        "D1-s-r",
        "D1-r D2-s-r",
        "D1-goal D2-r",
        "D2-goal",
    ]


def test_color_keeps_text(write_map: WriteMap) -> None:
    """Stripping the escape codes gives back the plain line."""
    network = MapParser(write_map(RESTRICTED_MAP)).parse_file()
    log = Simulation(network, plan(network)).run()
    for turn in log:
        colored = format_turn(turn, color=True)
        assert re.sub(r"\033\[[0-9;]*m", "", colored) == format_turn(turn)


def test_color_paints_zone_dims_connection(write_map: WriteMap) -> None:
    network = MapParser(write_map(RESTRICTED_MAP)).parse_file()
    first, second, *_ = Simulation(network, plan(network)).run()
    assert format_turn(first, color=True) == f"D1-\033[2ms-r{RESET}"
    assert f"\033[38;5;196mr{RESET}" in format_turn(second, color=True)


# ~~~~~ stats ~~~~~
def test_stats_restricted_run(write_map: WriteMap) -> None:
    network = MapParser(write_map(RESTRICTED_MAP)).parse_file()
    p = plan(network)
    s = stats(Simulation(network, p).run(), p)
    assert s.turns == 4
    assert s.drones == 2
    assert s.lanes == 1
    assert s.avg_turns == 3.5  # D1 lands turn 3, D2 turn 4
    assert s.avg_moves == 6 / 4
    assert s.path_cost == 6  # each lane is r (2) + goal (1)


@pytest.mark.parametrize(
    "path", sorted(MAPS_DIR.glob("*/*.txt")), ids=lambda p: p.stem
)
def test_stats_match_plan(path: Path) -> None:
    network = MapParser(path).parse_file()
    p = plan(network)
    s = stats(Simulation(network, p).run(), p)
    assert s.turns == p.turns
    assert s.drones == len(network.drones)
    assert "turns:" in format_stats(s)
