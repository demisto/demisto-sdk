import astroid
import pylint.testutils

from demisto_sdk.commands.lint.resources.pylint_plugins import branch_base_checker


class TestLOGChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of exit checker .
    """

    CHECKER_CLASS = branch_base_checker.BranchCustomBaseChecker

    def test_LOG_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.log() exists in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        _, node_a, _ = astroid.extract_node(
            """
            def test_function(): #@
                LOG("Some log message") #@
                return True #@
        """
        )
        assert node_a is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="LOG-exists",
                node=node_a,
            )
        ):
            self.checker.visit_call(node_a)

    def test_no_LOG(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.log() does not exists in the code .
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b, _ = astroid.extract_node(
            """
            def test_function(): #@
                # LOG("Some log message") #@
                return True #@
        """
        )
        assert node_a is not None and node_b is None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
