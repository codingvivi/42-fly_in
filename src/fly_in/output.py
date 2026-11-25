"""Turning the turn log into text: the required lines, colors, stats."""

from typing import NamedTuple

from .model import Zone
from .planning import Plan, lane_length
from .simulation import Turn

RESET = "\033[0m"
DIM = "\033[2m"

# map colors are free-form words (subject: "no fixed list"), so known ones
# get a 256-color code and anything else is printed uncolored
COLORS: dict[str, int] = {
    "black": 240,  # true black vanishes on a dark terminal, so dark gray
    "gray": 245,
    "grey": 245,
    "white": 15,
    "red": 196,
    "darkred": 88,
    "maroon": 88,
    "crimson": 161,
    "orange": 208,
    "brown": 130,
    "gold": 220,
    "yellow": 226,
    "lime": 118,
    "green": 40,
    "cyan": 51,
    "blue": 33,
    "purple": 129,
    "violet": 177,
    "magenta": 201,
    "pink": 213,
}
# "rainbow" gets one of these per letter
RAINBOW = (196, 208, 226, 40, 33, 129)


def _fg(code: int) -> str:
    return f"\033[38;5;{code}m"


def paint(text: str, color: str | None) -> str:
    """Wrap text in the ANSI code for a map color; unknown -> unchanged."""
    if color is None:
        return text
    name = color.lower()
    if name == "rainbow":
        return (
            "".join(
                _fg(RAINBOW[i % len(RAINBOW)]) + ch
                for i, ch in enumerate(text)
            )
            + RESET
        )
    code = COLORS.get(name)
    if code is None:
        return text
    return f"{_fg(code)}{text}{RESET}"


def format_turn(turn: Turn, color: bool = False) -> str:
    """One output line: D<id>-<place> per drone that moved, by drone id.

    A drone still in flight toward a restricted zone shows the connection
    name. With color on, zones are painted in their map color and
    connections are dimmed; the text itself is the same either way.
    """
    parts: list[str] = []
    for drone, place in sorted(turn.items(), key=lambda kv: kv[0].id):
        name = place.name
        if color:
            if isinstance(place, Zone):
                name = paint(name, place.attributes.color)
            else:
                name = f"{DIM}{name}{RESET}"
        parts.append(f"{drone}-{name}")
    return " ".join(parts)


# ~~~~~ stats ~~~~~
class Stats(NamedTuple):
    """Secondary metrics from the subject's scoring section.

    turns          -- total simulation turns, the main score
    drones         -- drones delivered
    lanes          -- lanes that carried at least one drone
    avg_turns      -- average turn a drone lands on
    avg_moves      -- average drones moving per turn
    path_cost      -- sum over drones of their lane's weighted length
    """

    turns: int
    drones: int
    lanes: int
    avg_turns: float
    avg_moves: float
    path_cost: int


def stats(log: list[Turn], plan: Plan) -> Stats:
    """Compute the stats of a finished run from its turn log and plan."""
    # a drone lands on the last turn it moves
    landed: dict[int, int] = {}
    for turn_nbr, turn in enumerate(log, start=1):
        for drone in turn:
            landed[drone.id] = turn_nbr

    drones = len(landed)
    moves = sum(len(turn) for turn in log)
    return Stats(
        turns=len(log),
        drones=drones,
        lanes=len(set(plan.assignment)),
        avg_turns=sum(landed.values()) / drones if drones else 0.0,
        avg_moves=moves / len(log) if log else 0.0,
        path_cost=sum(lane_length(plan.lanes[i]) for i in plan.assignment),
    )


def format_stats(s: Stats) -> str:
    """Stats as a short multi-line summary."""
    return "\n".join(
        (
            f"turns:            {s.turns}",
            f"drones:           {s.drones}",
            f"lanes used:       {s.lanes}",
            f"avg turns/drone:  {s.avg_turns:.2f}",
            f"avg moves/turn:   {s.avg_moves:.2f}",
            f"total path cost:  {s.path_cost}",
        )
    )
