import os
from mock import patch


class TestCreateFailedUnitTestsFile:
    def setup(self):
        self.outfile = ''

    def teardown(self):
        if self.outfile:
            os.remove(self.outfile)

    def test_sanity(self):
        from demisto_sdk.commands.lint.lint_manager import LintManager

        self.outfile = 'single_failed_package.txt'

        LintManager.create_failed_unittests_file(['asdf'], self.outfile)
        assert os.path.isfile(self.outfile)
        with open(self.outfile) as file_:
            file_content = file_.read()

        assert file_content == 'asdf'

    def test_several_tests_failures(self):
        from demisto_sdk.commands.lint.lint_manager import LintManager

        self.outfile = 'several_failed_packages.txt'

        LintManager.create_failed_unittests_file(['test', 'test2', 'test'], self.outfile)
        assert os.path.isfile(self.outfile)
        with open(self.outfile) as file_:
            file_content = file_.read()

        assert file_content == 'test\ntest2\ntest'

    def test_no_test_failures(self):
        from demisto_sdk.commands.lint.lint_manager import LintManager

        self.outfile = 'several_failed_packages.txt'

        LintManager.create_failed_unittests_file([], self.outfile)
        assert os.path.isfile(self.outfile)
        with open(self.outfile) as file_:
            file_content = file_.read()

        assert file_content == ''

    @patch('demisto_sdk.commands.lint.lint_manager.get_dev_requirements')
    @patch('demisto_sdk.commands.lint.lint_manager.LintManager.create_failed_unittests_file')
    def test_no_outfile_set(self, create_failed_unittests_file, get_dev_requirements):
        _ = get_dev_requirements  # unused
        from demisto_sdk.commands.lint.lint_manager import LintManager
        lint_manager = LintManager('../../../../tests')
        lint_manager._print_final_results(['test'], ['test2'])
        assert create_failed_unittests_file.call_count == 0
        assert not os.path.isfile(self.outfile)
