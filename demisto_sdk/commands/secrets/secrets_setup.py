import sys
from pathlib import Path
import typer

from demisto_sdk.commands.common.configuration import sdk
from demisto_sdk.utils.utils import update_command_args_from_config_file


def secrets(
        ctx: typer.Context,
        input: str = typer.Option(None, help="Specify file to check secret on."),
        post_commit: bool = typer.Option(
            False,
            help="Whether the secrets check is done after committing files.",
        ),
        ignore_entropy: bool = typer.Option(
            False,
            help="Ignore entropy algorithm that finds secret strings (passwords/api keys).",
        ),
        whitelist: Path = typer.Option(
            Path("./Tests/secrets_white_list.json"),
            help='Full path to whitelist file, should be "secrets_white_list.json".',
        ),
        prev_ver: str = typer.Option(None, help="Branch to run secrets validation against."),
        file_paths: list[Path] = typer.Argument(None, help="File paths to check for secrets."),
):
    """Run Secrets validator to catch sensitive data before exposing your code to a public repository."""

    from demisto_sdk.commands.secrets.secrets import SecretsValidator

    # Update command args from config
    update_command_args_from_config_file("secrets", {
        "input": input,
        "post_commit": post_commit,
        "ignore_entropy": ignore_entropy,
        "whitelist": str(whitelist),
        "prev_ver": prev_ver,
        "file_paths": [str(p) for p in file_paths],
    })

    sys.path.append(sdk.configuration.env_dir)
    secrets_validator = SecretsValidator(
        configuration=sdk.configuration,
        is_circle=post_commit,
        ignore_entropy=ignore_entropy,
        white_list_path=str(whitelist),
        input_path=input,
    )
    return secrets_validator.run()
