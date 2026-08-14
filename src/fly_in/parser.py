from pathlib import Path

from .network import Network

class ParseError(Exception):
    def __init__(self, lineno: int, cause:str) -> None:
        super().__init__(f"line{lineno}: {cause}")

class MapParser:
    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def parse(self) -> Network:

