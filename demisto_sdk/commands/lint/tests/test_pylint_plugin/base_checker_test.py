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
                pylint.testutils.Message(
                    msg_id='invalid-import-common-server-python',
                    node=node_a,
                ),
        ):
            self.checker.visit_importfrom(node_a)
            self.checker.visit_importfrom(node_a)


class TestCommandsImplementedChecker(pylint.testutils.CheckerTestCase):
    """
    Class which tests the functionality of commands checker.
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_regular_if_else_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - if else claus exists when the if contains only one command instead of two.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2']
        node_a = astroid.extract_node("""
            if a == 'test-1': #@
                return true
            else:
                return false
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test2']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_if(node_a)
            self.checker.leave_module(node_a)

        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
            if a == 'test-1' or a == 'test3': #@
                return true
            else:
                return false
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test2']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_if(node_a)
            self.checker.leave_module(node_a)

    def test_test_module_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - if else claus exists when the if contains all commands and test-module.
        Then:
            - Ensure no errors
        """
        self.checker.commands = ['test-1']
        node_a = astroid.extract_node("""
            if a == 'test-1': #@
                return True
            elif a == 'test-module':
                return True
            else:
                return False
        """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_if(node_a)
            self.checker.leave_module(node_a)

    def test_not_command_dict_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Command names are part of a dict when the key is the command name and the value is the function.
            - Two of the commands appear in the dict as keys.
            - The last command does not appear in the dict as a key, instead it appears as a value.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
            {'test-1' : 1, 'test2':2 , 'test': 'test3'} #@
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test3']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_dict(node_a)
            self.checker.visit_call(node_a)
            self.checker.leave_module(node_a)

    def test_all_command_dict_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Command names are part of a dict when the key is the command name and the value is the function.
        Then:
            - Ensure that nothing being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
            {'test-1' : 1, 'test2':2 , 'test3': 3} #@
        """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_dict(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_not_all_if_command_in_list_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Commands appear in the if claus as a list.
            - Two of the commands appear in the list.
            - The last command does not appear in the list.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a, node_b = astroid.extract_node("""
            if a in ['test-1','test2']:  #@
                return False
            elif a in ['test2']:
                return True #@
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test3']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_if(node_a)
            self.checker.visit_if(node_b)
            self.checker.leave_module(node_a)

    def test_all_if_command_in_list_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - All commands appear in the if claus as a list.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
                   if a in ['test-1','test2','test3']:  #@
                       return False
               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_if(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_not_all_if_command_in_tuple_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Commands appear in the if claus as a tuple.
            - Two of the commands appear in the tuple.
            - The last command does not appear in the tuple.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
            if a in ('test-1','test2'):  #@
                return False
            else:
                return True
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test3']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_if(node_a)
            self.checker.leave_module(node_a)

    def test_all_if_command_in_tuple_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - All commands appear in the if claus as a tuple.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
                   if a in ('test-1','test2','test3'):  #@
                       return False
               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_if(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_not_all_if_command_in_set_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Commands appear in the if claus as a tuple.
            - Two of the commands appear in the set.
            - The last command does not appear in the set.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
            if a in {'test-1','test2'}:  #@
                return False
            else:
                return True
        """)
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-commands-exist',
                    node=node_a,
                    args=str(['test3']),
                ),
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.visit_if(node_a)
            self.checker.leave_module(node_a)

    def test_all_if_command_in_set_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - All commands appear in the if claus as a set.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['test-1', 'test2', 'test3']
        node_a = astroid.extract_node("""
                   if a in {'test-1','test2','test3'}:  #@
                       return False
               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_if(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_infer_if_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - All commands appear in the if claus as a tuple.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['integration-name-test-1']
        node_a = astroid.extract_node("""
                A = 'integration-name'
                if demisto.commands() == f'{A}-test-1':  #@
                    return False
               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_if(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_infer_dict_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - All commands appear in the if claus as a tuple.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['integration-name-test1', 'integration-name-test2']
        node_a = astroid.extract_node("""
                A = 'integration-name'
                {f'{A}-test1': run_1, f'{A}-test2': run_2}  #@
               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_dict(node_a)
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='unimplemented-test-module',
                    node=node_a
                )
        ):
            self.checker.leave_module(node_a)

    def test_commands_dismiss_for_feeds_checker(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - For feeds which import from any ApiModule, the commands should not be checks as they are probably implemented
              in the ApiModule itself.
        Then:
            - Ensure that no being added to the message errors of pylint for each appearance
        """
        self.checker.commands = ['integration-name-test1', 'integration-name-test2']
        node_a = astroid.extract_node("""
                from TestApiModule import *


               """)
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_importfrom(node_a)
            self.checker.leave_module(node_a)


class TestCommandResultsIndicatorsChecker(pylint.testutils.CheckerTestCase):
    """
    """
    CHECKER_CLASS = base_checker.CustomBaseChecker

    def test_indicators_exist(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - Invalid use of indicators inside of CommandResults in the code.
        Then:
            - Ensure that the correct message id is being added to the message errors of pylint for each appearance

        """
        node_a = astroid.extract_node("""CommandResults(name=name,test=test,indicators=indicators)""")
        assert node_a
        with self.assertAddsMessages(
                pylint.testutils.Message(
                    msg_id='commandresults-indicators-exists',
                    node=node_a,
                ),
        ):
            self.checker.visit_call(node_a)

    def test_indicators_doesnt_exist(self):
        """
        Given:
            - String of a code part which is being examined by pylint plugin.
        When:
            - No use of  indicators inside of CommandResults in the code.
            - Use of indicator instead of indicators inside of CommandResults.
        Then:
            - Ensure that there is no errors, Check that there is no error message.
        """
        node_a = astroid.extract_node("""CommandResults(name=name,test=test,indicator=indicators)""")
        assert node_a
        with self.assertNoMessages():
            self.checker.visit_call(node_a)
