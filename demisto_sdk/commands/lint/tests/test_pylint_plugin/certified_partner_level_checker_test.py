import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import \
    certified_partner_level_checker

# You can find documentation about adding new test checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker


class TestSysExitChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = certified_partner_level_checker.CertifiedPartnerChecker

    def test_sys_exit_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sys.exit exists in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                sys.exit(1) #@
                return True #@
        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='sys-exit-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_b)

    def test_sys_exit_in_comments(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sys.exit exists in the code but only as a comment
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function():
                ''' this is sys.exit(1) in doc string test''' #@
                # this is sys.exit(1) in comment #@
                return True
        """)
        assert node_a is None and node_b is None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_sys_exit_non_zero_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sys.exit exists in the code but with 0 as input.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        _, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                sys.exit(0) #@
                return True #@
        """)
        assert node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_b)

    def test_no_sys_exit(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sys.exit does not exists in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                return True #@
        """)
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)


class TestDemistoLogChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of demisto.log checker .
    """
    CHECKER_CLASS = certified_partner_level_checker.CertifiedPartnerChecker

    def test_demisto_log_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.log exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                demisto.log('print this ') #@
                return True #@
        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='demisto-log-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_b)

    def test_no_demisto_log(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.log does not exists in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                return True #@
        """)
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)


class TestMainChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of main checker
    """
    CHECKER_CLASS = certified_partner_level_checker.CertifiedPartnerChecker

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


class TestDemistoResultsChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of demisto.results checker .
    """
    CHECKER_CLASS = certified_partner_level_checker.CertifiedPartnerChecker

    def test_demisto_results_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - demisto.results exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b = astroid.extract_node("""
            def test_function(): #@
                demisto.results('ok') #@
        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='demisto-results-exists',
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
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                return True #@
        """)
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
        node_a, node_b, node_c = astroid.extract_node("""
            def test_function(): #@
                # demisto.results('ok') should be used #@
                return True #@
        """)
        assert node_a is not None and node_b is None and node_c is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)


class TestReturnOutputChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of demisto.results checker .
    """
    CHECKER_CLASS = certified_partner_level_checker.CertifiedPartnerChecker

    def test_return_output_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_output exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b = astroid.extract_node("""
            def create_trail(args): #@
                return_outputs(human_readable, ec) #@
        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='return-outputs-exists',
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
        node_a, node_b = astroid.extract_node("""
            def test_function(): #@
                return True #@
        """)
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_demisto_results_comments(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_outputs does not exists in the code but only in comments.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b, node_c = astroid.extract_node("""
            def test_function(): #@
                # return_outputs(human_readable, ec) should be used #@
                return True #@
        """)
        assert node_a is not None and node_b is None and node_c is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)
