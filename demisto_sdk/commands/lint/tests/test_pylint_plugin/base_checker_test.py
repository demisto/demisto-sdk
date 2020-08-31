import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import base_checker

# You can find documentation about adding new test checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker


class TestPrintChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of print checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_print(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - print function exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                print('catch this print') #@
                return True #@
        """)
        assert node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='print-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_b)

    def test_no_print(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - print function does not exists in the code
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.
        """
        node_a, node_b = astroid.extract_node("""
            def test_function():  #@
                return True #@
        """)
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_print_in_docstr(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - print function exists in the code but only as a comment
        Then:
            - Ensure that it does not raise any errors, Check that there is no error message.
        """
        node_a = astroid.extract_node("""
            def test_function():
                '''this is doc string of print('test') function''' #@
                return True
        """)
        assert node_a is None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)


class TestSysExitChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_sys_exit_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sys.exit exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        _, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                sys.exit(0) #@
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
                ''' this is sys.exit(0) in doc string test''' #@
                # this is sys.exit(0) in comment #@
                return True
        """)
        assert node_a is None and node_b is None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
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
