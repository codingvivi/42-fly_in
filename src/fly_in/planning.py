"""Turning lanes into a schedule: how many turns, which drone flies where."""

import heapq

from .cost import entry_cost
from .model import Zone


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
