import typer
from typing import Optional, List
from pathlib import Path


app = typer.Typer()


def test_modeling_rules(mrule_dirs: List[Path],
                        xsiam_url: str, api_key: str, auth_id: str, xsiam_token: str):
    ...


# ====================== test-modeling-rule ====================== #


def tenant_config_cb(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]):
    if ctx.resilient_parsing:
        return
    if param.value_is_missing(value):
        err_str = (f'{param.name} must be set either via the environment variable '
                   f'"{param.envvar}" or passed explicitly when running the command')
        raise typer.BadParameter(err_str)
    return value


@app.command(no_args_is_help=True)
def test_modeling_rule(
    input: List[Path] = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help='The path to a directory of a modeling rule. May pass multiple paths to test multiple modeling rules.'
    ),
    xsiam_url: Optional[str] = typer.Option(
        None,
        envvar='DEMISTO_BASE_URL',
        help='The base url to the xsiam tenant.',
        rich_help_panel='XSIAM Tenant Configuration',
        show_default=False,
        callback=tenant_config_cb
    ),
    api_key: Optional[str] = typer.Option(
        None,
        envvar='DEMISTO_API_KEY',
        help='The api key for the xsiam tenant.',
        rich_help_panel='XSIAM Tenant Configuration',
        show_default=False,
        callback=tenant_config_cb
    ),
    auth_id: Optional[str] = typer.Option(
        None,
        envvar='XSIAM_AUTH_ID',
        help='The auth id associated with the xsiam api key being used.',
        rich_help_panel='XSIAM Tenant Configuration',
        show_default=False,
        callback=tenant_config_cb
    ),
    xsiam_token: Optional[str] = typer.Option(
        None,
        envvar='XSIAM_TOKEN',
        help='The token used to push event logs to XSIAM',
        rich_help_panel='XSIAM Tenant Configuration',
        show_default=False,
        callback=tenant_config_cb
    ),
    verbosity: int = typer.Option(
        0,
        '-v', '--verbose',
        count=True,
        clamp=True,
        max=3,
        show_default=True,
        help='Verbosity level -v / -vv / .. / -vvv',
        rich_help_panel='Logging Configuration'
    ),
    quiet: bool = typer.Option(
        True,
        help='Quiet output, only output results in the end.',
        rich_help_panel='Logging Configuration',
    ),
    log_path: Path = typer.Option(
        None,
        '-lp', '--log-path',
        resolve_path=True,
        show_default=False,
        help='Path of directory in which you would like to store all levels of logs.',
        rich_help_panel='Logging Configuration'
    ),
    log_file_name: str = typer.Option(
        'test-modeling-rule.log',
        '-ln', '--log-name',
        resolve_path=True,
        help='The file name (including extension) where log output should be saved to.',
        rich_help_panel='Logging Configuration'
    )
):
    """
    Test a modeling rule against an XSIAM tenant
    """
    from demisto_sdk.commands.common.logger import logging_setup
    logging_setup(
        verbose=verbosity,
        quiet=quiet,
        log_path=log_path,  # type: ignore[arg-type]
        log_file_name=log_file_name
    )
    test_modeling_rules(
        input,
        xsiam_url, api_key, auth_id, xsiam_token  # type: ignore[arg-type] since if they are not set to str values an error occurs
    )


if __name__ == '__main__':
    app()
