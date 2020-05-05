from pathlib import Path

from TestSuite.integration import Integration


class Script(Integration):
    # Im here just to have one!!!
    def __init__(self, tmpdir: Path, name):
        super().__init__(tmpdir, name)
