import logging
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple, Union

import typer
from rich import print as printr
from rich.console import Console, Group
from rich.logging import RichHandler
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
    ModelingRule, MRule)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.test_content.test_modeling_rule import init_test_data
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_interface import (
    XsiamApiClient, XsiamApiClientConfig)


logger = logging.getLogger('demisto-sdk')


custom_theme = Theme({
    "info": "cyan",
    "info_h1": "cyan underline",
    "warning": "yellow",
    "error": "red",
    "danger": "bold red",
    "success": "green",
    "em": "italic"
})
console = Console(theme=custom_theme)


app = typer.Typer()


ContentEntity = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject]


def create_table(expected: Dict[str, Any], received: Dict[str, Any]) -> Table:
    """Create a table to display the expected and received values.

    Args:
        expected (Dict[str, Any]): mapping of keys to expected values
        received (Dict[str, Any]): mapping of keys to received values

    Returns:
        Table: Table object to display the expected and received values.
    """
    table = Table('Model Field', 'Expected Value', 'Received Value')
    for key, val in expected.items():
        table.add_row(key, str(val), str(received.get(key)))
    return table


def verify_results(results: List[dict], test_data: init_test_data.TestData):
    """Verify that the results of the XQL query match the expected values.

    Args:
        results (List[dict]): The results of the XQL query.
        test_data (init_test_data.TestData): The data parsed from the test data file.

    Raises:
        typer.Exit: If there are no results.
        ValueError: If the number of results does not match the number of test data events.
        typer.Exit: If the results do not match the expected values.
    """
    if not len(results):
        err = ('[red]No results were returned by the query - it\'s possible there is a syntax'
               ' error with your modeling rule and that it did not install properly on the tenant[/red]')
        logger.error(err, extra={'markup': True})
        raise typer.Exit(1)
    if len(results) != len(test_data.data):
        raise ValueError(f'Expected {len(test_data.data)} results, got {len(results)}')
    errors = False
    for i, result in enumerate(results):
        logger.info(f'\n[cyan underline]Result {i + 1}[/cyan underline]', extra={'markup': True})

        # get mapping for the given query result
        td_event_id = result.pop(f'{test_data.data[0].dataset}.test_data_event_id')
        mapping = None
        for e in test_data.data:
            if str(e.test_data_event_id) == td_event_id:
                mapping = e.mapping
                break

        printr(create_table(mapping, result))

        if mapping:
            for key, val in mapping.items():
                if not val:
                    # TODO: Make this a debugging statement
                    logger.debug(
                        f'[cyan]No mapping for {key} - skipping checking match[/cyan]',
                        extra={'markup': True}
                    )
                else:
                    result_val = result.get(key)
                    logger.debug(
                        f'[cyan]Checking for key {key}:\n - expected: {val}\n - received: {result_val}[/cyan]',
                        extra={'markup': True}
                    )
                    if result_val != val:
                        logger.error(
                            f'[red][bold]{key}[/bold] --- "{result_val}" != "{val}"[/red]',
                            extra={'markup': True}
                        )
                        errors = True
        else:
            logger.error(
                f'[red]No matching mapping found for test_data_event_id={td_event_id} in test_data {test_data}[/red]',
                extra={'markup': True}
            )
            errors = True
    if errors:
        raise typer.Exit(1)


def generate_xql_query(rule: MRule, test_data_event_ids: List[str]) -> str:
    """Generate an XQL query from the given rule and test data event IDs.

    Args:
        rule (MRule): Rule object parsed from the modeling rule file.
        test_data_event_ids (List[str]): List of test data event IDs to query.

    Returns:
        str: The XQL query.
    """
    fields = ', '.join([f'{f}' for f in rule.fields])
    td_event_ids = ', '.join([f'"{td_event_id}"' for td_event_id in test_data_event_ids])
    query = (f'datamodel dataset in({rule.dataset}) | filter {rule.dataset}.test_data_event_id in({td_event_ids}) '
             f'| dedup {rule.dataset}.test_data_event_id by desc _insert_time | fields '
             f'{rule.dataset}.test_data_event_id, {fields}')
    return query


