import typer
from typing import Any, Dict, Optional, List, Union
from pathlib import Path
from rich import print as printr
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from time import sleep
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import ModelingRule, MRule
from demisto_sdk.commands.test_content.test_modeling_rule import init_test_data
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_interface import XsiamApiClient, XsiamApiClientConfig
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack


custom_theme = Theme({
    "info": "cyan",
    "info_h1": "cyan underline",
    "warning": "yellow",
    "error": "red",
    "danger": "bold red",
    "success": "green",
    "em": "italic"
})
console = Console()


app = typer.Typer()


ContentEntity = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject]


def create_table(expected: Dict[str, Any], received: Dict[str, Any]) -> Table:
    table = Table('Model Field', 'Expected Value', 'Received Value')
    for key, val in expected.items():
        table.add_row(key, str(val), str(received.get(key)))
    return table


def verify_results(results: List[dict], test_data: init_test_data.TestData):
    if not len(results):
        err = ('[error]No results were returned by the query - it\'s possible there is a syntax'
               ' error with your modeling rule and that it did not install properly on the tenant[/error]')
        printr(err)
        raise typer.Exit(1)
    if len(results) != len(test_data.data):
        raise ValueError(f'Expected {len(test_data.data)} results, got {len(results)}')
    for i, result in enumerate(results):
        printr(f'\n[cyan underline]Result {i + 1}[/cyan underline]')
        # get mapping for the given query result
        td_event_id = result.pop(f'{test_data.data[0].dataset}.test_data_event_id')
        mapping = None
        for e in test_data.expected_values:
            if str(e.test_data_event_id) == td_event_id:
                mapping = e.mapping
                break

        printr(create_table(mapping, result))

        if mapping:
            for key, val in mapping.items():
                if not val:
                    # TODO: Make this a debugging statement
                    printr(f'[cyan]No mapping for {key} - skipping checking match[/cyan]')
                else:
                    printr(f'[cyan]Checking for key {key}:\n - expected: {val}\n - received: {result.get(key)}[/cyan]')
                    assert result.get(key) == val, f'Expected {val} to equal {result.get(key)}'
        else:
            printr(
                f'[red]No matching mapping found for test_data_event_id={td_event_id} in test_data {test_data}[/red]'
            )
            raise typer.Exit(1)


def generate_xql_query(rule: MRule, test_data_event_ids: List[str]) -> str:
    fields = ', '.join([f'{f}' for f in rule.fields])
    td_event_ids = ', '.join([f'"{td_event_id}"' for td_event_id in test_data_event_ids])
    query = f'datamodel dataset in({rule.dataset}) | filter {rule.dataset}.test_data_event_id in({td_event_ids}) | dedup {rule.dataset}.test_data_event_id by desc _insert_time | fields {rule.dataset}.test_data_event_id, {fields}'
    return query


def validate_mappings(xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData):
    with console.status('[info]Validating mappings...[/info]'):
        for rule in mr.rules:
            query = generate_xql_query(rule, [str(d.test_data_event_id) for d in test_data.data])
            console.log(query)
            execution_id = xsiam_client.start_xql_query(query)
            results = xsiam_client.get_xql_query_result(execution_id)
            verify_results(results, test_data)
    console.print('[green]Mappings validated successfully[/green]')


def push_test_data_to_tenant(xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData):
    events_test_data = [e.event_data for e in test_data.data]
    for i, event_log in enumerate(test_data.data):
        if isinstance(event_log.event_data, dict):
            events_test_data[i] = {**event_log.event_data, "test_data_event_id": str(event_log.test_data_event_id)}
    # printr(events_test_data)
    console.print('[info]Pushing test data to tenant...[/info]')
    xsiam_client.add_create_dataset(events_test_data, mr.rules[0].vendor, mr.rules[0].product)
    console.print('[success]Test data pushed successfully[/success]')


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
    printr('[info]Verifying pack installed on tenant[/info]')
    identified_pack = get_containing_pack(mr)
    installed_packs = xsiam_client.installed_packs
    found_pack = None
    for pack in installed_packs:
        if identified_pack.id == pack.get('id'):
            found_pack = pack
            break
    if found_pack:
        printr(f'[info]Found pack on tenant:\n{found_pack}[/info]')
    else:
        printr(f'[error]Pack {identified_pack.id} was not found on tenant[/error]')
        # TODO: add option to interactively install pack
        # upload_result = 0
        # if interactive:
        #     upload = typer.confirm(f'Would you like to upload {identified_pack.id} to the tenant?')
        #     if upload:
        #         printr(f'[info_h1]Upload "{identified_pack.id}"[/info_h1]')
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
        #         printr(f'[info_h1]Upload "{identified_pack.id}"[/info_h1]')
        #         # implement correct invocation of upload command
        #         # upload_result = upload_cmd(zip=True, xsiam=True, input=identified_pack.path)
        #         try:
        #             xsiam_client.upload_packs(identified_pack.path)
        #         except requests.exceptions.HTTPError as err:
        #             printr(f'[error]Failed to upload pack {identified_pack.id} to tenant: {err}[/error]')
        #             upload_result = 1
        # if not interactive or not upload_result == 0:
        printr('[error]Please install or upload the pack to the tenant and try again[/error]')
        cmd_group = Group(
            Syntax(f'demisto-sdk upload -z -x -i {identified_pack.path}', "bash"),
            Syntax(f'demisto-sdk modeling-rules test {mr.path.parent}', "bash")
        )
        printr(Panel(cmd_group))
        raise typer.Exit(1)


