import ast as ast_mod

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.generate_unit_tests.common import ast_name


class TestModule:
    def __init__(
        self,
        tree: ast_mod.Module,
        module_name: str,
        to_concat: bool,
        module: ast_mod.Module = None,
    ):
        self.functions = []
        self.imports = [
            ast_mod.Import(names=[ast_mod.alias(name="pytest", asname=None)]),
            ast_mod.Import(names=[ast_mod.alias(name="io", asname=None)]),
            ast_mod.ImportFrom(
                module="CommonServerPython",
                names=[ast_mod.alias(name="*", asname=None)],
                level=0,
            ),
        ]
        self.module = module
        self.server_url = ast_mod.Assign(
            targets=[ast_name("SERVER_URL")],
            value=ast_mod.Constant(value="https://test_url.com"),
        )
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
        io_open = ast_mod.Call(
            func=ast_mod.Attribute(value=ast_name("io"), attr=ast_name("open")),
            args=[ast_name("path")],
            keywords=[
                ast_mod.keyword(arg="mode", value=ast_mod.Constant(value="r")),
                ast_mod.keyword(arg="encoding", value=ast_mod.Constant(value="utf-8")),
            ],
        )
        f_read = ast_mod.Call(
            ast_mod.Attribute(value=ast_name("f"), attr=ast_name("read")),
            args=[],
            keywords=[],
        )
        return_node = ast_mod.Return(
            value=ast_mod.Call(
                func=ast_mod.Attribute(value=ast_name("json"), attr=ast_name("loads")),
                args=[f_read],
                keywords=[],
            )
        )
        body = [
            ast_mod.With(
                items=[
                    ast_mod.withitem(context_expr=io_open, optional_vars=ast_name("f"))
                ],
                body=[ast_mod.Expr(value=return_node)],
            )
        ]

        func = ast_mod.FunctionDef(
            name="util_load_json",
            args=ast_mod.arguments(
                posonlyargs=[],
                args=[ast_name("path")],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )
        return func

    def generate_test_client(self):
        """
        Return: client function to mock
        """
        client_init_args = self.get_client_init_args(self.get_client_ast())
        keywords = []
        for arg in client_init_args:
            arg_name = arg.arg
            arg_annotation = str(arg.annotation) if hasattr(arg, "annotation") else None
            if "url" in arg_name:
                keywords.append(
                    ast_mod.keyword(arg=arg_name, value=ast_name("SERVER_URL"))
                )
            elif arg_annotation and arg_annotation == "bool":
                keywords.append(ast_mod.keyword(arg=arg_name, value=ast_name("True")))
            elif arg_annotation and arg_annotation == "str":
                keywords.append(
                    ast_mod.keyword(arg=arg_name, value=ast_mod.Constant("test"))
                )
            elif arg_name != "self":
                keywords.append(ast_mod.keyword(arg=arg_name, value=ast_name("None")))
        body = [
            ast_mod.Return(
                value=ast_mod.Call(func=ast_name("Client"), args=[], keywords=keywords)
            )
        ]

        func = ast_mod.FunctionDef(
            name="client",
            args=ast_mod.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=body,
            decorator_list=[
                ast_mod.Call(
                    func=ast_mod.Attribute(value=ast_name("pytest"), attr="fixture"),
                    args=[],
                    keywords=[],
                )
            ],
            returns=None,
        )
        return func

    def get_client_ast(self):
        """
        Args: Ast tree of the input code.
        Return: Sub ast tree of the client class.
        """
        for body_node in self.tree.body:
            if hasattr(body_node, "bases"):
                bases = [str(id) for id in body_node.bases]
                if "BaseClient" in bases:
                    return body_node
        return None

    @staticmethod
    def get_client_init_args(client_ast: ast_mod.ClassDef):
        for statement in client_ast.body:
            if "name" in statement._fields and statement.name == "__init__":
                return statement.args.args
        logger.debug("No init function was found in Client class.")
        return None

    def build_imports(self, names_to_import: list):
        aliases = [ast_name(name) for name in names_to_import]
        return ast_mod.ImportFrom(module=self.module_name, names=aliases, level=0)
