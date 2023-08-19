import contextlib
import os
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import dateparser
import pytz
import requests
import typer
from junitparser import TestSuite, TestCase, Failure, Skipped, Error, JUnitXml
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
from demisto_sdk.commands.common.handlers import (
    DEFAULT_JSON_HANDLER as json,  # noqa F401
)
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import is_epoch_datetime
from demisto_sdk.commands.test_content.test_modeling_rule import init_test_data
from demisto_sdk.commands.test_content.xsiam_tools.test_data import Validations
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_client import (
    XsiamApiClient,
    XsiamApiClientConfig,
)
from demisto_sdk.commands.upload.upload import upload_content_entity as upload_cmd
from demisto_sdk.utils.utils import get_containing_pack

BUILD_NUM = os.environ.get("CI_BUILD_ID")
WORKFLOW_ID = os.environ.get("CI_PIPELINE_ID")

CUSTOM_THEME = Theme(
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
console = Console(theme=CUSTOM_THEME)

EXPECTED_SCHEMA_MAPPINGS = {
    str: {"type": "string", "is_array": False},
    dict: {"type": "string", "is_array": False},
    list: {"type": "string", "is_array": False},
    int: {"type": "int", "is_array": False},
    float: {"type": "float", "is_array": False},
    datetime: {"type": "datetime", "is_array": False},
    bool: {"type": "boolean", "is_array": False},
}

SYNTAX_ERROR_IN_MODELING_RULE = (
    "No results were returned by the query - it's possible there is a syntax error with your "
    "modeling rule and that it did not install properly on the tenant"
)

FAILURE_TO_PUSH_EXPLANATION = 'Failed pushing test data to tenant, potential reasons could be:\n - an incorrect token\n - currently only http collectors configured with "Compression" as "gzip" and "Log Format" as "JSON" are supported, double check your collector is configured as such\n - the configured http collector on your tenant is disabled'

XQL_QUERY_ERROR_EXPLANATION = (
    "Error executing XQL query, potential reasons could be:\n - mismatch between "
    "dataset/vendor/product marked in the test data from what is in the modeling rule\n"
    " - dataset was not created in the tenant\n - model fields in the query are invalid\n"
    "Try manually querying your tenant to discover the exact problem."
)
TIME_ZONE_WARNING = "Could not find timezone"

NOT_AVAILABLE = "N/A"

app = typer.Typer()


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


def day_suffix(day: int) -> str:
    """
    Returns a suffix string base on the day of the month.
        for 1, 21, 31 => st
        for 2, 22 => nd
        for 3, 23 => rd
        for to all the others => th

        see here for more details: https://en.wikipedia.org/wiki/English_numerals#Ordinal_numbers

    Args:
        day: The day of the month represented by a number.

    Returns:
        suffix string (st, nd, rd, th).
    """
    return "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def convert_epoch_time_to_string_time(
    epoch_time: int, with_ms: bool = False, tenant_timezone: str = "UTC"
) -> str:
    """
    Converts epoch time with milliseconds to string time with timezone delta.

    Args:
        epoch_time: The received epoch time (with milliseconds).
        with_ms: Whether to convert the epoch time with ms or not default is False.
        tenant_timezone: The timezone of the XSIAM tenant.

    Returns:
        The string time with timezone delta.
    """
    datetime_object = datetime.fromtimestamp(
        epoch_time / 1000, pytz.timezone(tenant_timezone)
    )
    time_format = (
        f"%b %-d{day_suffix(datetime_object.day)} %Y %H:%M:%S{'.%f' if with_ms else ''}"
    )
    return datetime_object.strftime(time_format)


