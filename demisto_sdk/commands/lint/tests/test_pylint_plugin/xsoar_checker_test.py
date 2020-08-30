import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import base_checker


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


class TestSleepChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_sleep_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - time.sleep(0) exists in the code twice
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        _, node_a, node_b, _ = astroid.extract_node("""
            def test_function(): #@
                time.sleep(60) #@
                time.sleep(70) #@
                return True #@
        """)
        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='sleep-exists',
                    node=node_a,
                ),
                pylint.testutils.Message(
                    msg_id='sleep-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_no_sleep(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - sleep does not exists in the code .
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
    Class which tests the functionality of sys exit checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

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
