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


class TestImportCommonServerPythonChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of commonServerPython import checker .
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_valid_common_server_python_import(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - valid import of commonServerPython exists in the code.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        node_a = astroid.extract_node("""from CommonServerPython import *""")
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_importfrom(node_a)

    def test_invalid_common_server_python_import(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Invalid import of commonServerPython exists in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a = astroid.extract_node("""from CommonServerPython import DemistoException""")
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='invalid-import-common-server-python',
                    node=node_a,
                ),
        ):
            self.checker.visit_importfrom(node_a)


class TestAllArgsImplementedChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests that all arguments from yml file are implemented in the code.
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_one_arg_isnt_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - One unimplemented arguments in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        self.checker.args_list = ['test']
        node_a = astroid.extract_node("""
            def test_function():
                args.get('yaa','')  #@
         """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-args-exist',
                    args=str(['test']),
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_some_args_arent_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Two unimplemented arguments in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        self.checker.args_list = ['test1', 'test2']
        node_a = astroid.extract_node("""
            def test_function():
                test1 = "this is a test"  #@
         """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-args-exist',
                    args=str(['test1', 'test2']),
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_all_args_are_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - all args are implemented in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        self.checker.args_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                demisto.args().get('test1' ,'')  #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

        self.checker.args_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                args.get('test1')  #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_all_index_args_are_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - all args are implemented in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        self.checker.args_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                args['test1'] #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)

        self.checker.args_list = ['test1']
        node_a = astroid.extract_node("""
                    def test_function():
                        demisto.args()['test1'] #@
                 """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)


class TestAllParamsImplementedChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests that all params from yml file are implemented in the code.
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_some_get_params_arent_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Two unimplemented params in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        self.checker.param_list = ['test1', 'test2']
        node_a = astroid.extract_node("""
            def test_function():
                test1 = "this is a test"  #@
         """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-params-exist',
                    args=str(['test1', 'test2']),
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

        self.checker.param_list = ['test1', 'test2']
        node_a = astroid.extract_node("""
            def test_function():
                test1 = param.get('test').get('test1')  #@
         """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-params-exist',
                    args=str(['test1', 'test2']),
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_all_get_params_are_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - all params are implemented in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                params.get('test1').get("identifier") #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                params.get('test1')  #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_all_index_params_are_implemented(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - all params are implemented in the code.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
            def test_function():
                params['test1']['identifier'] #@
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)

        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
                    def test_function():
                        params['test1'] #@
                 """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)

        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
                    def test_function():
                        demisto.params()['test1'] #@
                 """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)

        self.checker.param_list = ['test1']
        node_a = astroid.extract_node("""
                    def test_function():
                        demisto.params()['test1']['identifier'] #@
                 """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_subsscript(node_a)
            self.checker.leave_module(node_a)


class TestApiModuleChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests that if there is an import from api module then the feed params are removed from params list
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_api_module_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Parameters list which includes feed required params.
            - Feed Params list which is a list with three required params.
            - import from some ApiModule (HTTPFeedApiModule).
        Then:
             - Ensure that there is no errors, Check that there is no error message.
               This is because the current params list parameters should be implemented in the api module
        """
        self.checker.param_list = ['feedReputation', 'feed']
        self.checker.feed_params = ['feedReputation', 'feed', 'feedInterval']
        node_a = astroid.extract_node("""
            from HTTPFeedApiModule import *
         """)
        assert node_a is not None
        with self.assertNoMessages():
            self.checker.visit_importfrom(node_a)
            self.checker.leave_module(node_a)

    def test_api_module_doesnt_exists(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Parameters list which includes feed required params.
            - Feed Params list which is empty.
            - No import from any ApiModule.
        Then:
            - Ensure that the correct error messages is printed, as this is not implemented within any api module
             all params should be implemented
        """
        self.checker.param_list = ['feedReputation', 'feed']
        self.checker.feed_params = ['feedReputation', 'feed', 'feedInterval']
        node_a = astroid.extract_node("""
                a = test
         """)
        assert node_a is not None
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-params-exist',
                    args=str(['feedReputation', 'feed']),
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)
