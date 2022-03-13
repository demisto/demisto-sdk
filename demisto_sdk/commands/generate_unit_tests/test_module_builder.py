import ast as ast_mod
from .klara_extension import ast_name
from demisto_sdk.commands.generate_docs.generate_integration_doc import get_command_examples


def create_command_arg_mock_dictionary(commands_examples_input, specific_commands):
    command_examples = get_command_examples(commands_examples_input, specific_commands)
    commands_args_dict = {}
    for command in command_examples:
        command_line = command.split(' ')
        command_dict = {}
        for arg in command_line[1:]:
            key = arg.split['='][0]
            value = arg.split['='][1]
            command_dict.update(key, value)
        commands_args_dict.update(command_line[0], )
    return commands_args_dict

class TestModule:
    def __init__(self, tree, module_name, to_concat, module=None):
        self.functions = []
        self.imports = [ast_mod.Import(names=[ast_mod.alias(name='pytest')]),
                        ast_mod.Import(names=[ast_mod.alias(name='io')]),
                        ast_mod.ImportFrom(module='CommonServerPython', names=[ast_mod.alias(name='*')], level=0)]
        self.module = module
        self.server_url = ast_mod.Assign(targets=[ast_name('SERVER_URL')],
                                         value=ast_mod.Constant(value='https://test_url.com'))
        self.tree = tree
        self.module_name = module_name
        self.global_args = []
        self.to_concat = to_concat

    def to_ast(self):
        body = []
        if not self.to_concat:
            body.extend(self.imports)
            body.append(self.server_url)
            body.extend([self.util_json_builder(), self.generate_test_client()])
        body.extend(self.global_args)
        body.extend([f.to_ast() for f in self.functions])
        return ast_mod.Module(body=body)

    def util_json_builder(self):
        """
        Return: ast sub-tree of a function to read and parse json file:
        with io.open(path, mode='r', encoding='utf-8') as f:
            return json.loads(f.read())
        """
        io_open = ast_mod.Call(func=ast_mod.Attribute(value=ast_name('io'), attr=ast_name('open')),
                               args=[ast_name('path')],
                               keywords=[ast_mod.keyword(arg='mode', value=ast_mod.Constant(value='r')),
                                         ast_mod.keyword(arg='encoding', value=ast_mod.Constant(value='utf-8'))])
        f_read = ast_mod.Call(ast_mod.Attribute(value=ast_name('f'), attr=ast_name('read')), args=[], keywords=[])
        return_node = ast_mod.Return(
            value=ast_mod.Call(func=ast_mod.Attribute(value=ast_name('json'), attr=ast_name('loads')),
                               args=[f_read],
                               keywords=[]))
        body = [
            ast_mod.With(
                items=[ast_mod.withitem(context_expr=io_open, optional_vars=ast_name('f'))],
                body=[ast_mod.Expr(value=return_node)])
        ]

        func = ast_mod.FunctionDef(
            name="util_load_json",
            args=ast_mod.arguments(
                posonlyargs=[], args=[ast_name('path')], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None,
                defaults=[]
            ),
            body=body,
            decorator_list=[],
            returns=None
        )
        return func

    def generate_test_client(self):
        """
            Return: client function to mock
        """
        body = [
            ast_mod.Return(value=ast_mod.Call(func=ast_name('Client'),
                                              args=[],
                                              keywords=[ast_mod.keyword(arg='base_url', value=ast_name('SERVER_URL'))]))
        ]

        func = ast_mod.FunctionDef(
            name="client",
            args=ast_mod.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
            ),
            body=body,
            decorator_list=[ast_mod.Call(func=ast_mod.Attribute(value=ast_name('pytest'), attr='fixture'),
                                         args=[],
                                         keywords=[])],
            returns=None
        )
        return func

    def get_client_ast(self):
        """
        Args: Ast tree of the input code.
        Return: Sub ast tree of the client class.
        """
        for body_node in self.tree.body:
            if hasattr(body_node, 'bases'):
                bases = [str(id) for id in body_node.bases]
                if 'BaseClient' in bases:
                    return body_node
        return None

    def build_imports(self, names_to_import):
        aliases = [ast_name(name) for name in names_to_import]
        return ast_mod.ImportFrom(module=self.module_name, names=aliases, level=0)
