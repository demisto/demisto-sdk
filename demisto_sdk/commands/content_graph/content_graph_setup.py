import typer

from demisto_sdk.commands.content_graph.commands.create import create
from demisto_sdk.commands.content_graph.commands.get_dependencies import (
    get_dependencies,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    get_relationships,
)
from demisto_sdk.commands.content_graph.commands.update import update

graph_cmd_group = typer.Typer(
    name="graph",
    hidden=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
graph_cmd_group.command("create", no_args_is_help=False)(create)
graph_cmd_group.command("update", no_args_is_help=False)(update)
graph_cmd_group.command("get-relationships", no_args_is_help=True)(get_relationships)
graph_cmd_group.command("get-dependencies", no_args_is_help=True)(get_dependencies)

if __name__ == "__main__":
    graph_cmd_group()