def verify_results(
    modeling_rule: ModelingRule,
    tested_dataset: str,
    results: List[dict],
    test_data: init_test_data.TestData,
) -> list[TestCase]:
    """Verify that the results of the XQL query match the expected values.

    Args:
        modeling_rule (ModelingRule): The modeling rule object parsed from the modeling rule file.
        tested_dataset (str): The dataset to verify result for.
        results (List[dict]): The results of the XQL query.
        test_data (init_test_data.TestData): The data parsed from the test data file.

    Returns:
        list[TestCase]: Tuple of a boolean indicating whether the results match the expected values, and a TestCase
    """

    if not results:
        logger.error(
            f"[red]{SYNTAX_ERROR_IN_MODELING_RULE}[/red]", extra={"markup": True}
        )
        test_case = TestCase(
            f"Modeling rule - {modeling_rule.normalize_file_name()}",
            classname="Modeling Rule Results",
        )
        test_case.result = [Failure(SYNTAX_ERROR_IN_MODELING_RULE)]
        test_case.system_err = SYNTAX_ERROR_IN_MODELING_RULE
        return [test_case]

    rule_relevant_data = [
        data for data in test_data.data if data.dataset == tested_dataset
    ]
    if len(results) != len(rule_relevant_data):
        err = (
            f"Expected {len(test_data.data)} results, got {len(results)}. Verify that the event"
            " data used in your test data file meets the criteria of the modeling rule, e.g. the filter"
            " condition."
        )
        test_case = TestCase(
            f"Modeling rule - {modeling_rule.normalize_file_name()}",
            classname="Modeling Rule Results",
        )
        test_case.result = [Failure(err)]
        logger.error(f"[red]{err}[/red]", extra={"markup": True})
        return [test_case]

    test_cases = []
    for i, result in enumerate(results, start=1):
        expected_values = None
        tenant_timezone: str = ""
        logger.info(
            f"\n[cyan][underline]Result {i}/{len(results)}[/underline][/cyan]",
            extra={"markup": True},
        )

        # get expected_values for the given query result
        td_event_id = result.pop(f"{tested_dataset}.test_data_event_id")
        result_test_case = TestCase(
            f"Modeling rule - {modeling_rule.path} {i}/{len(results)} test_data_event_id:{td_event_id}",
            classname=f"test_data_event_id:{td_event_id}",
        )
        result_test_case_system_out = []
        result_test_case_system_err = []
        result_test_case_results = []

        for e in test_data.data:
            if str(e.test_data_event_id) == td_event_id:
                expected_values = e.expected_values
                tenant_timezone = e.tenant_timezone
                break
        if not tenant_timezone:
            result_test_case_system_out.append(TIME_ZONE_WARNING)
            logger.warning(f"[yellow]{TIME_ZONE_WARNING}[/yellow]")

        if expected_values:
            if (
                expected_time_value := expected_values.get(
                    SingleModelingRule.TIME_FIELD
                )
            ) and (time_value := result.get(SingleModelingRule.TIME_FIELD)):
                result[
                    SingleModelingRule.TIME_FIELD
                ] = convert_epoch_time_to_string_time(
                    time_value, "." in expected_time_value, tenant_timezone
                )
            table_result = create_table(expected_values, result)
            printr(table_result)
            for key, val in expected_values.items():
                if val:
                    result_val = result.get(key)
                    out = f"Checking for key {key}:\n - expected: {val}\n - received: {result_val}"
                    logger.debug(f"[cyan]{out}[/cyan]", extra={"markup": True})
                    result_test_case_system_out.append(out)

                    if type(result_val) == type(val) and result_val == val:
                        out = f"Value and Type Matched for key {key}"
                        result_test_case_system_out.append(out)
                        logger.debug(out)
                    else:
                        if type(result_val) == type(val):
                            err = (
                                f"Expected value does not match for key {key}: - expected: {val} - received: {result_val} "
                                f"Types match:{type(result_val)}"
                            )
                            logger.error(
                                f'[red][bold]{key}[/bold] --- "{result_val}" != "{val}" Types match:{type(result_val)}\n',
                                extra={"markup": True},
                            )
                        else:
                            err = (
                                f"Expected value and type do not match for key {key}: - expected: {val} - received: "
                                f"{result_val} expected type: {type(val)} received type: {type(result_val)}"
                            )
                            logger.error(
                                f'[red][bold]{key}[/bold] --- "{result_val}" != "{val}"\n'
                                f'[bold]{key}[/bold] --- Received value type: "{type(result_val)}" '
                                f'!=  Expected value type: "{type(val)}"[/red]',
                                extra={"markup": True},
                            )
                        result_test_case_system_err.append(err)
                        result_test_case_results.append(Failure(err))
                else:
                    err = f"No mapping for this {key} - skipping checking match"
                    result_test_case_system_out.append(err)
                    result_test_case_results.append(Skipped(err))
                    logger.debug(f"[cyan]{err}[/cyan]", extra={"markup": True})
        else:
            err = f"No matching expected_values found for test_data_event_id={td_event_id} in test_data {test_data}"
            logger.error(f"[red]{err}[/red]", extra={"markup": True})
            result_test_case_results.append(Failure(err))

        result_test_case.system_err = "\n".join(result_test_case_system_err)
        result_test_case.system_out = "\n".join(result_test_case_system_out)
        if result_test_case_results:
            result_test_case.result = result_test_case_results

        test_cases.append(result_test_case)

    return test_cases


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
    xsiam_client: XsiamApiClient,
    modeling_rule: ModelingRule,
    test_data: init_test_data.TestData,
) -> list[TestCase]:
    """Validate the expected_values in the given test data file."""
    validate_expected_values_test_cases = []
    for rule in modeling_rule.rules:
        validate_expected_values_test_case = TestCase(
            f"Validate expected_values {modeling_rule.path} dataset:{rule.dataset} "
            f"vendor:{rule.vendor} product:{rule.product}",
            classname="Validate expected values query",
        )
        query = generate_xql_query(
            rule,
            [
                str(d.test_data_event_id)
                for d in test_data.data
                if d.dataset == rule.dataset
            ],
        )
        query_info = f"Query for dataset {rule.dataset}:\n{query}"
        logger.debug(query_info)
        validate_expected_values_test_case_system_out = [query_info]
        try:
            execution_id = xsiam_client.start_xql_query(query)
            results = xsiam_client.get_xql_query_result(execution_id)
            validate_expected_values_test_case_system_out.append(
                "Successfully executed XQL query"
            )
            logger.debug("Successfully executed XQL query")
        except requests.exceptions.HTTPError:
            logger.error(
                f"[red]{XQL_QUERY_ERROR_EXPLANATION}[/red]",
                extra={"markup": True},
            )
            validate_expected_values_test_case.system_err = XQL_QUERY_ERROR_EXPLANATION
            validate_expected_values_test_case.result = [
                Error("Failed to execute XQL query")
            ]
        else:
            verify_results_test_cases = verify_results(
                modeling_rule, rule.dataset, results, test_data
            )
            validate_expected_values_test_cases.extend(verify_results_test_cases)
        validate_expected_values_test_case.system_out = "\n".join(
            validate_expected_values_test_case_system_out
        )
        validate_expected_values_test_cases.append(validate_expected_values_test_case)

    return validate_expected_values_test_cases


