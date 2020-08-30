import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import xsoar_checker


class TestMainChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of main checker
    """
    CHECKER_CLASS = xsoar_checker.XsoarChecker

    def test_main_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - main function exists in the code
        Then:
            - Ensure that there is no error message added.
        """
        node_a = astroid.extract_node("""
            def test():
                return False

            def main(): #@
                return True
        """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_a)
            self.checker.leave_module(node_a)

    def test_no_main(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - main function does not exists in the code
        Then:
            - Ensure that the correct error message is added to pylint error message list.
        """
        node_a, node_b, node_c, node_d = astroid.extract_node("""
            def test_function():  #@
                return True  #@
            def another_function():#@
                return False  #@
        """)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='main-func-doesnt-exist',
                    node=node_a,
                ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_c)
            self.checker.leave_module(node_a)
