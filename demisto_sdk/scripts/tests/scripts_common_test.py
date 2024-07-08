import os

import pytest
import typer
from pytest_mock import MockerFixture

from demisto_sdk.scripts.scripts_common import CI_ENV_VAR, ERROR_IS_CI_INVALID, is_ci


class TestIsCI:

    valid_true = "true"
    valid_false = "false"
    invalid_false = "fale"

    def test_valid_true_env_var_supplied(self, mocker: MockerFixture):
        """
        Given:
        - The `CI` environmental variable.

        When:
        - The `CI` environmental variable is set to 'true'.

        Then:
        - `is_ci` returns `True`
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.valid_true})

        actual = is_ci()

        assert actual

    def test_valid_false_env_var_supplied(self, mocker: MockerFixture):
        """
        Given:
        - `CI` environmental variable.

        When:
        - The `CI` environmental variable is set to 'false'.

        Then:
        - `is_ci` returns `False`
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.valid_false})

        actual = is_ci()

        assert not actual

    def test_invalid_env_var_supplied(self, mocker: MockerFixture):
        """
        Given:
        - `CI` environmental variable.

        When:
        - The `CI` environmental variable is set to an invalid value 'fale'.

        Then:
        - `typer.BadParameter` is raised.
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.invalid_false})

        with pytest.raises(typer.BadParameter) as exception_info:
            is_ci()

        assert str(exception_info.value) == ERROR_IS_CI_INVALID.format(
            env_var_str=self.invalid_false
        )

    def test_env_var_not_supplied(self):
        """
        Given:
        - `CI` environmental variable.

        When:
        - The `CI` environmental variable is not set.

        Then:
        - `False` is returned.
        """

        actual = is_ci()

        assert not actual