def validate_schema_aligned_with_test_data(
    test_data: init_test_data.TestData, schema: Dict
) -> bool:
    """
    Validates that the schema is aligned with the test-data types.

    Args:
        test_data: the test data object.
        schema: the content of the schema file.

    """

    # map each dataset from the schema to the correct events that has the same dataset
    schema_dataset_to_events = {
        dataset: [
            event_log for event_log in test_data.data if event_log.dataset == dataset
        ]
        for dataset in schema.keys()
    }

    errors_occurred = False

    for dataset, event_logs in schema_dataset_to_events.items():
        all_schema_dataset_mappings = schema[dataset]
        test_data_mappings: Dict = {}
        error_logs = set()
        for event_log in event_logs:
            for event_key, event_val in event_log.event_data.items():
                if (
                    event_val is None
                ):  # if event_val is None, warn and continue looping.
                    logger.warning(
                        f"{event_key=} is null on {event_log.test_data_event_id} "
                        f"event for {dataset=}, ignoring {event_key=}",
                        extra={"markup": True},
                    )
                    # add the event key to the mapping to validate there isn't another key with a different type
                    test_data_mappings[event_key] = None
                    continue

                if schema_key_mappings := all_schema_dataset_mappings.get(event_key):
                    # we do not consider epochs as datetime in xsiam
                    if (
                        isinstance(event_val, str)
                        and not is_epoch_datetime(event_val)
                        and dateparser.parse(
                            event_val, settings={"STRICT_PARSING": True}
                        )
                    ):
                        event_val_type = datetime
                    else:
                        event_val_type = type(event_val)

                    test_data_key_mappings = EXPECTED_SCHEMA_MAPPINGS[event_val_type]

                    if (
                        existing_testdata_key_mapping := test_data_mappings.get(
                            event_key
                        )
                    ) and existing_testdata_key_mapping != test_data_key_mappings:
                        error_logs.add(
                            f"The testdata contains events with the same {event_key=} "
                            f"that have different types for dataset {dataset}"
                        )
                        errors_occurred = True
                        continue
                    else:
                        test_data_mappings[event_key] = test_data_key_mappings

                    if test_data_key_mappings != schema_key_mappings:
                        error_logs.add(
                            f"[red][bold]the field {event_key} has mismatch on type or is_array in "
                            f"event ID {event_log.test_data_event_id} between testdata "
                            f"and schema[/bold] --- TestData Mapping "
                            f'"{test_data_key_mappings}" != Schema Mapping "{schema_key_mappings}"'
                        )
                        errors_occurred = True

        missing_test_data_keys = set(all_schema_dataset_mappings.keys()) - set(
            test_data_mappings.keys()
        )
        if missing_test_data_keys:
            logger.warning(
                f"[yellow]The following fields {missing_test_data_keys} are in schema for dataset {dataset}, but not "
                f"in test-data, make sure to remove them from schema or add them to test-data if necessary[/yellow]",
                extra={"markup": True},
            )

        if error_logs:
            for _log in error_logs:
                logger.error(_log, extra={"markup": True})
        else:
            logger.info(
                f"[green]Schema type mappings = Testdata type mappings for dataset {dataset}[/green]",
                extra={"markup": True},
            )
    return not errors_occurred


