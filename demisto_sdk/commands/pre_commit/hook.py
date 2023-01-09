from dataclasses import dataclass
from typing import Tuple


@dataclass
class Hook:
    id: str
    language: str
    args: Tuple[str, ...]