from pathlib import Path
from typing import List
import pytest
from demisto_sdk.commands.lint.linter import Linter


@pytest.fixture
def linter_obj() -> Linter:
    return Linter(pack_dir=Path(__file__).parent / 'data' / 'Integration' / 'intergration_sample',
                  content_path=Path(__file__).parent / 'test_data',
                  req_3=["pytest==3.0"],
                  req_2=["pytest==2.0"])


@pytest.fixture(scope='session')
def lint_files() -> List[Path]:
    return [Path(__file__).parent / 'test_data' / 'Integration' / 'intergration_sample' / 'intergration_sample.py']
