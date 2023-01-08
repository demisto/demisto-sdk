import logging
from pathlib import Path
from typing import List

import astor
import autopep8
import click
from klara.contract import solver
from klara.contract.solver import MANAGER, ContractSolver, nodes

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import Colors
from demisto_sdk.commands.common.tools import print_error, print_success
from demisto_sdk.commands.generate_docs.common import execute_command
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    get_command_examples,
)
from demisto_sdk.commands.generate_unit_tests.test_case_builder import (
    ArgsBuilder,
    TestCase,
)
from demisto_sdk.commands.generate_unit_tests.test_module_builder import TestModule

logger = logging.getLogger("demisto-sdk")
json = JSON_Handler()


class UnitTestsGenerator:
    def __init__(
        self,
        input_path: str = "",
        test_data_path: str = "",
        commands: List[str] = [],
        output_dir: str = "",
        module_name: str = "",
        command_examples_input: str = "",
        insecure: bool = False,
        use_demisto: bool = False,
        append: bool = False,
    ):
        self.input_path = input_path
        self.test_data_path = test_data_path
        self.commands = commands
        self.output_dir = output_dir
        self.module_name = module_name
        self.to_concat = append
        self.command_examples_input = command_examples_input
        self.commands_to_generate = {}
        self.errors = []
        self.insecure = insecure
        self.use_demisto = use_demisto
        self.example_dict = {}
        self.command_examples = get_command_examples(
            self.command_examples_input, self.commands
        )
        self.create_command_to_generate_dict()
        if self.use_demisto:
            self.run_commands()

    def get_input_file(self):
        """
        Returns the source code for which the unit tests will be generated.
        """

        with open(self.input_path) as input_file:
            return input_file.read()

    def decision_maker(self, command_name: str):
        """
        Returns true if unit test should be generated to a command, false otherwise
        """
        return len(self.commands) == 0 or command_name in self.commands_to_generate

    @staticmethod
    def command_name_transformer(command_name: str):
        return command_name.strip("!").replace("-", "_") + "_command"

    def execute_commands_into_dict(self):
        """
        gets an array of command examples, run them one by one and return a map of
            {base command -> {readable_outputs:markdown, outputs:context_outputs}}
        Note: if a command appears more then once, run all occurrences but stores only the last.
        """
        examples: dict = {}
        errors: list = []
        for example in self.command_examples:
            name, md_example, context_example, cmd_errors = execute_command(
                example, self.insecure
            )

            context_example = json.dumps(context_example)
            errors.extend(cmd_errors)

            if not cmd_errors:
                name = self.command_name_transformer(name)
                examples[name] = {
                    "readable_output": md_example,
                    "outputs": context_example,
                }
        return examples, errors

    def create_command_to_generate_dict(self):
        """
        Parses command_examples into dictionary of command name and arguments.
        """
        display_commands = []
        for command in self.command_examples:
            command_line = command.split(" ")
            command_name = self.command_name_transformer(command_line[0])
            command_name_without_vendor = command_name.split("_", 1)[1]
            command_dict = {}
            display_commands.append(command_name)
            for arg in command_line[1:]:
                key = arg.split("=")[0]
                value = arg.split("=")[1]
                value = value.replace('"', "")
                command_dict.update({key: value})
            if command_name in self.commands_to_generate:
                self.commands_to_generate.get(command_name).append(command_dict)
            elif command_name_without_vendor in self.commands_to_generate:
                self.commands_to_generate.get(command_name_without_vendor).append(
                    command_dict
                )
            else:
                self.commands_to_generate.update({command_name: [command_dict]})
                self.commands_to_generate.update(
                    {command_name_without_vendor: [command_dict]}
                )

        click.echo("Unit tests will be generated for the following commands:")
        click.echo("\n".join(display_commands))

    def run_commands(self):
        """
        Runs commands using Demisto instance
        """
        global logger
        self.example_dict, build_errors = self.execute_commands_into_dict()
        if build_errors:
            logger.error("Found errors while executing command using demisto:")
            logger.error("\n".join(build_errors))


