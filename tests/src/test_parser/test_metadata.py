"""The bracketed `[key=value ...]` block on zone and connection lines.

Split three ways: the delimiters and key=value shape (handled by the
parser's text helpers), then the values themselves (handled by pydantic,
separately for zones and connections since they accept different keys).
"""

import re

import pytest
from helpers import (
    Row,
    WriteMap,
    color,
    hub,
    link,
    map,
    max_drones,
    max_link_capacity,
    named_arg,
    params,
    zone,
)

from fly_in.parser import MapParser, ParseError

ZONE_CHOICES = "'priority', 'normal', 'restricted' or 'blocked'"
NOT_AN_INT = "Input should be a valid integer"
AT_LEAST_ONE = "Input should be greater than or equal to 1"
NO_EXTRAS = "Extra inputs are not permitted"
# Connection is a pydantic dataclass, so it words the same rule differently
# from the BaseModel used for zone attributes
UNEXPECTED = "Unexpected keyword argument"


# the builders always close the bracket, so delimiter faults are written
# out in full; without a '[' the fragment reads as a fourth positional
BAD_METADATA_FORMAT: list[Row] = [
    ("hub: a 0 0 [zone=normal", "line 5: Unterminated [", "unterminated"),
    ("hub: a 0 0 [", "line 5: Unterminated [", "unterminated_empty"),
    (
        "hub: a 0 0 zone=normal]",
        "line 5: required format: name x y",
        "closed_never_opened",
    ),
    (
        hub("a", meta=["zone"]),
        "line 5: required metadata format: key=value",
        "no_equals",
    ),
    (hub("a", meta=["=normal"]), f"line 5: {NO_EXTRAS}", "empty_key"),
]


@pytest.mark.parametrize(
    ("zone_line", "error_text"), params(BAD_METADATA_FORMAT)
)
def test_bad_metadata_format(
    write_map: WriteMap, zone_line: str, error_text: str
) -> None:
    map_txt = map(zone_line, link("start", "a"))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


# 'zone=a=b' splits once, so the value keeps the second '='
BAD_ZONE_METADATA: list[Row] = [
    (
        zone("bogus"),
        f"line 5: zone: Input should be {ZONE_CHOICES}",
        "unknown",
    ),
    (zone(""), f"line 5: zone: Input should be {ZONE_CHOICES}", "empty"),
    (
        "zone=a=b",
        f"line 5: zone: Input should be {ZONE_CHOICES}",
        "two_equals",
    ),
    (max_drones(0), f"line 5: max_drones: {AT_LEAST_ONE}", "cap_zero"),
    (max_drones(-1), f"line 5: max_drones: {AT_LEAST_ONE}", "cap_negative"),
    (max_drones("abc"), f"line 5: max_drones: {NOT_AN_INT}", "cap_text"),
    (max_drones(1.5), f"line 5: max_drones: {NOT_AN_INT}", "cap_float"),
    (named_arg("bogus", 1), f"line 5: bogus: {NO_EXTRAS}", "unknown_key"),
    (
        named_arg("max_link_capacity", 2),
        f"line 5: max_link_capacity: {NO_EXTRAS}",
        "connection_key_on_zone",
    ),
]


@pytest.mark.parametrize(("meta", "error_text"), params(BAD_ZONE_METADATA))
def test_bad_zone_metadata_value(
    write_map: WriteMap, meta: str, error_text: str
) -> None:
    map_txt = map(hub("a", meta=[meta]), link("start", "a"))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


# the zone spelling of capacity must not work on a connection
BAD_CONNECTION_METADATA: list[Row] = [
    (
        max_link_capacity(0),
        f"line 4: max_link_capacity: {AT_LEAST_ONE}",
        "cap_zero",
    ),
    (
        max_link_capacity("abc"),
        f"line 4: max_link_capacity: {NOT_AN_INT}",
        "cap_text",
    ),
    (zone("normal"), f"line 4: zone: {UNEXPECTED}", "zone_key"),
    (color("green"), f"line 4: color: {UNEXPECTED}", "color_key"),
    (max_drones(2), f"line 4: max_drones: {UNEXPECTED}", "zone_capacity_key"),
]


@pytest.mark.parametrize(
    ("meta", "error_text"), params(BAD_CONNECTION_METADATA)
)
def test_bad_connection_metadata_value(
    write_map: WriteMap, meta: str, error_text: str
) -> None:
    map_txt = map(link_line=link("start", "end", meta=[meta]))
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()
