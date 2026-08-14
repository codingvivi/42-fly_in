from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class Drone:
    id: int

    def __str__(self) -> str:
        return f"D{self.id}"
