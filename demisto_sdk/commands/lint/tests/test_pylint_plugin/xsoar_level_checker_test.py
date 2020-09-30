import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import \
    xsoar_level_checker

# You can find documentation about adding new test checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker


class TestDocStringChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = xsoar_level_checker.XsoarChecker

    def test_docs_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Two given functions. Main does not have docs but the Test function does.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.

        """
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                '''
                test docs
                '''
                sys.exit(1)
                return True
            def main(): #@
                try:
                    return True
                except:
                    return False
                    return_error('error')
        """)
        assert node_b is not None and node_a is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

    def test_docs_doesnt_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - two functions exist , both do not have docs.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint regarding the test
             fucntion.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                sys.exit(1)
                return True
            def main(): #@
                return True
                return_error('err')

        """)
        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='docstring-doesnt-exits',
                    node=node_a,
                ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

    def test_docs_doesnt_exists_in_main_only(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - two functions exist , main and another and main does not have docs and the other does.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                '''
                This function has docs string
                '''
                sys.exit(1)
                return True
            def main(): #@
                return True
                return_error('err')

        """)
        assert node_b is not None and node_a is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)
