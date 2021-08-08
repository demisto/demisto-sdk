import astroid
import pylint.testutils

from demisto_sdk.commands.lint.resources.pylint_plugins import \
    partner_level_checker

# You can find documentation about adding new test checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker


class TestTryExceptMainChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = partner_level_checker.PartnerChecker

    def test_try_except_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - in main function, try except statement exists.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.

        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                try:
                    return True
                except:
                    return False
                    return_error('error')
        """)
        assert node_b is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_b)

    def test_try_except_finally_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - in main function, try-except-finally statement exists.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.

        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                try:
                    return True
                except:
                    return False
                    return_error('error')
                finally:
                    pass
        """)
        assert node_b
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_b)

    def test_try_except_doesnt_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - in main function , there is no try except statement.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                return True
                return_error('err')

        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='try-except-main-doesnt-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_functiondef(node_b)


class TestReturnErrorInMainChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = partner_level_checker.PartnerChecker

    def test_return_error_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_error exists in main function.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.

        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                try:
                    return True
                except:
                    return_error('not ok')

        """)
        assert node_b is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_b)

    def test_return_error_dosnt_exists_in_main(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - in main function , there is no return_error statement and in no other section in the code.
        Then:
            - Ensure that the correct message id is being added to the messages of pylint
        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                try:
                    return True
                except:
                    return False

        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='return-error-does-not-exist-in-main',
                    node=node_b,
                ),
        ):
            self.checker.visit_functiondef(node_b)

    def test_return_error_exists_not_in_main(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_error statment exists but not in main function but in a different one.
        Then:
            - Ensure that the correct message id is being added to the messages of pylint
        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return_error('error')
            def main():
                try:
                    return True
                except:
                    return False

        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='return-error-does-not-exist-in-main',
                    node=node_b,
                ),
        ):
            self.checker.visit_functiondef(node_b)


class TestReturnErrorCountChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = partner_level_checker.PartnerChecker

    def test_return_error_exists_once(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_error exists only once.
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.

        """
        node_b = astroid.extract_node("""
            def test_function():
                sys.exit(1)
                return True
            def main():
                try:
                    return True
                except:
                    return_error('not ok')

        """)
        assert node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_b)
            self.checker.leave_module(node_b)

    def test_return_error_exists_more_than_once(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_error usage exists more than once in the code.
        Then:
            - Ensure that the correct message id is being added to the messages of pylint
        """
        node_a, node_b = astroid.extract_node("""
            return_error()
            def test_function():
                return_error('again') #@
            def main():
                try:
                    return True
                except:
                    return_error('not ok') #@

        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='too-many-return-error',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_b)