def validate_mappings(xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData):
    """Validate the mappings in the given test data file."""
    logger.info('[cyan]Validating mappings...[/cyan]', extra={'markup': True})
    for rule in mr.rules:
        query = generate_xql_query(rule, [str(d.test_data_event_id) for d in test_data.data])
        logger.debug(query)
        execution_id = xsiam_client.start_xql_query(query)
        results = xsiam_client.get_xql_query_result(execution_id)
        verify_results(results, test_data)
    logger.info('[green]Mappings validated successfully[/green]', extra={'markup': True})


def push_test_data_to_tenant(xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData):
    """Push the test data to the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        test_data (init_test_data.TestData): Test data object parsed from the test data file.
    """
    events_test_data = [e.event_data for e in test_data.data]
    for i, event_log in enumerate(test_data.data):
        if isinstance(event_log.event_data, dict):
            events_test_data[i] = {**event_log.event_data, "test_data_event_id": str(event_log.test_data_event_id)}
    # printr(events_test_data)
    logger.info('[cyan]Pushing test data to tenant...[/cyan]', extra={'markup': True})
    xsiam_client.add_create_dataset(events_test_data, mr.rules[0].vendor, mr.rules[0].product)
    logger.info('[green]Test data pushed successfully[/green]', extra={'markup': True})


def get_containing_pack(content_entity: ContentEntity) -> Pack:
    """Get pack object that contains the content entity.

    Args:
        content_entity: Content entity object.

    Returns:
        Pack: Pack object that contains the content entity.
    """
    pack_path = content_entity.path
    while pack_path.parent.name != 'Packs':
        pack_path = pack_path.parent
    return Pack(pack_path)


def verify_pack_exists_on_tenant(xsiam_client: XsiamApiClient, mr: ModelingRule, interactive: bool):
    """Verify that the pack containing the modeling rule exists on the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        interactive (bool): Whether command is being run in interactive mode.
    """
    logger.info('[cyan]Verifying pack installed on tenant[/cyan]', extra={'markup': True})
    identified_pack = get_containing_pack(mr)
    installed_packs = xsiam_client.installed_packs
    found_pack = None
    for pack in installed_packs:
        if identified_pack.id == pack.get('id'):
            found_pack = pack
            break
    if found_pack:
        logger.debug(f'[cyan]Found pack on tenant:\n{found_pack}[/cyan]', extra={'markup': True})
    else:
        logger.error(f'[red]Pack {identified_pack.id} was not found on tenant[/red]', extra={'markup': True})
        # TODO: add option to interactively install pack
        # upload_result = 0
        # if interactive:
        #     upload = typer.confirm(f'Would you like to upload {identified_pack.id} to the tenant?')
        #     if upload:
        #         printr(f'[cyan underline]Upload "{identified_pack.id}"[/cyan underline]')
        #         # implement correct invocation of upload command
        #         upload_result = upload_cmd(zip=True, xsiam=True, input=identified_pack.path)
        #         if upload_result != 0:
        #             printr(f'[error]Failed to upload pack {identified_pack.id} to tenant[/error]')
        # if not interactive or not upload_result == 0:
        #     printr('[error]Please install or upload the pack to the tenant and try again[/error]')
        #     cmd_group = Group(
        #         Syntax(f'demisto-sdk upload -z -x -i {identified_pack.path}', "bash"),
        #         Syntax(f'demisto-sdk modeling-rules test {mr.path}', "bash")
        #     )
        #     printr(Panel(cmd_group))
        #     raise typer.Exit(1)
        # ## different way?
        # upload_result = 0
        # if interactive:
        #     upload = typer.confirm(f'Would you like to upload {identified_pack.id} to the tenant?')
        #     if upload:
        #         printr(f'[cyan underline]Upload "{identified_pack.id}"[/cyan underline]')
        #         # implement correct invocation of upload command
        #         # upload_result = upload_cmd(zip=True, xsiam=True, input=identified_pack.path)
        #         try:
        #             xsiam_client.upload_packs(identified_pack.path)
        #         except requests.exceptions.HTTPError as err:
        #             printr(f'[error]Failed to upload pack {identified_pack.id} to tenant: {err}[/error]')
        #             upload_result = 1
        # if not interactive or not upload_result == 0:
        logger.error(
            '[red]Please install or upload the pack to the tenant and try again[/red]',
            extra={'markup': True}
        )
        cmd_group = Group(
            Syntax(f'demisto-sdk upload -z -x -i {identified_pack.path}', "bash"),
            Syntax(f'demisto-sdk modeling-rules test {mr.path.parent}', "bash")
        )
        printr(Panel(cmd_group))
        raise typer.Exit(1)


