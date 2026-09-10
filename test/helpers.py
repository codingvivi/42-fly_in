"""Builders for map-file text: one function per keyword, plus `map`.

Parameters are typed `object`, not `str`/`int`, so error tests can feed
the parser garbage ("abc", 1.5, None) without mypy rejecting the call.
`object` rather than `Any` keeps the bodies type-checked -- every value
here is only ever interpolated, which any object supports.
"""


def _named_args(**kwargs: object) -> str:
    """Render kwargs as ' [k=v k=v]', or '' when there are none."""
    if not kwargs:
        return ""
    return " [" + " ".join(f"{k}={v}" for k, v in kwargs.items()) + "]"


def nb_drones(count: object = 2) -> str:
    return f"nb_drones: {count}"


def start(
    name: object = "start", x: object = 0, y: object = 0, **meta: object
) -> str:
    return f"start_hub: {name} {x} {y}{_named_args(**meta)}"


def end(
    name: object = "end", x: object = 9, y: object = 0, **meta: object
) -> str:
    return f"end_hub: {name} {x} {y}{_named_args(**meta)}"


def link(a: object, b: object, **meta: object) -> str:
    return f"connection: {a}-{b}{_named_args(**meta)}"


def hub(
    name: object = "testhub", x: object = 0, y: object = 0, **meta: object
) -> str:
    return f"hub: {name} {x} {y}{_named_args(**meta)}"


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