def test_rule(mr: ModelingRule, xsiam_url: str, api_key: str, auth_id: str, xsiam_token: str, interactive: bool):
    # initialize xsiam client
    xsiam_client_cfg = XsiamApiClientConfig(
        xsiam_url=xsiam_url, api_key=api_key, auth_id=auth_id, xsiam_token=xsiam_token
    )
    xsiam_client = XsiamApiClient(xsiam_client_cfg)
    verify_pack_exists_on_tenant(xsiam_client, mr, interactive)
    test_data = init_test_data.TestData.parse_file(mr.testdata_path.as_posix())
    push_test_data_to_tenant(xsiam_client, mr, test_data)
    sleep(5)
    validate_mappings(xsiam_client, mr, test_data)


def check_test_data_event_data_exists(test_data_path: Path) -> List[str]:
    missing_event_data = []
    test_data = init_test_data.TestData.parse_file(test_data_path)
    for event_log in test_data.data:
        if not event_log.event_data:
            missing_event_data.append(event_log.test_data_event_id)
    return missing_event_data


def validate_modeling_rule(
        mrule_dir: Path,
        xsiam_url: str, api_key: str, auth_id: str, xsiam_token: str, interactive: bool, ctx: typer.Context
):
    console.rule("[info]Test Modeling Rule[/info]")
    printr(f'[info]<<<< {mrule_dir} >>>>[/info]')
    mr_entity = ModelingRule(mrule_dir.as_posix())
    execd_cmd = Panel(Syntax(f'{ctx.command_path} {mrule_dir}', "bash"))
    if not mr_entity.testdata_path:
        printr(f'[warning]No test data file found for {mrule_dir}[/warning]')
        if interactive:
            generate = typer.confirm(f'Would you like to generate a test data file for {mrule_dir}?')
            if generate:
                printr('[info_h1]Generate Test Data File[/info_h1]')
                init_td = app.command()(init_test_data.init_test_data)
                events_count = typer.prompt(
                    'For how many events would you like to generate templates?', type=int, default=1, show_default=True
                )
                init_td([mrule_dir], events_count)
                if mr_entity.testdata_path:
                    printr(f'[success]Test data file generated for {mrule_dir}[/success]')
                    printr(f'[info]Please complete the test data file at {mr_entity.testdata_path} '
                           'with test event(s) data and expected outputs and then rerun,')
                    printr(execd_cmd)
                    raise typer.Exit()
                else:
                    printr(f'[error]Failed to generate test data file for {mrule_dir}[/error]')
                    raise typer.Exit(1)
            else:
                printr(f'[warning]Skipping test data file generation for {mrule_dir}[/warning]')
                printr(f'[warning]Please create a test data file for {mrule_dir} and then rerun,[/warning]')
                printr(execd_cmd)
                raise typer.Abort()
        else:
            printr(f'[warning]Please create a test data file for {mrule_dir} and then rerun,[/warning]')
            printr(execd_cmd)
    else:
        printr(f'[info]Test data file found at {mr_entity.testdata_path}[/info]')
        printr('[info]Checking that event data was added to the test data file[/info]')
        missing_event_data = check_test_data_event_data_exists(mr_entity.testdata_path)
        if missing_event_data:
            printr('[warning]Event log test data is missing for the following ids:[/warning]')
            for test_data_event_id in missing_event_data:
                printr(f'[warning] - {test_data_event_id}[/warning]')
            printr(f'[info]Please complete the test data file at {mr_entity.testdata_path} '
                   'with test event(s) data and expected outputs and then rerun,')
            printr(execd_cmd)
            raise typer.Exit(1)
        test_rule(mr_entity, xsiam_url, api_key, auth_id, xsiam_token, interactive)


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
    printr(f'[cyan]modeling rules directories to test: {input}[/cyan]')
    for mrule_dir in input:
        validate_modeling_rule(
            mrule_dir,
            xsiam_url, api_key,  # type: ignore[arg-type] since if they are not set to str values an error occurs
            auth_id, xsiam_token,  # type: ignore[arg-type] since if they are not set to str values an error occurs
            interactive, ctx
        )


if __name__ == '__main__':
    app()
