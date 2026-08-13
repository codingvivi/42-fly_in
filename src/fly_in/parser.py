from pathlib import Path

from .network import Network


class MapParser:
    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def parse(self) -> Network:
        return Network(breast=str(self._path))
