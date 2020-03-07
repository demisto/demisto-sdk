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