class CustomContactSolver(ContractSolver):
    def __init__(self, cfg, as_tree):
        """
        Args: cfg: klara cfg object parsed from input file
              as_tree: ast tree representing input code.
        """
        super().__init__(cfg, as_tree, "")

    def solve_function(
        self,
        func: nodes.FunctionDef,
        client_ast: nodes.ClassDef,
        generator: UnitTestsGenerator,
    ) -> TestCase:
        """
        Args: func: ast_node of the function analayzed.
              client_ast: ast sub-tree of the client class.
              generator: UnitTestsGenerator object.
        Returns: TestCase object to parse into unit test.
        """
        with MANAGER.initialize_z3_var_from_func(func):
            self.context.no_cache = True
            self.pre_conditions(func)
            directory_path = generator.test_data_path
            example_dict = generator.example_dict.get(str(func.name))
            commands_to_generate = generator.commands_to_generate
            use_demisto = generator.use_demisto and example_dict is not None

            test_case = TestCase(
                func=func,
                directory_path=directory_path,
                client_ast=client_ast,
                example_dict=example_dict,
                id=self.id,
            )

            # Compose args mock
            logger.debug("Composing mocked arguments.")
            arg_builder = ArgsBuilder(
                command_name=func.name,
                directory_path=directory_path,
                args_list=test_case.args_list,
                commands_to_generate=commands_to_generate,
            )
            args = arg_builder.args
            decorator = arg_builder.decorators
            global_args = arg_builder.global_arg

            # Compose request_mock calls for each API call made and CommandResults mock
            logger.debug("Composing request mock object.")
            test_case.request_mock_ast_builder()
            if use_demisto:
                test_case.build_json_file_mocked_command_results()

            # Compose a call to the command
            logger.debug("Composing call to command.")
            test_case.call_command_ast_builder()

            # Compose command results assertions
            logger.debug("Composing assertions.")
            test_case.create_command_results_assertions()

            # Compose test case object
            test_case.inputs = args
            test_case.decorators = decorator
            test_case.global_arg = global_args

            self.id += 1
            self.context.no_cache = False
            return test_case

    def solve(self, generator: UnitTestsGenerator) -> TestModule:
        """
        Args: generator: UnitTestsGenerator object.
        Returns: TestModule object to parse into tests file.
        """
        global logger
        test_module = TestModule(
            module_name=generator.module_name,
            tree=self.as_tree,
            to_concat=generator.to_concat,
        )
        self.visit(self.as_tree)
        logger.debug("Obtaining client class ast.")
        client_ast = test_module.get_client_ast()
        names_to_import = [client_ast.name]
        for func in self.functions:
            command_name = str(func.name)
            if command_name.endswith("_command"):
                names_to_import.append(func.name)
            if command_name not in generator.commands_to_generate:
                continue
            logger.info(
                f"{Colors.Fg.cyan}Analyzing function: {func} at line: {getattr(func, 'lineno', -1)}{Colors.reset}"
            )
            try:
                ast_func = self.solve_function(func, client_ast, generator)
                logger.info(
                    f"{Colors.Fg.cyan}Finished analyzing function: {func}\n{Colors.reset}"
                )
                test_module.functions.append(ast_func)
                if ast_func.global_arg:
                    test_module.global_args.extend(ast_func.global_arg)
            except Exception as e:
                logger.error(
                    f"{Colors.Fg.red}Skipped function: {func}, error is {e}\n{Colors.reset}"
                )
                raise e
            MANAGER.clear_z3_cache()
        test_module.imports.append(test_module.build_imports(names_to_import))
        return test_module


def run_generate_unit_tests(
    input_path: str,
    commands: list,
    output_dir: str,
    examples: str,
    insecure: bool,
    use_demisto: bool,
    append: bool,
):
    global logger

    click.echo("================= Running Unit Testing Generator ===================")
    # validate inputs
    input_path_obj = Path(input_path)
    if not input_path:
        print_error(
            "To use the generate_unit_tests version of this command please include an `input` argument"
        )
        return 1

    if not input_path_obj.is_file():
        print_error(f"Input file {input_path} was not found.")
        return 1

    if not input_path.lower().endswith(".py"):
        print_error(f"Input {input_path} is not a valid python file.")
        return 1

    module_name = input_path_obj.name

    dirname = input_path_obj.parent
    test_data_path = dirname / "test_data"
    if not test_data_path.is_dir():
        test_data_path.mkdir(parents=True, exist_ok=True)
    outputs_path = test_data_path / "outputs"
    if not outputs_path.is_dir():
        outputs_path.mkdir(parents=True, exist_ok=True)

    if not output_dir:
        output_dir = Path(input_path).parent

    if not examples:
        examples = str(input_path_obj.parent / "command_examples")

    # Check the directory exists and if not, try to create it
    output_dir_path_obj = Path(output_dir)
    if not output_dir_path_obj.exists():
        try:
            output_dir_path_obj.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            print_error(f"Error creating directory {output_dir} - {err}")
            return 1
    if not output_dir_path_obj.is_dir():
        print_error(f'The directory provided "{output_dir}" is not a directory')
        return 1

    file_name = module_name.split(".")[0]
    output_file = Path(output_dir, f"{file_name}_test.py")
    append = append and output_file.exists()
    generator = UnitTestsGenerator(
        input_path,
        test_data_path,
        commands,
        output_dir,
        file_name,
        examples,
        insecure,
        use_demisto,
        append,
    )

    logger.debug(
        f"Created generator object with the following params: input - {input_path},"
        f" test data path - {test_data_path},"
        f" commands -  {commands},"
        f" module_name - {file_name},"
        f" output_dir - {output_dir},"
        f" commands_examples - {examples},"
        f" insecure - {insecure},"
        f" use_demisto - {use_demisto},"
        f" append - {append}"
    )

    source = generator.get_input_file()
    if source:
        try:
            write_mode = "a" if generator.to_concat else "w"
            options = autopep8.parse_args(["--max-line-length", "100000", "-"])
            output_test = autopep8.fix_code(run(source, generator), options)
            if generator.to_concat:
                output_test = "\n" * 2 + output_test
            logger.debug(f"Writing to file: {output_file}")
            with open(output_file, write_mode) as f:
                f.write(output_test)

            print_success(
                f"Successfully finished generating integration code and saved it in {output_dir}"
            )
        except Exception as e:
            print_error(f'An error occurred: {e.args if hasattr(e, "args") else e}')
            return 1
    else:
        print_error("No source code was detected.")
        return 1
    return 0


def run(source: str, generator: UnitTestsGenerator):
    global logger
    logger.info(
        f"\n{Colors.Fg.green}Running code parser and testing generator.{Colors.reset}"
    )
    logger.debug("Starting parsing input code into ast.")
    tree = MANAGER.build_tree(ast_str=source)
    logger.debug("Finished parsing code into ast.")
    cfg = MANAGER.build_cfg(tree)
    cs = CustomContactSolver(cfg, tree)
    logger.info("Running solver for test generating.")
    module = cs.solve(generator)
    logger.info("Finished generating testing asts, parsing to source code.")
    output_test = astor.to_source(module.to_ast())
    logger.info("Finished parsing to code.")
    return output_test


# ----------------- Monkey Patching----------------------------------------

solver.TestCase = TestCase
solver.TestModule = TestModule
