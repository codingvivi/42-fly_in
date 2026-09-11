"""Builders for map-file text: one function per keyword, plus `map`.

Parameters are typed `object`, not `str`/`int`, so error tests can feed
the parser garbage ("abc", 1.5, None) without mypy rejecting the call.
`object` rather than `Any` keeps the bodies type-checked, every value
here is only ever interpolated, which any object supports.

Metadata is a keyword-only list of fragments, so name/x/y keep their
defaults and their positions:

    hub(meta=[zone("priority")])
    hub("a", meta=[zone("priority"), max_drones(2)])

Fragments rather than keywords because the map format allows what
Python keywords cannot express -- a repeated key, or a key that is not
an identifier -- and those are cases the parser has to reject:

    hub("a", meta=[max_drones(1), max_drones(2)])
    hub("a", meta=[named_arg("2bad", 1)])

`list[str]` rather than `Sequence[str]`: a bare `str` satisfies
Sequence[str] and would silently render one character per fragment.
"""


def _named_args(meta: list[str] | None) -> str:
    """Wrap fragments as ' [k=v k=v]', or '' when there are none."""
    if not meta:
        return ""
    return " [" + " ".join(meta) + "]"


# ~~~~~ metadata fragments ~~~~~
def named_arg(key: object, value: object) -> str:
    """One 'key=value' fragment; the escape hatch for odd keys."""
    return f"{key}={value}"


def zone(value: object = "normal") -> str:
    return named_arg("zone", value)


def color(value: object = "green") -> str:
    return named_arg("color", value)


def max_drones(value: object = 1) -> str:
    return named_arg("max_drones", value)


def max_link_capacity(value: object = 1) -> str:
    return named_arg("max_link_capacity", value)


# ~~~~~ one builder per map keyword ~~~~~
def nb_drones(count: object = 2) -> str:
    return f"nb_drones: {count}"


def start(
    name: object = "start",
    x: object = 0,
    y: object = 0,
    *,
    meta: list[str] | None = None,
) -> str:
    return f"start_hub: {name} {x} {y}{_named_args(meta)}"


def end(
    name: object = "end",
    x: object = 9,
    y: object = 0,
    *,
    meta: list[str] | None = None,
) -> str:
    return f"end_hub: {name} {x} {y}{_named_args(meta)}"


def link(a: object, b: object, *, meta: list[str] | None = None) -> str:
    return f"connection: {a}-{b}{_named_args(meta)}"


def hub(
    name: object = "testhub",
    x: object = 0,
    y: object = 0,
    *,
    meta: list[str] | None = None,
) -> str:
    return f"hub: {name} {x} {y}{_named_args(meta)}"


def map(
    *lines: str,
    nb_line: str | None = nb_drones(),
    start_line: str | None = start(),
    end_line: str | None = end(),
    link_line: str | None = link(a="start", b="end"),
) -> str:
    """The preamble plus `lines`; any preamble line drops out on None.

    With the whole preamble present the first extra line is line 5.
    Dropping start_line or end_line also needs link_line=None, or the
    default connection references a zone that no longer exists.
    """
    body = [nb_line, start_line, end_line, link_line, *lines]
    return "".join(f"{ln}\n" for ln in body if ln is not None)
