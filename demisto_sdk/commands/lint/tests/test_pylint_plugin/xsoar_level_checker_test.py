import astroid
import pylint.testutils

from demisto_sdk.commands.lint.resources.pylint_plugins import xsoar_level_checker

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
        node_a, node_b = astroid.extract_node(
            """
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
        """
        )
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
        node_a, node_b = astroid.extract_node(
            """
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
        """
        )
        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="missing-arg-type-annoation",
                node=node_b,
            ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

        node_a, node_b = astroid.extract_node(
            """
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
        """
        )

        assert node_b is not None and node_a is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="missing-arg-type-annoation",
                node=node_a,
            ),
            pylint.testutils.MessageTest(
                msg_id="missing-arg-type-annoation",
                node=node_b,
            ),
        ):
            self.checker.visit_functiondef(node_a)
            self.checker.visit_functiondef(node_b)

    def test_not_implemented_error_doesnt_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that in the else claus doesnt raises a NotImplementedError but raises a DemistoError
            - Main function that in the if claus raises a ValueError
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint to the relevent function.
        """
        node = astroid.extract_node(
            """
            def main() -> bool:
                if True:
                    return True
                if b:
                    raise ValueError("this is an error")
                else:
                    raise DemistoError("this is an error")
        """
        )
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="not-implemented-error-doesnt-exist",
                node=node,
            ),
        ):
            self.checker.visit_functiondef(node)

    def test_not_implemented_error_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that in the else claus raises a NotImplementedError
        Then:
            - Ensure that the there was not message added to the checker.
        """
        node = astroid.extract_node(
            """
            def main() -> bool:
                try:
                    if True:
                        return True
                    if b:
                        return False
                    else:
                        raise NotImplementedError("this command wasnt implemented")
                except Exception:
                    pass
        """
        )
        assert node is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_not_implemented_error_exists_in_if_clause(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that in the if clause raises a NotImplementedError.
        Then:
            - Ensure that the there was not message added to the checker.
        """
        node = astroid.extract_node(
            """
            def main() -> bool:
                try:
                    if command not in commands:
                        raise NotImplementedError("this command was not implemented")
                    else:
                        return True
                except Exception:
                    pass
        """
        )
        assert node is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_not_implemented_error_exists_not_inside_else_if_clauses(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that raises a NotImplementedError outside of if or else clauses.
        Then:
            - Ensure that the there was not message added to the checker.
        """
        node = astroid.extract_node(
            """
            def main() -> bool:
                try:
                    raise NotImplementedError("this command was not implemented")
                except Exception:
                    pass
        """
        )
        assert node is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_not_implemented_error_exists_inside_elif_clause(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that in the elif clause raises a NotImplementedError.
        Then:
            - Ensure that the there was not message added to the checker.
        """
        node = astroid.extract_node(
            """
            def main() -> bool:
                try:
                    if True:
                        return True
                    elif command not in commands:
                        raise NotImplementedError("this command was not implemented")
                    else:
                        return True
                except Exception:
                    pass
        """
        )
        assert node is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)

    def test_not_implemented_error_doesnt_exists_on_Script(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Main function that in the else claus raises a NotImplementedError but its in a script path
        Then:
            - Ensure that the there was not message added to the checker.
        """
        self.checker.is_script = True
        node = astroid.extract_node(
            """
            def main() -> bool:
                try:
                    if True:
                        return True
                    if b:
                        return False
                    else:
                        raise DemistoException("this command wasnt implemented")
                except Exception:
                    pass
        """
        )
        assert node is not None
        with self.assertNoMessages():
            self.checker.visit_functiondef(node)


class TestDirectAccessDictChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests if a direct access to dict was found and suggests .get instead.
    """

    CHECKER_CLASS = xsoar_level_checker.XsoarChecker

    def test_direct_access_doesnt_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - direct access to dict object doesnt exist
            - get access to dict exists
        Then:
            - Ensure that there was no message errors of pylint
        """
        node_a = astroid.extract_node(
            """
            args = {'test1':1,'test2':2}
            args.get('test1') #@
        """
        )

        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subscript(node_a)

        node_a = astroid.extract_node(
            """
            params = {'test1':1,'test2':2}
            params.get('test1') #@
        """
        )

        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subscript(node_a)

        node_a = astroid.extract_node(
            """
            params = {'test1':1,'test2':2}
            params['test1'] = a #@
        """
        )

        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subscript(node_a)

    def test_direct_access_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - direct access to dict object exist
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint to the relevent function.
        """
        node_a = astroid.extract_node(
            """
            args = {'test1':1,'test2':2}
            a = args['test1'] #@
        """
        )
        node_b = node_a.value
        assert node_a is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="direct-access-args-params-dict-exist",
                node=node_b,
            ),
        ):
            self.checker.visit_subscript(node_b)

        node_a = astroid.extract_node(
            """
            b = demisto.args()['test1'] #@
        """
        )
        assert node_a is not None
        node_b = node_a.value
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="direct-access-args-params-dict-exist",
                node=node_b,
            ),
        ):
            self.checker.visit_subscript(node_b)

        node_a = astroid.extract_node(
            """
            b = demisto.params()['test1'] #@
        """
        )
        node_b = node_a.value
        assert node_a is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="direct-access-args-params-dict-exist",
                node=node_b,
            ),
        ):
            self.checker.visit_subscript(node_b)

        node_a = astroid.extract_node(
            """
            a = params['test1'] #@
        """
        )
        node_b = node_a.value
        assert node_b is not None
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="direct-access-args-params-dict-exist",
                node=node_b,
            ),
        ):
            self.checker.visit_subscript(node_b)
