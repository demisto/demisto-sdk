from demisto_sdk.commands.lint.linter import Linter
from wcmatch.pathlib import Path
from unittest.mock import MagicMock

x = MagicMock(spec=Linter())

x()._run_flake8()

