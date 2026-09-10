from collections.abc import Callable
from pathlib import Path

import pytest


# .fixture will fill in tmp_path
# and assign write_map value of inner function
# before the function is called in code
# welcome to functional land
@pytest.fixture
def write_map(tmp_path: Path) -> Callable[[str], Path]:

    def _write(text: str, name: str = "map.txt") -> Path:
        path = tmp_path / "temp_map.txt"
        path.write_text(text)
        return path

    return _write
