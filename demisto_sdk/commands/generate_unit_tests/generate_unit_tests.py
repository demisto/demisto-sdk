import logging
import os
import astor
from demisto_sdk.commands.common.tools import print_error, arg_to_list, print_success
from klara.contract.__main__ import run
from klara.contract import solver
from .test_case_builder import TestCase, ArgsBuilder
from .test_module_builder import TestModule
from klara.contract.solver import MANAGER, ContractSolver, nodes


class UnitTestsGenerator:
    def __init__(self, input_path: str = '', test_data_path: str = '', commands: list[str] = [], output_dir: str = '',
                 verbose: bool = False, module_name: str = ''):
        self.input_path = input_path
        self.test_data_path = test_data_path
        self.commands = commands
        self.verbose = verbose
        self.output_dir = output_dir
        self.module_name = module_name

    def get_input_file(self):
        if os.path.isfile(self.input_path):
            with open(self.input_path, 'r') as input_file:
                return input_file.read()
        else:
            print_error('failed to open input file')

    def decision_maker(self, command_name):
        """
        Returns true if unit test should be generated to a command, false otherwise
        """
        return len(self.commands) == 0 or command_name in self.commands


class CustomContactSolver(ContractSolver):
    def __init__(self, cfg, as_tree, file_name):
        super().__init__(cfg, as_tree, file_name)

    def solve_function(self, func: nodes.FunctionDef, client_ast, directory_path) -> TestCase:
        with MANAGER.initialize_z3_var_from_func(func):
            self.context.no_cache = True
            self.pre_conditions(func)
            test_case = TestCase(func=func, directory_path=directory_path, client_ast=client_ast, id=self.id)

            # Compose args mock
            arg_builder = ArgsBuilder(command_name=func.name, directory_path=directory_path,
                                      args_list=test_case.args_list)
            args = arg_builder.args
            decorator = arg_builder.decorators
            global_args = arg_builder.global_arg

            # Compose request_mock calls for each API call made
            test_case.request_mock_ast_builder()

            # Compose a call to the command
            test_case.call_command_ast_builder()

            # Compose command results assertions
            test_case.create_command_results_assertions()

            # Compose test case object
            test_case.inputs = args
            test_case.decorators = decorator
            test_case.global_arg = global_args


            self.id += 1
            self.context.no_cache = False
            return test_case

    def solve(self, generator: UnitTestsGenerator) -> TestModule:
        test_module = TestModule(module_name=generator.module_name, tree=self.as_tree)
        self.visit(self.as_tree)
        client_ast = test_module.get_client_ast()
        names_to_import = [client_ast.name]
        for func in self.functions:
            if not str(func.name).endswith("_command") or not generator.decision_maker(str(func.name)):
                continue
            if generator.verbose:
                print(f"Analyzing function: {func} at line: {getattr(func, 'lineno', -1)}")
            try:
                ast_func = self.solve_function(func, client_ast, generator.test_data_path)
                test_module.functions.append(ast_func)
                names_to_import.append(func.name)
                if ast_func.global_arg:
                    test_module.global_args.extend(ast_func.global_arg)
            except ValueError:
                if generator.verbose:
                    print(f"Skipped function: {func} due to one of its argument doesn't have type")
            MANAGER.clear_z3_cache()
        test_module.imports.append(test_module.build_imports(names_to_import))
        return test_module


def run_generate_unit_tests(**kwargs):
    input_path = kwargs.get('input_path', '')
    test_data_path = kwargs.get('test_data_path', '')
    output_dir = kwargs.get('output_dir', '')
    commands = arg_to_list(kwargs.get('commands', ''))
    verbose = kwargs.get('verbose', False)

    # validate inputs
    if not input_path:
        print_error(
            'To use the generate_unit_tests version of this command please include an `input` argument')
        return 1

    if input_path and not os.path.isfile(input_path):
        print_error(F'Input file {input_path} was not found.')
        return 1

    if not input_path.lower().endswith('.py'):
        print_error(F'Input {input_path} is not a valid python file.')
        return 1

    module_name = os.path.basename(input_path)

    if not test_data_path:
        dirname = os.path.dirname(input_path)
        test_data_path = os.path.join(f'{dirname}/', "test_data")
        if not os.path.isdir(test_data_path):
            print_error(
                'There is no test_data folder in the working directory, please insert test data directory path.')
            return 1

    if not output_dir:
        output_dir = os.path.dirname(input_path)

    # Check the directory exists and if not, try to create it
    if not os.path.exists(output_dir):
        try:
            os.mkdir(output_dir)
        except Exception as err:
            print_error(f'Error creating directory {output_dir} - {err}')
            return 1
    if not os.path.isdir(output_dir):
        print_error(f'The directory provided "{output_dir}" is not a directory')
        return 1
    file_name = module_name.split('.')[0]
    generator = UnitTestsGenerator(input_path, test_data_path, commands, output_dir, verbose, file_name)
    source = generator.get_input_file()
    if source:
        output_test = run(source, generator)
        output_file = os.path.join(output_dir, f"{file_name}_test.py")
        print(f"Converting inferred test case to ast and write to file: {output_file}")
        with open(output_file, "w") as f:
            f.write(output_test)
        print_success(f'Successfully finished generating integration code and saved it in {output_dir}')

    return 0


def run(source, generator):
    tree = MANAGER.build_tree(ast_str=source)
    cfg = MANAGER.build_cfg(tree)
    cs = CustomContactSolver(cfg, tree, "test")
    module = cs.solve(generator)
    output_test = astor.to_source(module.to_ast())
    return output_test


# ----------------- Monkey Patching----------------------------------------

solver.TestCase = TestCase
solver.TestModule = TestModule
