class TestGatherFacts:
    """python version, docker images, yml parsing, test exists, lint files"""

    def test_not_valid_yml_parsed(self):
        """Not valid yml parsed - should not continue"""

    def test_not_valid_python_version(self):
        """Not valid python version - should not continue"""

    def test_not_valid_docker_images(self):
        """Not valid docker images - should not continue"""

    def test_tests_not_exists(self):
        """Should configure facts to False"""

    def test_tests_exists(self):
        """Should configure facts to True"""

    def test_lint_files_not_exists(self):
        """Should configure with empty list"""

    def test_lint_files_commonserverpython(self):
        """Should configure with commonserverpython.py"""


class TestFlake8:
    def test_run_flake8_no_errors(self):
        """Flake8 returns no errors"""

    def test_run_flake8_with_errors(self):
        """Flake8 returns errors"""

    def test_run_flake8_with_exception(self):
        """Flake8 run exception"""


class TestBandit:
    def test_run_bandit_no_errors(self):
        """Bandit returns no errors"""

    def test_run_bandit_with_errors(self):
        """Bandit returns errors"""

    def test_run_bandit_with_exception(self):
        """Bandit run exception"""


class TestMypy:
    def test_run_mypy_no_errors(self):
        """Mypy returns no errors"""

    def test_run_mypy_with_errors(self):
        """Mypy returns errors"""

    def test_run_mypy_with_exception(self):
        """Mypy run exception"""


class TestPylint:
    def test_run_pyliny_no_errors(self):
        """Pylint returns no errors"""

    def test_run_pylint_with_errors(self):
        """Pylint returns errors"""

    def test_run_pylint_with_docker_exception(self):
        """Pylint docker exception"""


class TestPytest:
    def test_run_pytest_no_errors(self):
        """Pytest returns no failed tests"""

    def test_run_pytest_with_errors(self):
        """Pytest returns failed tests"""

    def test_run_pytest_with_docker_exception(self):
        """Pytest docker exception"""


class TestRunLintInHost:
    """Flake8/Bandit/Mypy"""

    def test_run_one_lint_check(self):
        """Run only one lint check"""

    def test_run_two_lint_check(self):
        """Run two lint check"""

    def test_run_all_lint_check(self):
        """Run all lint check"""

    def test_no_lint_files(self):
        """No lint files exsits - not running any lint check"""


class TestRunLintInContainer:
    """Pylint/Pytest"""

    def test_run_only_one_check(self):
        """Run only one check"""

    def test_run_all_check(self):
        """Run all checks"""

    def test_no_lint_files(self):
        """No lint files exsits - not running any lint check"""

    def test_no_tests_found(self):
        """No test files exsits - not running pytest"""
