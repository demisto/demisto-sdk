import ast as ast_mod
import json
from typing import Union


def ast_name(id: str, ctx: Union[ast_mod.Load, ast_mod.Store, ast_mod.Del] = ast_mod.Load()):
    """
    Creates an ast Name node.
    """
    return ast_mod.Name(id=id, ctx=ctx)


def extract_outputs_from_command_run(context_example, output_prefix):
    splited_prefix = output_prefix.split('.')
    context_example = json.loads(context_example)
    for prefix in splited_prefix:
        context_example = context_example.get(prefix)
    return context_example
