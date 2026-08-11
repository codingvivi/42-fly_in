from dataclassses import dataclass


@dataclass(frozen=True)
class MapParser:
    test: str

    def parse(self) -> None:
        self.test = "Hellowww world"
