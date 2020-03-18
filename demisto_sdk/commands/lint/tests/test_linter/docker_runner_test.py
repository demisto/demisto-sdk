
class TestCreateImage:
    def test_build_image_no_errors(self):
        pass

    def test_build_image_template_error(self):
        pass

    def test_run_pylint_with_docker_exception(self):
        pass


class TestPylint:
    def test_run_pylint_no_errors(self):
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
