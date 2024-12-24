from subprocess import CalledProcessError

import pytest

from demisto_sdk.commands.test_content.constants import SSH_USER
from demisto_sdk.commands.test_content.tools import is_redhat_instance


def raise_exception():
    raise CalledProcessError(1, f"ls -l /home/{SSH_USER}/rhel_ami".split())


class CheckOutputMock:
    stdout = "output"


def test_is_redhat_instance_positive(mocker):
    mocker.patch("subprocess.run", return_value=CheckOutputMock)
    assert is_redhat_instance("instance_ip")


def test_is_redhat_instance_negative(mocker):
    mocker.patch("subprocess.check_output", side_effect=raise_exception)
    assert not is_redhat_instance("instance_ip")


@pytest.mark.parametrize(
    "day, suffix",
    [
        (1, "st"),
        (2, "nd"),
        (3, "rd"),
        (4, "th"),
        (10, "th"),
        (11, "th"),
        (12, "th"),
        (21, "st"),
        (31, "st"),
    ],
)
def test_day_suffix(day, suffix):
    """
    Given:
        - A day of a month.
            case-1: 1 => st.
            case-2: 2 => nd.
            case-3: 3 => rd.
            case-4: 4 => th.
            case-5: 10 => th.
            case-6: 11 => th.
            case-7: 12 => th.
            case-8: 21 => st.
            case-9: 31 => st.

    When:
        - The day_suffix function is running.

    Then:
        - Verify we get the expected results.
    """
    from demisto_sdk.commands.test_content.tools import (
        day_suffix,
    )

    assert day_suffix(day) == suffix
