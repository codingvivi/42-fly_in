"""Per-line syntax: the positional part of a zone line, and connections.

Everything here fails inside a single line, before any cross-line rule
gets a chance to run.
"""

import re

import pytest
from helpers import (
    LineBuilder,
    Row,
    WriteMap,
    end,
    hub,
    link,
    map,
    params,
    start,
)

from fly_in.parser import MapParser, ParseError

# which builder, which map() keyword it replaces, and the line it lands on
ZONE_BUILDERS: list[Row] = [
    (start, "start_line", 2, "start"),
    (end, "end_line", 3, "end"),
    (hub, None, 5, "hub"),
]

BAD_COORDS = {"none": None, "text": "abc", "float": 1.5}

BAD_ZONE_POSITIONALS: list[Row] = [
    *(
        ({axis: value}, "coordinates must be integers", f"{axis}_{label}")
        for axis in ("x", "y")
        for label, value in BAD_COORDS.items()
    ),
    ({"name": "a-b"}, "'-' is not allowed in names", "name_dash"),
    ({"name": "a b"}, "required format: name x y", "name_space"),
]


@pytest.mark.parametrize(
    ("builder", "map_argname", "line_nbr"), params(ZONE_BUILDERS)
)
@pytest.mark.parametrize(("kwargs", "reason"), params(BAD_ZONE_POSITIONALS))
def test_bad_positional_zone(
    write_map: WriteMap,
    builder: LineBuilder,
    map_argname: str | None,
    line_nbr: int,
    kwargs: dict[str, object],
    reason: str,
) -> None:
    # generate text from current line and arg tested
    line = builder(**kwargs)
    # if line_builder is one of the ones with defaults, override
    # else stick it into the positionals
    map_txt = map(line) if map_argname is None else map(**{map_argname: line})
    expected = f"line {line_nbr}: {reason}"

    with pytest.raises(ParseError, match=re.escape(expected)):
        MapParser(write_map(map_txt)).parse_file()


BAD_CONNECTIONS: list[Row] = [
    (
        link("start", "start"),
        "line 5: a zone cannot connect to itself",
        "self",
    ),
    (
        link("start", "test"),
        "line 5: connection to undefined zone 'test'",
        "unknown",
    ),
    (
        "connection: start end extra",
        "line 5: required format: zone1-zone2",
        "three_tokens",
    ),
    (
        "connection: start-end-extra",
        "line 5: required format: zone1-zone2",
        "three_names",
    ),
    (
        "connection: start-",
        "line 5: required format: zone1-zone2",
        "empty_side",
    ),
]


@pytest.mark.parametrize(
    ("connections", "error_text"), params(BAD_CONNECTIONS)
)
def test_bad_connections(
    write_map: WriteMap, connections: str, error_text: str
) -> None:
    map_txt = map(connections)
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()


KEYWORD_FORMAT = 'line 5: Required format: "keyword: config"'

BAD_KEYWORDS: list[Row] = [
    ("hub a 0 0", KEYWORD_FORMAT, "no_colon"),
    ("hub : a 0 0", KEYWORD_FORMAT, "detached_colon"),
    ("hub", KEYWORD_FORMAT, "bare_word"),
    ("bogus: a 0 0", "line 5: Unknown syntax", "unknown_keyword"),
    ("HUB: a 0 0", "line 5: Unknown syntax", "wrong_case"),
    (":", "line 5: Keyword needs an argument", "colon_only"),
]


@pytest.mark.parametrize(("line", "error_text"), params(BAD_KEYWORDS))
def test_bad_keyword(write_map: WriteMap, line: str, error_text: str) -> None:
    map_txt = map(line)
    with pytest.raises(ParseError, match=re.escape(error_text)):
        MapParser(write_map(map_txt)).parse_file()
