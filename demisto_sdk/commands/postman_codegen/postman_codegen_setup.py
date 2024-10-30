from pathlib import Path
import json
import typer

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.postman_codegen.postman_codegen import postman_to_autogen_configuration
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.config import get_config

postman_codegen_app = typer.Typer()


@postman_codegen_app.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    help="""Generates a Cortex XSOAR integration given a Postman collection 2.1 JSON file."""
)
def postman_codegen(
    input: Path = typer.Option(..., help="The Postman collection 2.1 JSON file"),
    output: Path = typer.Option(Path("."), help="The output directory to save the config file or the integration"),
    name: str = typer.Option(None, help="The output integration name"),
    output_prefix: str = typer.Option(None, help="The global integration output prefix. By default it is the product name."),
    command_prefix: str = typer.Option(None, help="The prefix for each command in the integration. By default is the product name in lower case"),
    config_out: bool = typer.Option(False, help="Used for advanced integration customization. Generates a config JSON file instead of integration."),
    package: bool = typer.Option(False, help="Generated integration will be split to package format instead of a YML file.")
):
    config = get_config()
    postman_config = postman_to_autogen_configuration(
        collection=json.load(open(input)),  # Open the file directly
        name=name,
        command_prefix=command_prefix,
        context_path_prefix=output_prefix,
    )

    if config_out:
        path = Path(output) / f"config-{postman_config.name}.json"
        path.write_text(json.dumps(postman_config.to_dict(), indent=4))
        typer.echo(f"Config file generated at:\n{str(path.absolute())}")
    else:
        # Generate integration YML
        yml_path = postman_config.generate_integration_package(output, is_unified=True)
        if package:
            yml_splitter = YmlSplitter(
                configuration=config.configuration,
                file_type=FileType.INTEGRATION,
                input=str(yml_path),
                output=str(output),
            )
            yml_splitter.extract_to_package_format()
            typer.echo(f"<green>Package generated at {str(Path(output).absolute())} successfully</green>")
        else:
            typer.echo(f"<green>Integration generated at {str(yml_path.absolute())} successfully</green>")


if __name__ == "__main__":
    postman_codegen_app()
