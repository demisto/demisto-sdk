from pathlib import Path

from typer.testing import CliRunner


class TestValidateMyPyGlobalIgnore:
    from demisto_sdk.scripts.prevent_mypy_global_ignore import main as func

    added_code = "print('some added code')"
    added_mypy_ignore = f"{added_code}  # type: ignore"
    added_mypy_ignore_tab = "\t# type: ignore"
    added_mypy_global_ignore = "# type: ignore"
    added_mypy_global_ignore_1 = "#type: ignore"
    added_mypy_global_ignore_2 = "# type:ignore"
    added_mypy_global_ignore_3 = "#type:ignore"

    mypy_disable_error_code = '# mypy: disable-error-code="attr-defined"'
    added_mypy_disable_error_code = f"{added_code}\n{mypy_disable_error_code}"

    mypy_disable_multiple_error_codes = '# mypy: disable-error-code="attr-defined,misc"'
    added_mypy_disable_multiple_error_codes = (
        f"{added_code}\n{mypy_disable_multiple_error_codes}"
    )

    mypy_disable_error_code_no_space = '#mypy: disable-error-code="attr-defined"'
    added_mypy_disable_error_code_no_space = (
        f"{added_code}\n{mypy_disable_error_code_no_space}"
    )

    mypy_disable_error_code_no_space_2 = '# mypy:disable-error-code="attr-defined"'
    added_mypy_disable_error_code_no_space_2 = (
        f"{added_code}\n{mypy_disable_error_code_no_space_2}"
    )

    """
    Test class for validation of mypy global ignore.
    """

    @classmethod
    def test_mypy_ignore_not_added(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        non-mypy ignore comment is added.

        Given:
        - A Python file.

        When:
        - Valid Python code is added to the intengration code.

        Then:
        - Exit code 0 is returned.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_code)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 0

    @classmethod
    def test_mypy_ignore_add_not_global(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        non-global mypy ignore comment is added.

        Given:
        - A Python file.

        When:
        - Valid Python code is added to the intengration code.

        Then:
        - Exit code 0 is returned.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_ignore)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 0

    @classmethod
    def test_mypy_ignore_add_tab(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a non-global mypy ignore comment is added in the beginning
        of the statement with a tab.

        Given:
        - A Python file.

        When:
        - Type ignore comment is added to the end of a print
        statement.

        Then:
        - Exit code 0 is returned.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_ignore_tab)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 0

    @classmethod
    def test_mypy_ignore_add_global(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        global mypy ignore comment is added.

        Given:
        - A Python file.

        When:
        - A global ignore mypy type comment is added.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_global_ignore)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1

        assert (
            f"File '{py_file_path}' in line 1 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_ignore_add_global_no_whitespace_1(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        between '#' and 'type'.

        Given:
        - A Python file.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_global_ignore_1)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1

        assert (
            f"File '{py_file_path}' in line 1 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_ignore_add_global_no_whitespace_2(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        between ':' and 'ignore'.

        Given:
        - A Python file.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_global_ignore_2)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1

        assert (
            f"File '{py_file_path}' in line 1 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_ignore_add_global_no_whitespace_3(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        in the ignore comment.

        Given:
        - A Python file.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_global_ignore_3)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1

        assert (
            f"File '{py_file_path}' in line 1 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_disable_error_code(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a mypy disable error code is present in the source code.

        Given:
        - A Python file.

        When:
        - A mypy disable error code is added.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_disable_error_code)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1
        assert (
            f"File '{py_file_path}' in line 2 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_disable_multiple_error_code(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        multiple mypy disable error codes are present in the source code.

        Given:
        - A Python file.

        When:
        - 2 mypy disable error codes are added.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_disable_multiple_error_codes)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1
        assert (
            f"File '{py_file_path}' in line 2 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_disable_error_code_no_whitespace(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a mypy disable error code is present in the source code without a
        whitespace.

        Given:
        - A Python file.

        When:
        - A mypy disable error code is added without whitespace
        between the '#' and 'mypy'.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_disable_error_code_no_space)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1
        assert (
            f"File '{py_file_path}' in line 2 sets global mypy ignore. Please remove it."
            in result.stdout
        )

    @classmethod
    def test_mypy_disable_error_code_no_whitespace_2(cls, tmp_path: Path):
        """
        Test the behavior of `prevent_mypy_global_ignore` when
        a mypy disable error code is present in the source code without a
        whitespace.

        Given:
        - A Python file.

        When:
        - A mypy disable error code is added without whitespace
        between the 'mypy:' and 'disable-error-code'.

        Then:
        - Exit code 1 is returned.
        - The output includes a message to remove the global ignore.
        """

        py_file_path = tmp_path / "a.py"
        py_file_path.write_text(cls.added_mypy_disable_error_code_no_space_2)

        result = CliRunner().invoke(cls.func, [str(py_file_path)])

        assert result.exit_code == 1
        assert (
            f"File '{py_file_path}' in line 2 sets global mypy ignore. Please remove it."
            in result.stdout
        )
