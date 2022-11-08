import typer
from typing import Optional, List
from pathlib import Path
from rich import print as printr
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import ModelingRule
from demisto_sdk.commands.test_content.test_modeling_rule import init_test_data


app = typer.Typer()


def test_modeling_rules(
        mrule_dirs: List[Path],
        xsiam_url: str, api_key: str, auth_id: str, xsiam_token: str, interactive: bool, ctx: typer.Context):
    printr(f'[cyan]modeling rules directories to test: {mrule_dirs}[/cyan]')
    for mrule_dir in mrule_dirs:
        printr(f'[cyan]Testing modeling rule in: {mrule_dir}[/cyan]')
        mr_entity = ModelingRule(mrule_dir.as_posix())
        if not mr_entity.testdata_path:
            printr(f'[yellow]No test data file found for {mrule_dir}[/yellow]')
            if interactive:
                generate = typer.confirm(f'Would you like to generate a test data file for {mrule_dir}?')
                if generate:
                    printr(f'[cyan]Generating test data file for {mrule_dir}[/cyan]')
                    init_td = app.command()(init_test_data.init_test_data)
                    init_td([mrule_dir], 1)
                    if mr_entity.testdata_path:
                        printr(f'[green]Test data file generated for {mrule_dir}[/green]')
                        printr(f'[cyan]Please complete the test data file at {mr_entity.testdata_path} '
                               'with test event(s) data and expected outputs and then rerun '
                               f'[italic]{ctx.command_path} {mrule_dir}[/italic][/cyan]')
                        typer.Exit()
                    else:
                        printr(f'[red]Failed to generate test data file for {mrule_dir}[/red]')
                        typer.Exit(1)
                else:
                    printr(f'[yellow]Skipping test data file generation for {mrule_dir}[/yellow]')
                    printr(
                        f'[yellow]Please create a test data file for {mrule_dir}'
                        f' and then rerun [italic]{ctx.command_path} {mrule_dir}[/italic][/yellow]'
                    )
                    typer.Abort()
            else:
                printr(f'[yellow]Please create a test data file for {mrule_dir}'
                       f' and then rerun [italic]{ctx.command_path} {mrule_dir}[/italic][/yellow]')
        else:
            printr(f'[cyan]Test data found: Commence testing modeling rule: {mrule_dir}[/cyan]')
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
    ctx: typer.Context,
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
    ),
    interactive: bool = typer.Option(
        True,
        '--interactive/--non-interactive', '-i/-ni',
        help=('Interactive mode, will prompt the user if they want to generate test '
              'data templates if none exists for the passed modeling rules.'),
        rich_help_panel='Interactive Configuration',
        hidden=True
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
        xsiam_url, api_key,  # type: ignore[arg-type] since if they are not set to str values an error occurs
        auth_id, xsiam_token,  # type: ignore[arg-type] since if they are not set to str values an error occurs
        interactive, ctx
    )


if __name__ == '__main__':
    app()
