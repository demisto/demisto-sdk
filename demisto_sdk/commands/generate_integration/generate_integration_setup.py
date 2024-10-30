import typer
import json
from pathlib import Path
from demisto_sdk.commands.generate_integration.code_generator import IntegrationGeneratorConfig

generate_integration_app = typer.Typer()


@generate_integration_app.command(
    help="Generates a Cortex XSOAR integration from a config JSON file produced by commands like "
         "postman-codegen and openapi-codegen."
)
def generate_integration(
        input: Path = typer.Option(..., "-i", "--input",
                                   help="Config JSON file path from postman-codegen or openapi-codegen"),
        output: Path = typer.Option(Path("."), "-o", "--output", help="Directory to save the integration package"),
):
    # Open and load the JSON config file
    with input.open("r") as file:
        config_dict = json.load(file)

    # Initialize the integration generator config
    config = IntegrationGeneratorConfig(**config_dict)

    # Generate the integration package
    config.generate_integration_package(output, True)