def verify_test_data_exists(test_data_path: Path) -> Tuple[List[str], List[str]]:
    """Verify that the test data file exists and is valid.

    Args:
        test_data_path (Path): Path to the test data file.

    Returns:
        Tuple[List[str], List[str]]: Tuple of lists where the first list is test event
            ids that do not have example event data, and the second list is test event
            ids that do not have mappings to check.
    """
    missing_event_data, missing_mapping_data = [], []
    test_data = init_test_data.TestData.parse_file(test_data_path)
    for event_log in test_data.data:
        if not event_log.event_data:
            missing_event_data.append(event_log.test_data_event_id)
        if all([val is None for val in event_log.mapping.values()]):
            missing_mapping_data.append(event_log.test_data_event_id)
    return missing_event_data, missing_mapping_data


def validate_modeling_rule(
        mrule_dir: Path,
        xsiam_url: str, api_key: str, auth_id: str, xsiam_token: str,
        push: bool, interactive: bool, ctx: typer.Context
):
    """Validate a modeling rule.

    Args:
        mrule_dir (Path): Path to the modeling rule directory.
        xsiam_url (str): URL of the xsiam tenant.
        api_key (str): xsiam API key.
        auth_id (str): xsiam auth ID.
        xsiam_token (str): xsiam token.
        push (bool): Whether to push test event data to the tenant.
        interactive (bool): Whether command is being run in interactive mode.
        ctx (typer.Context): Typer context.
    """
    console.rule("[info]Test Modeling Rule[/info]")
    logger.info(f'[cyan]<<<< {mrule_dir} >>>>[/cyan]', extra={'markup': True})
    mr_entity = ModelingRule(mrule_dir.as_posix())
    execd_cmd = Panel(Syntax(f'{ctx.command_path} {mrule_dir}', "bash"))
    if not mr_entity.testdata_path:
        logger.warning(f'[warning]No test data file found for {mrule_dir}[/warning]', extra={'markup': True})
        if interactive:
            generate = typer.confirm(f'Would you like to generate a test data file for {mrule_dir}?')
            if generate:
                logger.info('[cyan underline]Generate Test Data File[/cyan underline]', extra={'markup': True})
                init_td = app.command()(init_test_data.init_test_data)
                events_count = typer.prompt(
                    'For how many events would you like to generate templates?', type=int, default=1, show_default=True
                )
                init_td([mrule_dir], events_count)
                if mr_entity.testdata_path:
                    logger.info(
                        f'[green]Test data file generated for {mrule_dir}[/green]',
                        extra={'markup': True}
                    )
                    logger.info(
                        f'[cyan]Please complete the test data file at {mr_entity.testdata_path} '
                        'with test event(s) data and expected outputs and then rerun,[/cyan]',
                        extra={'markup': True}
                    )
                    printr(execd_cmd)
                    raise typer.Exit()
                else:
                    logger.error(
                        f'[error]Failed to generate test data file for {mrule_dir}[/error]',
                        extra={'markup': True}
                    )
                    raise typer.Exit(1)
            else:
                logger.warning(
                    f'[yellow]Skipping test data file generation for {mrule_dir}[/yellow]',
                    extra={'markup': True}
                )
                logger.warning(
                    f'[yellow]Please create a test data file for {mrule_dir} and then rerun,[/yellow]',
                    extra={'markup': True}
                )
                printr(execd_cmd)
                raise typer.Abort()
        else:
            logger.warning(
                f'[yellow]Please create a test data file for {mrule_dir} and then rerun,[/yellow]',
                extra={'markup': True}
            )
            printr(execd_cmd)
    else:
        logger.info(f'[cyan]Test data file found at {mr_entity.testdata_path}[/cyan]', extra={'markup': True})
        logger.info('[cyan]Checking that event data was added to the test data file[/cyan]', extra={'markup': True})
        missing_event_data, _ = verify_test_data_exists(mr_entity.testdata_path)

        # initialize xsiam client
        xsiam_client_cfg = XsiamApiClientConfig(
            xsiam_url=xsiam_url, api_key=api_key, auth_id=auth_id, xsiam_token=xsiam_token
        )
        xsiam_client = XsiamApiClient(xsiam_client_cfg)
        verify_pack_exists_on_tenant(xsiam_client, mr_entity, interactive)
        test_data = init_test_data.TestData.parse_file(mr_entity.testdata_path.as_posix())

        if push:
            if missing_event_data:
                logger.warning(
                    '[yellow]Event log test data is missing for the following ids:[/yellow]',
                    extra={'markup': True}
                )
                for test_data_event_id in missing_event_data:
                    logger.warning(f'[yellow] - {test_data_event_id}[/yellow]', extra={'markup': True})
                logger.warning(
                    f'[yellow]Please complete the test data file at {mr_entity.testdata_path} '
                    'with test event(s) data and expected outputs and then rerun,[/yellow]',
                    extra={'markup': True}
                )
                printr(execd_cmd)
                raise typer.Exit(1)
            push_test_data_to_tenant(xsiam_client, mr_entity, test_data)
            sleep(5)
        else:
            logger.info(
                '[cyan]The command flag "--no-push" was passed - skipping pushing of test data[/cyan]',
                extra={'markup': True}
            )
        validate_mappings(xsiam_client, mr_entity, test_data)


