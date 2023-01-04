import logging
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import requests
import typer
from rich import print as printr
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme
from typer.main import get_command_from_info

from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
    ModelingRule,
    SingleModelingRule,
)
from demisto_sdk.commands.common.logger import (
    set_console_stream_handler,
    setup_rich_logging,
)
from demisto_sdk.commands.test_content.test_modeling_rule import init_test_data
from demisto_sdk.commands.test_content.xsiam_tools import xsiam_client
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_client import (
    XsiamApiClient,
    XsiamApiClientConfig,
)
from demisto_sdk.commands.upload.upload import upload_content_entity as upload_cmd
from demisto_sdk.utils.utils import get_containing_pack

custom_theme = Theme(
    {
        "info": "cyan",
        "info_h1": "cyan underline",
        "warning": "yellow",
        "error": "red",
        "danger": "bold red",
        "success": "green",
        "em": "italic",
    }
)
console = Console(theme=custom_theme)


app = typer.Typer()
logger = logging.getLogger("demisto-sdk")


def create_table(expected: Dict[str, Any], received: Dict[str, Any]) -> Table:
    """Create a table to display the expected and received values.

    Args:
        expected (Dict[str, Any]): mapping of keys to expected values
        received (Dict[str, Any]): mapping of keys to received values

    Returns:
        Table: Table object to display the expected and received values.
    """
    table = Table("Model Field", "Expected Value", "Received Value")
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
    if not results:
        err = (
            "[red]No results were returned by the query - it's possible there is a syntax"
            " error with your modeling rule and that it did not install properly on the tenant[/red]"
        )
        logger.error(err, extra={"markup": True})
        raise typer.Exit(1)
    if len(results) != len(test_data.data):
        err = (
            f"[red]Expected {len(test_data.data)} results, got {len(results)}. Verify that the event"
            " data used in your test data file meets the criteria of the modeling rule, e.g. the filter"
            " condition.[/red]"
        )
        logger.error(err, extra={"markup": True})
        raise typer.Exit(1)
    errors = False
    for i, result in enumerate(results):
        logger.info(
            f"\n[cyan underline]Result {i + 1}[/cyan underline]", extra={"markup": True}
        )

        # get expected_values for the given query result
        td_event_id = result.pop(f"{test_data.data[0].dataset}.test_data_event_id")
        expected_values = None
        for e in test_data.data:
            if str(e.test_data_event_id) == td_event_id:
                expected_values = e.expected_values
                break

        if expected_values:
            printr(create_table(expected_values, result))

            for key, val in expected_values.items():
                if not val:
                    logger.debug(
                        f"[cyan]No mapping for {key} - skipping checking match[/cyan]",
                        extra={"markup": True},
                    )
                else:
                    result_val = result.get(key)
                    logger.debug(
                        f"[cyan]Checking for key {key}:\n - expected: {val}\n - received: {result_val}[/cyan]",
                        extra={"markup": True},
                    )
                    if result_val != val:
                        logger.error(
                            f'[red][bold]{key}[/bold] --- "{result_val}" != "{val}"[/red]',
                            extra={"markup": True},
                        )
                        errors = True
        else:
            logger.error(
                (
                    f"[red]No matching expected_values found for test_data_event_id={td_event_id} in "
                    f"test_data {test_data}[/red]"
                ),
                extra={"markup": True},
            )
            errors = True
    if errors:
        raise typer.Exit(1)


def generate_xql_query(rule: SingleModelingRule, test_data_event_ids: List[str]) -> str:
    """Generate an XQL query from the given rule and test data event IDs.

    Args:
        rule (SingleModelingRule): Rule object parsed from the modeling rule file.
        test_data_event_ids (List[str]): List of test data event IDs to query.

    Returns:
        str: The XQL query.
    """
    fields = ", ".join([field for field in rule.fields])
    td_event_ids = ", ".join(
        [f'"{td_event_id}"' for td_event_id in test_data_event_ids]
    )
    query = (
        f"config timeframe = 10y | datamodel dataset in({rule.dataset}) | filter {rule.dataset}.test_data_event_id "
        f"in({td_event_ids}) | dedup {rule.dataset}.test_data_event_id by desc _insert_time | fields "
        f"{rule.dataset}.test_data_event_id, {fields}"
    )
    return query


