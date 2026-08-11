from dataclassses import dataclass


@dataclass
class Network:
    breast: str

    def link(self) -> None:
        print(self.breast)