def setup_logging(verbosity: int, quiet: bool, log_path: Path, log_file_name: str):
    """Override the default StreamHandler with the RichHandler.

    Setup logging and then override the default StreamHandler with the RichHandler.

    Args:
        verbosity (int): The log level to output.
        quiet (bool): If True, no logs will be output.
        log_path (Path): Path to the directory where the log file will be created.
        log_file_name (str): The filename of the log file.
    """
    from demisto_sdk.commands.common.logger import logging_setup
    logger = logging_setup(
        verbose=verbosity,
        quiet=quiet,
        log_path=log_path,  # type: ignore[arg-type]
        log_file_name=log_file_name
    )
    console_handler_index = -1
    for i, h in enumerate(logger.handlers):
        if h.name == 'console-handler':
            console_handler_index = i
    if console_handler_index != -1:
        logger.handlers[console_handler_index] = RichHandler(
            rich_tracebacks=True,
        )
    else:
        logger.addHandler(RichHandler(rich_tracebacks=True))


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
        False,
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
    push: bool = typer.Option(
        True,
        '--push/--no-push', '-p/-np',
        help=('In the event that you\'ve already pushed test data and only want to test mappings, you can'
              'pass "--no-push" to skip pushing the test data.'),
        rich_help_panel='Interactive Configuration',
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
    setup_logging(verbosity, quiet, log_path, log_file_name)
        
    logger.info(f'[cyan]modeling rules directories to test: {input}[/cyan]', extra={'markup': True})
    for mrule_dir in input:
        validate_modeling_rule(
            mrule_dir,
            xsiam_url, api_key,  # type: ignore[arg-type] since if they are not set to str values an error occurs
            auth_id, xsiam_token,  # type: ignore[arg-type] since if they are not set to str values an error occurs
            push, interactive, ctx
        )


if __name__ == '__main__':
    app()