def validate_expected_values(
    xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData
):
    """Validate the expected_values in the given test data file."""
    logger.info("[cyan]Validating expected_values...[/cyan]", extra={"markup": True})
    success = True
    for rule in mr.rules:
        query = generate_xql_query(
            rule, [str(d.test_data_event_id) for d in test_data.data]
        )
        logger.debug(query)
        try:
            execution_id = xsiam_client.start_xql_query(query)
            results = xsiam_client.get_xql_query_result(execution_id)
        except requests.exceptions.HTTPError:
            logger.error(
                (
                    "[red]Error executing XQL query, potential reasons could be:\n - mismatch between "
                    "dataset/vendor/product marked in the test data from what is in the modeling rule\n"
                    " - dataset was not created in the tenant\n - model fields in the query are invalid\n"
                    "Try manually querying your tenant to discover the exact problem.[/red]"
                ),
                extra={"markup": True},
            )
            success = False
        else:
            verify_results(results, test_data)
    if success:
        logger.info(
            "[green]Mappings validated successfully[/green]", extra={"markup": True}
        )
    else:
        raise typer.Exit(1)


def check_dataset_exists(
    xsiam_client: XsiamApiClient,
    test_data: init_test_data.TestData,
    timeout: int = 60,
    interval: int = 5,
):
    """Check if the dataset in the test data file exists in the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        test_data (init_test_data.TestData): The data parsed from the test data file.
        timeout (int, optional): The number of seconds to wait for the dataset to exist. Defaults to 60.
        interval (int, optional): The number of seconds to wait between checking for the dataset. Defaults to 5.

    Raises:
        typer.Exit: If the dataset does not exist after the timeout.
    """
    dataset = test_data.data[0].dataset
    logger.info(
        f'[cyan]Checking if dataset "{dataset}" exists on the tenant...[/cyan]',
        extra={"markup": True},
    )
    query = f"config timeframe = 10y | dataset = {dataset}"
    for i in range(timeout // interval):
        logger.debug(f"Check #{i+1}...")
        try:
            execution_id = xsiam_client.start_xql_query(query)
            results = xsiam_client.get_xql_query_result(execution_id)
            if results:
                logger.info(
                    f"[green]Dataset {dataset} exists[/green]", extra={"markup": True}
                )
                return
            else:
                err = (
                    f"[red]Dataset {dataset} exists but no results were returned. This could mean that your testdata "
                    "does not meet the criteria for an associated Parsing Rule and is therefore being dropped from "
                    "the dataset. Check to see if a Parsing Rule exists for your dataset and that your testdata "
                    "meets the criteria for that rule.[/red]"
                )
                logger.error(err, extra={"markup": True})
                raise typer.Exit(1)
        except requests.exceptions.HTTPError:
            pass
        sleep(interval)
    logger.error(
        f"[red]Dataset {dataset} does not exist after {timeout} seconds[/red]",
        extra={"markup": True},
    )
    raise typer.Exit(1)


def push_test_data_to_tenant(
    xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData
):
    """Push the test data to the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        test_data (init_test_data.TestData): Test data object parsed from the test data file.
    """
    events_test_data = [
        {
            **event_log.event_data,
            "test_data_event_id": str(event_log.test_data_event_id),
        }
        for event_log in test_data.data
        if isinstance(event_log.event_data, dict)
    ]
    logger.info("[cyan]Pushing test data to tenant...[/cyan]", extra={"markup": True})
    try:
        xsiam_client.push_to_dataset(
            events_test_data, mr.rules[0].vendor, mr.rules[0].product
        )
    except requests.exceptions.HTTPError:
        logger.error(
            (
                "[red]Failed pushing test data to tenant, potential reasons could be:\n - an incorrect token\n"
                ' - currently only http collectors configured with "Compression" as "gzip" and "Log Format" as "JSON"'
                " are supported, double check your collector is configured as such\n - the configured http collector "
                "on your tenant is disabled[/red]"
            ),
            extra={"markup": True},
        )
        raise typer.Exit(1)
    logger.info("[green]Test data pushed successfully[/green]", extra={"markup": True})


def verify_pack_exists_on_tenant(
    xsiam_client: XsiamApiClient, mr: ModelingRule, interactive: bool
):
    """Verify that the pack containing the modeling rule exists on the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        interactive (bool): Whether command is being run in interactive mode.
    """
    logger.info(
        "[cyan]Verifying pack installed on tenant[/cyan]", extra={"markup": True}
    )
    containing_pack = get_containing_pack(mr)
    containing_pack_id = containing_pack.id
    installed_packs = xsiam_client.installed_packs
    found_pack = None
    for pack in installed_packs:
        if containing_pack_id == pack.get("id"):
            found_pack = pack
            break
    if found_pack:
        logger.debug(
            f"[cyan]Found pack on tenant:\n{found_pack}[/cyan]", extra={"markup": True}
        )
    else:
        logger.error(
            f"[red]Pack {containing_pack_id} was not found on tenant[/red]",
            extra={"markup": True},
        )

        upload_result = 0
        if interactive:
            # interactively install pack
            upload = typer.confirm(
                f"Would you like to upload {containing_pack_id} to the tenant?"
            )
            if upload:
                logger.info(
                    f'[cyan underline]Upload "{containing_pack_id}"[/cyan underline]',
                    extra={"markup": True},
                )
                upload_kwargs = {
                    "zip": True,
                    "xsiam": True,
                    "input": containing_pack.path,
                    "keep_zip": None,
                    "insecure": False,
                    "input_config_file": None,
                    "skip_validation": False,
                    "verbose": False,
                    "reattach": True,
                }
                upload_result = upload_cmd(**upload_kwargs)
                if upload_result != 0:
                    logger.error(
                        f"[red]Failed to upload pack {containing_pack_id} to tenant[/red]",
                        extra={"markup": True},
                    )
                # wait for pack to finish installing
                sleep(1)
            else:
                upload_result = 1
        if not interactive or not upload_result == 0:
            logger.error(
                "[red]Please install or upload the pack to the tenant and try again[/red]",
                extra={"markup": True},
            )
            cmd_group = Group(
                Syntax(f"demisto-sdk upload -z -x -i {containing_pack.path}", "bash"),
                Syntax(f"demisto-sdk modeling-rules test {mr.path.parent}", "bash"),
            )
            printr(Panel(cmd_group))
            raise typer.Exit(1)


def verify_test_data_exists(test_data_path: Path) -> Tuple[List[str], List[str]]:
    """Verify that the test data exists and is valid.

    Args:
        test_data_path (Path): Path to the test data file.

    Returns:
        Tuple[List[str], List[str]]: Tuple of lists where the first list is test event
            ids that do not have example event data, and the second list is test event
            ids that do not have expected_values to check.
    """
    missing_event_data, missing_expected_values_data = [], []
    test_data = init_test_data.TestData.parse_file(test_data_path)
    for event_log in test_data.data:
        if not event_log.event_data:
            missing_event_data.append(event_log.test_data_event_id)
        if all([val is None for val in event_log.expected_values.values()]):
            missing_expected_values_data.append(event_log.test_data_event_id)
    return missing_event_data, missing_expected_values_data


def validate_modeling_rule(
    mrule_dir: Path,
    xsiam_url: str,
    api_key: str,
    auth_id: str,
    xsiam_token: str,
    collector_token: str,
    push: bool,
    interactive: bool,
    ctx: typer.Context,
):
    """Validate a modeling rule.

    Args:
        mrule_dir (Path): Path to the modeling rule directory.
        xsiam_url (str): URL of the xsiam tenant.
        api_key (str): xsiam API key.
        auth_id (str): xsiam auth ID.
        xsiam_token (str): xsiam token.
        collector_token (str): collector token.
        push (bool): Whether to push test event data to the tenant.
        interactive (bool): Whether command is being run in interactive mode.
        ctx (typer.Context): Typer context.
    """
    console.rule("[info]Test Modeling Rule[/info]")
    logger.info(f"[cyan]<<<< {mrule_dir} >>>>[/cyan]", extra={"markup": True})
    mr_entity = ModelingRule(mrule_dir.as_posix())
    execd_cmd = Panel(Syntax(f"{ctx.command_path} {mrule_dir}", "bash"))
    if not mr_entity.testdata_path:
        logger.warning(
            f"[yellow]No test data file found for {mrule_dir}[/yellow]",
            extra={"markup": True},
        )
        if interactive:
            generate = typer.confirm(
                f"Would you like to generate a test data file for {mrule_dir}?"
            )
            if generate:
                logger.info(
                    "[cyan underline]Generate Test Data File[/cyan underline]",
                    extra={"markup": True},
                )
                events_count = typer.prompt(
                    "For how many events would you like to generate templates?",
                    type=int,
                    default=1,
                    show_default=True,
                )

                from demisto_sdk.commands.test_content.test_modeling_rule.init_test_data import (
                    app as init_td_app,
                )

                if not init_td_app.registered_commands:
                    err = (
                        '[red]Failed to load the "init-test-data" typer application to interactively create a '
                        "testdata file.[/red]"
                    )
                    logger.error(err, extra={"markup": True})
                    raise typer.Exit(1)

                # the init-test-data typer application should only have the one command
                init_td_cmd_info = init_td_app.registered_commands[0]

                init_td_cmd = get_command_from_info(
                    init_td_cmd_info,
                    pretty_exceptions_short=app.pretty_exceptions_short,
                    rich_markup_mode=app.rich_markup_mode,
                )
                init_td_cmd_ctx = init_td_cmd.make_context(
                    init_td_cmd.name,
                    [mrule_dir.as_posix(), f"--count={events_count}"],
                    parent=ctx,
                )
                init_td_cmd.invoke(init_td_cmd_ctx)

                if mr_entity.testdata_path:
                    logger.info(
                        f"[green]Test data file generated for {mrule_dir}[/green]",
                        extra={"markup": True},
                    )
                    logger.info(
                        f"[cyan]Please complete the test data file at {mr_entity.testdata_path} "
                        "with test event(s) data and expected outputs and then rerun,[/cyan]",
                        extra={"markup": True},
                    )
                    printr(execd_cmd)
                    raise typer.Exit()
                else:
                    logger.error(
                        f"[red]Failed to generate test data file for {mrule_dir}[/red]",
                        extra={"markup": True},
                    )
                    raise typer.Exit(1)
            else:
                logger.warning(
                    f"[yellow]Skipping test data file generation for {mrule_dir}[/yellow]",
                    extra={"markup": True},
                )
                logger.warning(
                    f"[yellow]Please create a test data file for {mrule_dir} and then rerun,[/yellow]",
                    extra={"markup": True},
                )
                printr(execd_cmd)
                raise typer.Abort()
        else:
            logger.warning(
                f"[yellow]Please create a test data file for {mrule_dir} and then rerun,[/yellow]",
                extra={"markup": True},
            )
            printr(execd_cmd)
    else:
        logger.info(
            f"[cyan]Test data file found at {mr_entity.testdata_path}[/cyan]",
            extra={"markup": True},
        )
        logger.info(
            "[cyan]Checking that event data was added to the test data file[/cyan]",
            extra={"markup": True},
        )
        missing_event_data, _ = verify_test_data_exists(mr_entity.testdata_path)

        # initialize xsiam client
        xsiam_client_cfg = XsiamApiClientConfig(
            base_url=xsiam_url,
            api_key=api_key,
            auth_id=auth_id,  # type: ignore[arg-type]
            token=xsiam_token,
            collector_token=collector_token,  # type: ignore[arg-type]
        )
        xsiam_client = XsiamApiClient(xsiam_client_cfg)
        verify_pack_exists_on_tenant(xsiam_client, mr_entity, interactive)
        test_data = init_test_data.TestData.parse_file(
            mr_entity.testdata_path.as_posix()
        )

        if push:
            if missing_event_data:
                logger.warning(
                    "[yellow]Event log test data is missing for the following ids:[/yellow]",
                    extra={"markup": True},
                )
                for test_data_event_id in missing_event_data:
                    logger.warning(
                        f"[yellow] - {test_data_event_id}[/yellow]",
                        extra={"markup": True},
                    )
                logger.warning(
                    f"[yellow]Please complete the test data file at {mr_entity.testdata_path} "
                    "with test event(s) data and expected outputs and then rerun,[/yellow]",
                    extra={"markup": True},
                )
                printr(execd_cmd)
                raise typer.Exit(1)
            push_test_data_to_tenant(xsiam_client, mr_entity, test_data)
            check_dataset_exists(xsiam_client, test_data)
        else:
            logger.info(
                '[cyan]The command flag "--no-push" was passed - skipping pushing of test data[/cyan]',
                extra={"markup": True},
            )
        validate_expected_values(xsiam_client, mr_entity, test_data)


# ====================== test-modeling-rule ====================== #


def tenant_config_cb(
    ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]
):
    if ctx.resilient_parsing:
        return
    if param.value_is_missing(value):
        err_str = (
            f"{param.name} must be set either via the environment variable "
            f'"{param.envvar}" or passed explicitly when running the command'
        )
        raise typer.BadParameter(err_str)
    return value


