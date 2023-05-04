from typing import Optional

import pytest

from demisto_sdk.commands.common.cpu_count import (
    DEMISTO_SDK_MAX_CPU_CORES,
    cpu_count,
    os,
)


@pytest.mark.parametrize(
    "env_var_value, expected_result",
    [
        (None, os.cpu_count() - 1),
        ("", os.cpu_count() - 1),
        ("not_a_number", os.cpu_count() - 1),
        ("2", 2),
        ("10", min(10, os.cpu_count())),
        ("0", 1),
        ("-1", 1),
    ],
)
def test_cpu_count(monkeypatch, env_var_value: Optional[str], expected_result: int):
    monkeypatch.setenv(DEMISTO_SDK_MAX_CPU_CORES, env_var_value)
    assert cpu_count() == expected_result
