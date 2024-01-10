


from pathlib import Path
from TestSuite.repo import Repo


def test_suite(tmpdir):
    ripo = Repo(Path(tmpdir))
    pack  = ripo.create_pack()
    pack.create_integration()
    pack.object
    pack.object
    