def logs_token_cb(ctx: typer.Context, param: typer.CallbackParam, value: Optional[str]):
    if ctx.resilient_parsing:
        return
    if param.value_is_missing(value):
        parameter_to_check = "xsiam_token"
        other_token = ctx.params.get(parameter_to_check)
        if not other_token:
            err_str = (
                f"One of {param.name} or {parameter_to_check} must be set either via it's associated"
                " environment variable or passed explicitly when running the command"
            )
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
        help="The path to a directory of a modeling rule. May pass multiple paths to test multiple modeling rules.",
    ),
    xsiam_url: Optional[str] = typer.Option(
        None,
        envvar="DEMISTO_BASE_URL",
        help="The base url to the xsiam tenant.",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    api_key: Optional[str] = typer.Option(
        None,
        envvar="DEMISTO_API_KEY",
        help="The api key for the xsiam tenant.",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    auth_id: Optional[str] = typer.Option(
        None,
        envvar="XSIAM_AUTH_ID",
        help="The auth id associated with the xsiam api key being used.",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    xsiam_token: Optional[str] = typer.Option(
        None,
        envvar="XSIAM_TOKEN",
        help="The token used to push event logs to XSIAM",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
    ),
    collector_token: Optional[str] = typer.Option(
        None,
        envvar="XSIAM_COLLECTOR_TOKEN",
        help="The token used to push event logs to a custom HTTP Collector",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=logs_token_cb,
    ),
    verbosity: int = typer.Option(
        0,
        "-v",
        "--verbose",
        count=True,
        clamp=True,
        max=3,
        show_default=True,
        help="Verbosity level -v / -vv / .. / -vvv",
        rich_help_panel="Logging Configuration",
    ),
    quiet: bool = typer.Option(
        False,
        help="Quiet output - sets verbosity to default.",
        rich_help_panel="Logging Configuration",
    ),
    log_path: Path = typer.Option(
        None,
        "-lp",
        "--log-path",
        resolve_path=True,
        show_default=False,
        help="Path of directory in which you would like to store all levels of logs. If not given, then the "
        '"log_file_name" command line option will be disregarded, and the log output will be to stdout.',
        rich_help_panel="Logging Configuration",
    ),
    log_file_name: str = typer.Option(
        "test-modeling-rule.log",
        "-ln",
        "--log-name",
        resolve_path=True,
        help="The file name (including extension) where log output should be saved to.",
        rich_help_panel="Logging Configuration",
    ),
    push: bool = typer.Option(
        True,
        "--push/--no-push",
        "-p/-np",
        help=(
            "In the event that you've already pushed test data and only want to verify expected values, you can"
            ' pass "--no-push" to skip pushing the test data.'
        ),
        rich_help_panel="Interactive Configuration",
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        "-i/-ni",
        help=(
            "Interactive mode, will prompt the user if they want to generate test "
            "data templates if none exists for the passed modeling rules."
        ),
        rich_help_panel="Interactive Configuration",
        hidden=True,
    ),
):
    """
    Test a modeling rule against an XSIAM tenant
    """
    setup_rich_logging(verbosity, quiet, log_path, log_file_name)

    # override XsiamApiClient logger
    xsiam_logger = logging.getLogger(xsiam_client.__name__)
    set_console_stream_handler(xsiam_logger)
    xsiam_logger.propagate = False

    logger.info(
        f"[cyan]modeling rules directories to test: {input}[/cyan]",
        extra={"markup": True},
    )
    errors = False
    for mrule_dir in input:
        try:
            validate_modeling_rule(
                mrule_dir,
                # can ignore the types since if they are not set to str values an error occurs
                xsiam_url,  # type: ignore[arg-type]
                api_key,  # type: ignore[arg-type]
                auth_id,  # type: ignore[arg-type]
                xsiam_token,  # type: ignore[arg-type]
                collector_token,  # type: ignore[arg-type]
                push,
                interactive,
                ctx,
            )
        except typer.Exit as e:
            if e.exit_code != 0:
                errors = True
                logger.error(
                    f"[red]Error testing modeling rule {mrule_dir}[/red]",
                    extra={"markup": True},
                )
    if errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
