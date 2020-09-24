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

    def test_number_of_prints(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - print function exists in the code couple of times.
        Then:
            - Ensure that it catches all the prints .
        """
        node_a, node_b = astroid.extract_node("""
            def test_function():
                print("first") #@
                a=1
                if(a==1):
                    print("second") #@
                return True
        """)
        assert node_a is not None and node_b is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='print-exists',
                    node=node_b,
                ),
                pylint.testutils.Message(
                    msg_id='print-exists',
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_a)


class TestSleepChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of Sleep checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_sleep_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - time.sleep(0) exists in the code twice
            - sleep(0) exists in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        _, node_a, node_b, node_c, _ = astroid.extract_node("""
            def test_function(): #@
                a=9
                time.sleep(60) #@
                time.sleep(a) #@
                sleep(100) #@
                return True #@
        """)
        assert node_b is not None and node_a is not None and node_c is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='sleep-exists',
                    node=node_a,
                ),
                pylint.testutils.Message(
                    msg_id='sleep-exists',
                    node=node_b,
                ),
                pylint.testutils.Message(
                    msg_id='sleep-exists',
                    node=node_c,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)

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


class TestExitChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of exit checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_exit_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - exit() exists in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        _, node_a, node_b, = astroid.extract_node("""
            def test_function(): #@
                if True:
                    exit() #@
                return True
            exit() #@
        """)
        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='exit-exists',
                    node=node_a,
                ),
                pylint.testutils.Message(
                    msg_id='exit-exists',
                    node=node_b,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)

    def test_no_exit(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - exit() does not exists in the code .
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


class TestQuithecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of quit checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_exit_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - quit() exists in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        _, node_a = astroid.extract_node("""
            def test_function(): #@
                return True
            quit() #@
        """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='quit-exists',
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)

    def test_no_quit(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - quit() does not exists in the code .
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a, node_b, node_c = astroid.extract_node("""
            def test_function(): #@
                return True #@
                # quit() #@
        """)
        assert node_a is not None and node_b is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.visit_call(node_b)
            self.checker.visit_call(node_c)
