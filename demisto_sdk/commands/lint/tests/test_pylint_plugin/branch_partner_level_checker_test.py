import astroid
import pylint.testutils

from demisto_sdk.commands.lint.resources.pylint_plugins import (
    branch_partner_level_checker,
)


class TestDemistoResultsChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of demisto.results checker .
    """

    CHECKER_CLASS = branch_partner_level_checker.BranchPartnerChecker

    def test_demisto_results_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.results exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b = astroid.extract_node(
            """
            def test_function(): #@
                demisto.results('ok') #@
        """
        )
        assert node_b is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="demisto-results-exists",
                node=node_b,
            ),
        ):
            self.checker.visit_call(node_b)

    def test_no_demisto_results(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.results does not exists in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node(
            """
            def test_function(): #@
                return True #@
        """
        )
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_demisto_results_comments(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.results does not exists in the code but only in comments.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b, node_c = astroid.extract_node(
            """
            def test_function(): #@
                # demisto.results('ok') should be used #@
                return True #@
        """
        )
        assert node_a is not None and node_b is None and node_c is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)


class TestReturnOutputChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of demisto.results checker .
    """

    CHECKER_CLASS = branch_partner_level_checker.BranchPartnerChecker

    def test_return_output_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_output exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b = astroid.extract_node(
            """
            def create_trail(args): #@
                return_outputs(human_readable, ec) #@
        """
        )
        assert node_b is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="return-outputs-exists",
                node=node_b,
            ),
        ):
            self.checker.visit_call(node_b)

    def test_no_return_outputs(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_outputs does not exists in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node(
            """
            def test_function(): #@
                return True #@
        """
        )
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_return_outputs_comments(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_outputs does not exists in the code but only in comments.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b, node_c = astroid.extract_node(
            """
            def test_function(): #@
                # return_outputs(human_readable, ec) should be used #@
                return True #@
        """
        )
        assert node_a is not None and node_b is None and node_c is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)