def check_dataset_exists(
    xsiam_client: XsiamApiClient,
    test_data: init_test_data.TestData,
    timeout: int = 90,
    interval: int = 5,
    init_sleep_time: int = 30,
) -> TestCase:
    """Check if the dataset in the test data file exists in the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        test_data (init_test_data.TestData): The data parsed from the test data file.
        timeout (int, optional): The number of seconds to wait for the dataset to exist. Defaults to 90 seconds.
        interval (int, optional): The number of seconds to wait between checking for the dataset. Defaults to 5.
        init_sleep_time (int, optional): The number of seconds to wait for dataset installation. Defaults to 30.

    """
    process_failed = False
    dataset_set = {data.dataset for data in test_data.data}
    dataset_set_test_case = TestCase(
        f"Check if dataset exists in tenant", classname="Check dataset exists"
    )
    dataset_set_test_case_start_time = datetime.utcnow()
    test_case_results = []
    logger.debug(
        f"Sleeping for {init_sleep_time} seconds before query for the dataset, to make sure the dataset was installed correctly."
    )
    sleep(init_sleep_time)

    for dataset in dataset_set:
        results_exist = False
        dataset_exist = False
        logger.info(
            f'[cyan]Checking if dataset "{dataset}" exists on the tenant...[/cyan]',
            extra={"markup": True},
        )
        query = f"config timeframe = 10y | dataset = {dataset}"
        for i in range(timeout // interval):
            with contextlib.suppress(requests.exceptions.HTTPError):
                # If the dataset doesn't exist HTTPError exception is raised.
                logger.debug(f"Check #{i+1}...")
                execution_id = xsiam_client.start_xql_query(
                    query, print_req_error=(i + 1 == timeout // interval)
                )
                dataset_exist = True
                # if we got result we will break from the loop
                if results := xsiam_client.get_xql_query_result(execution_id):
                    logger.info(
                        f"[green]Dataset {dataset} exists[/green]",
                        extra={"markup": True},
                    )
                    results_exist = True
                    break
                else:
                    results_exist = False
                    logger.info(
                        f"[cyan]trying to get results from the dataset for the {day_suffix(i+1)} time. continuing to try to get the results.[/cyan]",
                        extra={"markup": True},
                    )
                sleep(interval)

        # There are no results from the dataset, but it exists.
        if not results:
            err = (
                f"Dataset {dataset} exists but no results were returned. This could mean that your testdata "
                "does not meet the criteria for an associated Parsing Rule and is therefore being dropped from "
                "the dataset. Check to see if a Parsing Rule exists for your dataset and that your testdata "
                "meets the criteria for that rule."
            )
            test_case_results.append(Error(err))
            logger.error(f"[red]{err}[/red]", extra={"markup": True})
        if not dataset_exist:
            err = f"Dataset {dataset} does not exist after {timeout} seconds."
            test_case_results.append(Error(err))
            logger.error(f"[red]{err}[/red]", extra={"markup": True})

        process_failed |= not (dataset_exist and results_exist)

    if test_case_results:
        dataset_set_test_case.result = test_case_results
    dataset_set_test_case.time = (
        datetime.utcnow() - dataset_set_test_case_start_time
    ).total_seconds()
    return dataset_set_test_case


def push_test_data_to_tenant(
    xsiam_client: XsiamApiClient, mr: ModelingRule, test_data: init_test_data.TestData
) -> TestCase:
    """Push the test data to the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        test_data (init_test_data.TestData): Test data object parsed from the test data file.
    """
    push_test_data_test_case = TestCase(
        f"Push test data to tenant {mr.path}",
        classname="Push test data to tenant",
    )
    push_test_data_test_case_start_time = datetime.utcnow()
    system_errors = []
    for rule in mr.rules:
        events_test_data = [
            {
                **event_log.event_data,
                "test_data_event_id": str(event_log.test_data_event_id),
            }
            for event_log in test_data.data
            if isinstance(event_log.event_data, dict)
            and event_log.dataset == rule.dataset
        ]
        logger.info(
            f"[cyan]Pushing test data for {rule.dataset} to tenant...[/cyan]",
            extra={"markup": True},
        )
        try:
            xsiam_client.push_to_dataset(events_test_data, rule.vendor, rule.product)
        except requests.exceptions.HTTPError:
            system_err = (
                f"Failed pushing test data to tenant for dataset {rule.dataset}"
            )
            system_errors.append(system_err)
            logger.error(f"[red]{system_err}[/red]", extra={"markup": True})

    if system_errors:
        logger.error(
            f"[red]{FAILURE_TO_PUSH_EXPLANATION}[/red]",
            extra={"markup": True},
        )
        push_test_data_test_case.system_err = "\n".join(system_errors)
        push_test_data_test_case.result = [Failure(FAILURE_TO_PUSH_EXPLANATION)]
    else:
        system_out = "Test data pushed successfully"
        push_test_data_test_case.system_out = system_out
        logger.info(f"[green]{system_out}[/green]", extra={"markup": True})
    push_test_data_test_case.time = (
        datetime.utcnow() - push_test_data_test_case_start_time
    ).total_seconds()
    return push_test_data_test_case


def verify_pack_exists_on_tenant(
    xsiam_client: XsiamApiClient, mr: ModelingRule, interactive: bool
) -> bool:
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
                    f'[cyan][underline]Upload "{containing_pack_id}"[/underline][/cyan]',
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
        if not interactive or upload_result != 0:
            logger.error(
                "[red]Please install or upload the pack to the tenant and try again[/red]",
                extra={"markup": True},
            )
            cmd_group = Group(
                Syntax(f"demisto-sdk upload -z -x -i {containing_pack.path}", "bash"),
                Syntax(f"demisto-sdk modeling-rules test {mr.path.parent}", "bash"),
            )
            printr(Panel(cmd_group))
            return False
    return True


def verify_test_data_exists(test_data_path: Path) -> Tuple[List[UUID], List[UUID]]:
    """Verify that the test data exists and is valid.

    Args:
        test_data_path (Path): Path to the test data file.

    Returns:
        Tuple[List[str], List[str]]: Tuple of lists where the first list is test event
            first list: ids that do not have example event data.
            second list is test event ids that do not have expected_values to check.
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
    modeling_rule_directory: Path,
    xsiam_url: str,
    api_key: str,
    auth_id: str,
    xsiam_token: str,
    collector_token: str,
    push: bool,
    interactive: bool,
    ctx: typer.Context,
) -> Tuple[bool, TestSuite | None]:
    """Validate a modeling rule.

    Args:
        modeling_rule_directory (Path): Path to the modeling rule directory.
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
    logger.info(
        f"[cyan]<<<< {modeling_rule_directory} >>>>[/cyan]", extra={"markup": True}
    )
    modeling_rule = ModelingRule(modeling_rule_directory.as_posix())
    containing_pack = get_containing_pack(modeling_rule)
    executed_command = Panel(
        Syntax(f"{ctx.command_path} {modeling_rule_directory}", "bash")
    )
    modeling_rule_test_suite = TestSuite(
        f"Modeling Rule Test Results {modeling_rule.path}"
    )
    modeling_rule_test_suite.filepath = modeling_rule.path
    modeling_rule_test_suite.add_property("modeling_rule_path", modeling_rule.path)
    modeling_rule_test_suite.add_property(
        "test_data_path", modeling_rule.testdata_path or NOT_AVAILABLE
    )
    modeling_rule_test_suite.add_property("schema_path", modeling_rule.schema_path)
    modeling_rule_test_suite.add_property("push", push)
    modeling_rule_test_suite.add_property("interactive", interactive)
    modeling_rule_test_suite.add_property("xsiam_url", xsiam_url)
    modeling_rule_test_suite.add_property("from_version", modeling_rule.from_version)
    modeling_rule_test_suite.add_property("to_version", modeling_rule.to_version)
    modeling_rule_test_suite.add_property("pack_id", containing_pack.id)
    if modeling_rule.testdata_path:
        logger.info(
            f"[cyan]Test data file found at {modeling_rule.testdata_path}[/cyan]",
            extra={"markup": True},
        )
        logger.info(
            "[cyan]Checking that event data was added to the test data file[/cyan]",
            extra={"markup": True},
        )
        missing_event_data, _ = verify_test_data_exists(modeling_rule.testdata_path)

        # initialize xsiam client
        xsiam_client_cfg = XsiamApiClientConfig(
            base_url=xsiam_url,  # type: ignore[arg-type]
            api_key=api_key,  # type: ignore[arg-type]
            auth_id=auth_id,  # type: ignore[arg-type]
            token=xsiam_token,  # type: ignore[arg-type]
            collector_token=collector_token,  # type: ignore[arg-type]
        )
        xsiam_client = XsiamApiClient(xsiam_client_cfg)
        if not verify_pack_exists_on_tenant(xsiam_client, modeling_rule, interactive):
            test_case = TestCase(
                "Pack not installed on tenant", classname="Modeling Rule"
            )
            test_case.result = [Error("Pack not installed on tenant")]
            modeling_rule_test_suite.add_testcase(test_case)
            return False, modeling_rule_test_suite

        test_data = init_test_data.TestData.parse_file(
            modeling_rule.testdata_path.as_posix()
        )

        schema_test_case = TestCase("Validate Schema", classname="Modeling Rule")
        if schema_path := modeling_rule.schema_path:
            with open(modeling_rule.schema_path) as schema_file:
                try:
                    schema = json.load(schema_file)
                except JSONDecodeError as ex:
                    err = f"Failed to parse schema file {modeling_rule.schema_path} as JSON"
                    logger.error(
                        f"[red]{err}[/red]",
                        extra={"markup": True},
                    )
                    schema_test_case.system_err = str(ex)
                    schema_test_case.result = [Error(err)]
                    modeling_rule_test_suite.add_testcase(schema_test_case)
                    return False, modeling_rule_test_suite
        else:
            err = f"Schema file does not exist in path {modeling_rule.schema_path}"
            logger.error(
                f"[red]{err}[/red]",
                extra={"markup": True},
            )
            schema_test_case.system_err = err
            schema_test_case.result = [Error(err)]
            modeling_rule_test_suite.add_testcase(schema_test_case)
            return False, modeling_rule_test_suite

        if (
            Validations.SCHEMA_TYPES_ALIGNED_WITH_TEST_DATA.value
            not in test_data.ignored_validations
        ):
            logger.info(
                f"[green]Validating that the schema {schema_path} is aligned with TestData file.[/green]",
                extra={"markup": True},
            )

            if not validate_schema_aligned_with_test_data(
                test_data=test_data, schema=schema
            ):
                err = f"The schema {schema_path} is not aligned with the test data file {modeling_rule.testdata_path}"
                logger.error(
                    f"[red]{err}[/red]",
                    extra={"markup": True},
                )
                schema_test_case.system_err = err
                schema_test_case.result = [Error(err)]
                modeling_rule_test_suite.add_testcase(schema_test_case)
                return False, modeling_rule_test_suite
        else:
            skipped = f"Skipping the validation to check that the schema {schema_path} "
            f"is aligned with TestData file."
            logger.info(f"[green]{skipped}[/green]", extra={"markup": True})
            schema_test_case.result = [Skipped(skipped)]
            modeling_rule_test_suite.add_testcase(schema_test_case)

        if push:
            if missing_event_data:
                missing_event_data_test_case = TestCase(
                    "Missing Event Data", classname="Modeling Rule"
                )
                err = f"Missing Event Data for the following test data event ids: {missing_event_data}"
                missing_event_data_test_case.result = [Error(err)]
                prefix = "Event log test data is missing for the following ids:"
                system_errors = [prefix]
                logger.warning(
                    f"[yellow]{prefix}[/yellow]",
                    extra={"markup": True},
                )
                for test_data_event_id in missing_event_data:
                    logger.warning(
                        f"[yellow] - {test_data_event_id}[/yellow]",
                        extra={"markup": True},
                    )
                    system_errors.append(test_data_event_id)
                suffix = (
                    f"Please complete the test data file at {modeling_rule.testdata_path} "
                    f"with test event(s) data and expected outputs and then rerun"
                )
                logger.warning(
                    f"[yellow]{suffix}[/yellow]",
                    extra={"markup": True},
                )
                system_errors.append(suffix)
                missing_event_data_test_case.system_err = "\n".join(system_errors)
                modeling_rule_test_suite.add_testcase(missing_event_data_test_case)

                printr(executed_command)
                return False, modeling_rule_test_suite

            push_test_data_test_case = push_test_data_to_tenant(
                xsiam_client, modeling_rule, test_data
            )
            modeling_rule_test_suite.add_testcase(push_test_data_test_case)
            if not push_test_data_test_case.is_passed:
                return False, modeling_rule_test_suite

            dataset_set_test_case = check_dataset_exists(xsiam_client, test_data)
            modeling_rule_test_suite.add_testcase(dataset_set_test_case)
            if not dataset_set_test_case.is_passed:
                return False, modeling_rule_test_suite
        else:
            logger.info(
                '[cyan]The command flag "--no-push" was passed - skipping pushing of test data[/cyan]',
                extra={"markup": True},
            )
        logger.info(
            "[cyan]Validating expected_values...[/cyan]", extra={"markup": True}
        )
        validate_expected_values_test_cases = validate_expected_values(
            xsiam_client, modeling_rule, test_data
        )
        modeling_rule_test_suite.add_testcases(validate_expected_values_test_cases)
        if (
            not modeling_rule_test_suite.errors
            and not modeling_rule_test_suite.failures
        ):
            logger.info(
                "[green]Mappings validated successfully[/green]", extra={"markup": True}
            )
            return True, modeling_rule_test_suite
        return False, modeling_rule_test_suite
    else:
        logger.warning(
            f"[yellow]No test data file found for {modeling_rule_directory}[/yellow]",
            extra={"markup": True},
        )
        if interactive:
            generate = typer.confirm(
                f"Would you like to generate a test data file for {modeling_rule_directory}?"
            )
            if generate:
                logger.info(
                    "[cyan][underline]Generate Test Data File[/underline][/cyan]",
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
                    return False, None

                # the init-test-data typer application should only have the one command
                init_td_cmd_info = init_td_app.registered_commands[0]

                init_td_cmd = get_command_from_info(
                    init_td_cmd_info,
                    pretty_exceptions_short=app.pretty_exceptions_short,
                    rich_markup_mode=app.rich_markup_mode,
                )
                init_td_cmd_ctx = init_td_cmd.make_context(
                    init_td_cmd.name,
                    [modeling_rule_directory.as_posix(), f"--count={events_count}"],
                    parent=ctx,
                )
                init_td_cmd.invoke(init_td_cmd_ctx)

                if modeling_rule.testdata_path:
                    logger.info(
                        f"[green]Test data file generated for {modeling_rule_directory}[/green]",
                        extra={"markup": True},
                    )
                    logger.info(
                        f"[cyan]Please complete the test data file at {modeling_rule.testdata_path} "
                        "with test event(s) data and expected outputs and then rerun[/cyan]",
                        extra={"markup": True},
                    )
                    printr(executed_command)
                else:
                    logger.error(
                        f"[red]Failed to generate test data file for {modeling_rule_directory}[/red]",
                        extra={"markup": True},
                    )
            else:
                logger.warning(
                    f"[yellow]Skipping test data file generation for {modeling_rule_directory}[/yellow]",
                    extra={"markup": True},
                )
                logger.error(
                    f"[red]Please create a test data file for {modeling_rule_directory} and then rerun[/red]",
                    extra={"markup": True},
                )
                printr(executed_command)
        else:
            logger.error(
                f"[red]Please create a test data file for {modeling_rule_directory} and then rerun[/red]",
                extra={"markup": True},
            )
            printr(executed_command)
        return False, None


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


@app.command(
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def test_modeling_rule(
    ctx: typer.Context,
    inputs: List[Path] = typer.Argument(
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
    output_junit_file: Optional[Path] = typer.Option(
        None, "-jp", "--junit-path", help="Path to the output JUnit XML file."
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console_log_threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file_log_threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: str = typer.Option(
        "demisto_sdk_debug.log",
        "-lp",
        "--log_file_path",
        help="Path to the log file. Default: ./demisto_sdk_debug.log.",
    ),
):
    """
    Test a modeling rule against an XSIAM tenant
    """
    logging_setup(
        console_log_threshold=console_log_threshold,  # type: ignore[arg-type]
        file_log_threshold=file_log_threshold,  # type: ignore[arg-type]
        log_file_path=log_file_path,
    )
    handle_deprecated_args(ctx.args)

    logger.info(
        f"[cyan]modeling rules directories to test: {inputs}[/cyan]",
        extra={"markup": True},
    )
    errors = False
    xml = JUnitXml()
    for modeling_rule_directory in inputs:
        success, modeling_rule_test_suite = validate_modeling_rule(
            modeling_rule_directory,
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
        if not success:
            errors = True
            logger.error(
                f"[red]Error testing modeling rule {modeling_rule_directory}[/red]",
                extra={"markup": True},
            )
        if modeling_rule_test_suite:
            xml.add_testsuite(modeling_rule_test_suite)

    if output_junit_file:
        xml.write(output_junit_file, pretty=True)

    if errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
