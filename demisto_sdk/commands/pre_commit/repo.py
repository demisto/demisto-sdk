from dataclasses import dataclass
from typing import Tuple
from demisto_sdk.commands.pre_commit.hook import Hook


@dataclass
class Repo:
    repo: str
    rev: str
    hooks: Tuple[Hook, ...]
