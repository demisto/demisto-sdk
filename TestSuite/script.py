from pathlib import Path

from TestSuite.integration import Integration


class Script(Integration):
    # Im here just to have one!!!
    def __init__(self, tmpdir: Path, name, repo):
        super().__init__(tmpdir, name, repo)
