import ast
import importlib.util


class DecoratorsStuff:
    def __init__(self):
        self.docs = []
        self.commands = []
        self.collect_data = False

    def set_collect_data(self, value):
        self.collect_data = value

    @staticmethod
    def empty_decorator(func):
        return func

    def add_command_wrapper(self, func):
        def get_out_info():
            self.docs.append(func.__doc__)
        return get_out_info

    def add_command(self, command_name=None):
        if self.collect_data:
            self.commands.append(command_name)
            return self.add_command_wrapper
        else:
            return self.empty_decorator


class YMLGenerator:
    def __init__(self, filename):
        self.functions = []
        self.filename = filename
        self.decorators = None
        self.import_decorators_obj()

    def import_decorators_obj(self):
        spec = importlib.util.spec_from_file_location(self.filename)
        decorators = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(decorators)
        self.decorators = decorators

    def generate(self):
        self.collect_functions()
        self.decorators.set_collect_data(True)
        self.run_functions()
        print(f"{self.decorators.docs}")
        print(f"{self.decorators.commands}")
        self.decorators.set_collect_data(False)

    def collect_functions(self):
        with open(self.filename) as file:
            node = ast.parse(file.read())

        self.functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        print(f"functions found: {self.functions}")

    def run_functions(self):
        for function in self.functions:
            function()


yml_generator = YMLGenerator(filename='example_integration.py')
