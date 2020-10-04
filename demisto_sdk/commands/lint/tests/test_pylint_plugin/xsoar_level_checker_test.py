import astroid
import pylint.testutils
from demisto_sdk.commands.lint.resources.pylint_plugins import \
    xsoar_level_checker

# You can find documentation about adding new test checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker


class TestTypeAnnotationsChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests that all functions have type annotations .
    """
    CHECKER_CLASS = xsoar_level_checker.XsoarChecker

    def test_type_annotations_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - return_output exists in the code
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint
        """
        node_a, node_b = astroid.extract_node("""
            def test_num1(a: str, b:int) ->str: #@
                '''
                function docs
                '''
                return "test function"
            def test_num2(a: bool, b: bool, c:int) -> bool: #@
                '''
                function docs
                '''
                if a:
                    return True
                if b:
                    return False
                else:
                    return None
        """)
        assert node_b is not None and node_a is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

    def test_args_annotations_doesnt_exist(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Two given function, One does not have type annotations and the other does.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint to the relevent function.
        """
        node_a, node_b = astroid.extract_node("""
            def test_num1(a: str, b:int) ->str: #@
                '''
                function docs
                '''
                return "test function"
            def test_num2(a, b: bool, c:int) -> bool: #@
                '''
                function docs
                '''
                if a:
                    return True
                if b:
                    return False
                else:
                    return None
        """)
        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='missing-arg-type-annoation',
                    node=node_b,
                ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

        node_a, node_b = astroid.extract_node("""
            def test_num1(a, b) ->str: #@
                '''
                function docs
                '''
                return "test function"
            def test_num2(a, b: bool, c:int) -> bool: #@
                '''
                function docs
                '''
                if a:
                    return True
                if b:
                    return False
                else:
                    return None
        """)

        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='missing-arg-type-annoation',
                    node=node_a,
                ),
                pylint.testutils.Message(
                    msg_id='missing-arg-type-annoation',
                    node=node_b,
                ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)
