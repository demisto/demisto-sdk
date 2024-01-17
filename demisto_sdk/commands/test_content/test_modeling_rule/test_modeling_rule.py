import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import dateparser
import pytz
import requests
import typer
from junitparser import Error, Failure, JUnitXml, Skipped, TestCase, TestSuite
from junitparser.junitparser import Result
from packaging.version import Version
from tabulate import tabulate
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)
from typer.main import get_command_from_info

from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
    ModelingRule,
    SingleModelingRule,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import (
    DEFAULT_JSON_HANDLER as json,
)
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import (
    get_file,
    is_epoch_datetime,
    parse_int_or_default,
)
from demisto_sdk.commands.test_content.test_modeling_rule.constants import (
    EXPECTED_SCHEMA_MAPPINGS,
    FAILURE_TO_PUSH_EXPLANATION,
    NOT_AVAILABLE,
    SYNTAX_ERROR_IN_MODELING_RULE,
    TIME_ZONE_WARNING,
    XQL_QUERY_ERROR_EXPLANATION,
)
from demisto_sdk.commands.test_content.xsiam_tools.test_data import (
    TestData,
    Validations,
)
from demisto_sdk.commands.test_content.xsiam_tools.xsiam_client import (
    XsiamApiClient,
    XsiamApiClientConfig,
)
from demisto_sdk.commands.upload.upload import upload_content_entity as upload_cmd
from demisto_sdk.utils.utils import get_containing_pack

CI_PIPELINE_ID = os.environ.get("CI_PIPELINE_ID")
XSIAM_CLIENT_SLEEP_INTERVAL = 60
XSIAM_CLIENT_RETRY_ATTEMPTS = 5

app = typer.Typer()


def duration_since_start_time(start_time: datetime) -> float:
    """Get the duration since the given start time, in seconds.

    Args:
        start_time (datetime): Start time.

    Returns:
        float: Duration since the given start time, in seconds.
    """
    return (datetime.now(timezone.utc) - start_time).total_seconds()


def create_table(expected: Dict[str, Any], received: Dict[str, Any]) -> str:
    """Create a table to display the expected and received values.

    Args:
        expected: mapping of keys to expected values
        received: mapping of keys to received values

    Returns:
        String representation of a table, to display the expected and received values.
    """
    data = [(key, str(val), str(received.get(key))) for key, val in expected.items()]
    return tabulate(
        data,
        tablefmt="pretty",
        headers=["Model Field", "Expected Value", "Received Value"],
    )


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


def get_relative_path_to_content(path: Path) -> str:
    """Get the relative path to the content directory.

    Args:
        path: The path to the content item.

    Returns:
        Path: The relative path to the content directory.
    """
    if path.is_absolute() and path.as_posix().startswith(CONTENT_PATH.as_posix()):
        return path.as_posix().replace(f"{CONTENT_PATH.as_posix()}{os.path.sep}", "")
    return path.as_posix()


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


def get_type_pretty_name(obj: Any) -> str:
    """Get the pretty name of the type of the given object.

    Args:
        obj (Any): The object to get the type name for.

    Returns:
        str: The pretty name of the type of the given object.
    """
    return {
        type(None): "null",
        list: "list",
        dict: "dict",
        tuple: "tuple",
        set: "set",
        UUID: "UUID",
        str: "string",
        int: "int",
        float: "float",
        bool: "boolean",
        datetime: "datetime",
    }.get(type(obj), str(type(obj)))


def sanitize_received_value_by_expected_type(
    received_value: Any, expected_type: str
) -> Tuple[str, Any]:
    """
    XSIAM returns numeric values from the API always as float, so we need to check if the expected type is int and if that's the
    case and the value returned is a numeric without a floating point value, we can assume it's an int.
    Args:
        expected_type: The expected type of the object.
        received_value: The object to get the type for.

    Returns:
        The expected type of the object, and the object itself after being sanitized.
    """
    received_value_type = get_type_pretty_name(received_value)
    # The values returned from XSIAM for int/float are always float, so we need to check if the expected type is int.
    if (
        expected_type == "int"
        and received_value_type == "float"
        and int(received_value) == received_value
    ):
        return "int", int(received_value)
    return received_value_type, received_value


def create_retrying_caller(retry_attempts: int, sleep_interval: int) -> Retrying:
    """Create a Retrying object with the given retry_attempts and sleep_interval."""
    sleep_interval = parse_int_or_default(sleep_interval, XSIAM_CLIENT_SLEEP_INTERVAL)
    retry_attempts = parse_int_or_default(retry_attempts, XSIAM_CLIENT_RETRY_ATTEMPTS)
    retry_params: Dict[str, Any] = {
        "reraise": True,
        "before_sleep": before_sleep_log(logger, logging.DEBUG),
        "retry": retry_if_exception_type(requests.exceptions.RequestException),
        "stop": stop_after_attempt(retry_attempts),
        "wait": wait_fixed(sleep_interval),
    }
    return Retrying(**retry_params)


def xsiam_execute_query(
    xsiam_client: XsiamApiClient, query: str, print_req_error: bool = True
) -> List[dict]:
    """Execute an XQL query and return the results.
    Wrapper for XsiamApiClient.execute_query() with retry logic.
    """
    execution_id = xsiam_client.start_xql_query(query)
    return xsiam_client.get_xql_query_result(execution_id)


def xsiam_push_to_dataset(
    xsiam_client: XsiamApiClient, events_test_data: List[dict], rule: SingleModelingRule
) -> Dict[str, Any]:
    """Push the test data to the XSIAM dataset.
    Wrapper for XsiamApiClient.push_to_dataset() with retry logic.
    """
    return xsiam_client.push_to_dataset(events_test_data, rule.vendor, rule.product)


def xsiam_get_installed_packs(xsiam_client: XsiamApiClient) -> List[Dict[str, Any]]:
    """Get the list of installed packs from the XSIAM tenant.
    Wrapper for XsiamApiClient.get_installed_packs() with retry logic.
    """
    return xsiam_client.installed_packs


def verify_results(
    modeling_rule: ModelingRule,
    tested_dataset: str,
    results: List[dict],
    test_data: TestData,
) -> List[TestCase]:
    """Verify that the results of the XQL query match the expected values.

    Args:
        modeling_rule: The modeling rule object parsed from the modeling rule file.
        tested_dataset (str): The dataset to verify result for.
        results (List[dict]): The results of the XQL query.
        test_data (init_test_data.TestData): The data parsed from the test data file.

    Returns:
        list[TestCase]: List of test cases for the results of the XQL query.
    """

    if not results:
        logger.error(
            f"[red]{SYNTAX_ERROR_IN_MODELING_RULE}[/red]", extra={"markup": True}
        )
        test_case = TestCase(
            f"Modeling rule - {modeling_rule.normalize_file_name()}",
            classname="Modeling Rule Results",
        )
        test_case.result += [Failure(SYNTAX_ERROR_IN_MODELING_RULE)]
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
        test_case.result += [Failure(err)]
        logger.error(f"[red]{err}[/red]", extra={"markup": True})
        return [test_case]

    test_cases = []
    for i, result in enumerate(results, start=1):
        td_event_id = result.pop(f"{tested_dataset}.test_data_event_id")
        msg = (
            f"Modeling rule - {get_relative_path_to_content(modeling_rule.path)} {i}/{len(results)}"
            f" test_data_event_id:{td_event_id}"
        )
        logger.info(
            f"[cyan]{msg}[/cyan]",
            extra={"markup": True},
        )
        result_test_case = TestCase(
            msg,
            classname=f"test_data_event_id:{td_event_id}",
        )
        verify_results_against_test_data(
            result_test_case, result, test_data, td_event_id
        )

        test_cases.append(result_test_case)

    return test_cases


def verify_results_against_test_data(
    result_test_case: TestCase,
    result: Dict[str, Any],
    test_data: TestData,
    td_event_id: str,
):
    """Verify that the results of the XQL query match the expected values."""

    result_test_case_system_out = []
    result_test_case_system_err = []
    result_test_case_results = []
    tenant_timezone: str = ""
    expected_values = None
    # Find the expected values for the given test data event ID.
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
            expected_time_value := expected_values.get(SingleModelingRule.TIME_FIELD)
        ) and (time_value := result.get(SingleModelingRule.TIME_FIELD)):
            result[SingleModelingRule.TIME_FIELD] = convert_epoch_time_to_string_time(
                time_value, "." in expected_time_value, tenant_timezone
            )
        table_result = create_table(expected_values, result)
        logger.info(f"\n{table_result}")
        for expected_key, expected_value in expected_values.items():
            if expected_value:
                received_value = result.get(expected_key)
                expected_value_type = get_type_pretty_name(expected_value)
                (
                    received_value_type_sanitized,
                    received_value_sanitized,
                ) = sanitize_received_value_by_expected_type(
                    received_value, expected_value_type
                )
                out = (
                    f"Checking for key {expected_key} - "
                    f"expected value:{expected_value} expected type:{expected_value_type} "
                    f"received value:{received_value_sanitized} received type:{received_value_type_sanitized} "
                    f"before sanitization - received value:{received_value} received type: "
                    f"{get_type_pretty_name(received_value)}"
                )
                logger.debug(f"[cyan]{out}[/cyan]", extra={"markup": True})
                result_test_case_system_out.append(out)
                if (
                    received_value_sanitized == expected_value
                    and received_value_type_sanitized == expected_value_type
                ):
                    out = f"Value:{received_value_sanitized} and Type:{received_value_type_sanitized} Matched for key {expected_key}"
                    result_test_case_system_out.append(out)
                    logger.debug(out)
                else:
                    if received_value_type_sanitized == expected_value_type:
                        err = (
                            f"Expected value does not match for key {expected_key}: - expected: {expected_value} - "
                            f"received: {received_value_sanitized} Types match:{received_value_type_sanitized}"
                        )
                        logger.error(
                            f'[red][bold]{expected_key}[/bold] --- "{received_value_sanitized}" != "{expected_value}" '
                            f"Types match:{received_value_type_sanitized}[/red]",
                            extra={"markup": True},
                        )
                    else:
                        # Types don't match, so values are not matching either,
                        # so it means that both do not match.
                        err = (
                            f"Expected value and type do not match for key {expected_key}: - expected: {expected_value} - "
                            f"received: {received_value_sanitized} expected type: {expected_value_type} "
                            f"received type: {received_value_type_sanitized}"
                        )
                        logger.error(
                            f'[red][bold]{expected_key}[/bold][red] --- "{received_value_sanitized}" != "{expected_value}"\n'
                            f' [bold]{expected_key}[/bold][red] --- Received value type: "{received_value_type_sanitized}" '
                            f'!= Expected value type: "{expected_value_type}"[/red]',
                            extra={"markup": True},
                        )
                    result_test_case_system_err.append(err)
                    result_test_case_results.append(Failure(err))
            else:
                err = f"No mapping for key {expected_key} - skipping checking match"
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
        result_test_case.result += result_test_case_results
    return result_test_case


def generate_xql_query(rule: SingleModelingRule, test_data_event_ids: List[str]) -> str:
    """Generate an XQL query from the given rule and test data event IDs.

    Args:
        rule (SingleModelingRule): Rule object parsed from the modeling rule file.
        test_data_event_ids (List[str]): List of test data event IDs to query.

    Returns:
        str: The XQL query.
    """
    fields = ", ".join(list(rule.fields))
    td_event_ids = ", ".join(
        [f'"{td_event_id}"' for td_event_id in test_data_event_ids]
    )
    return (
        f"config timeframe = 10y | datamodel dataset in({rule.dataset}) | "
        f"filter {rule.dataset}.test_data_event_id in({td_event_ids}) | "
        f"dedup {rule.dataset}.test_data_event_id by desc _insert_time | "
        f"fields {rule.dataset}.test_data_event_id, {fields}"
    )


def validate_expected_values(
    xsiam_client: XsiamApiClient,
    retrying_caller: Retrying,
    modeling_rule: ModelingRule,
    test_data: TestData,
) -> List[TestCase]:
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
            results = retrying_caller(xsiam_execute_query, xsiam_client, query)
        except requests.exceptions.RequestException:
            logger.error(
                f"[red]{XQL_QUERY_ERROR_EXPLANATION}[/red]",
                extra={"markup": True},
            )
            validate_expected_values_test_case.system_err = XQL_QUERY_ERROR_EXPLANATION
            validate_expected_values_test_case.result += [
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
    test_data: TestData,
    schema: Dict,
) -> Tuple[bool, List[Result]]:
    """
    Validates that the schema is aligned with the test-data types.

    Args:
        test_data: the test data object.
        schema: the content of the schema file.
    Returns:
        Tuple[bool, List[Result]]: if the schema is aligned with the test-data types and a list of the results.
    """

    # map each dataset from the schema to the correct events that has the same dataset
    schema_dataset_to_events = {
        dataset: [
            event_log for event_log in test_data.data if event_log.dataset == dataset
        ]
        for dataset in schema.keys()
    }

    errors_occurred = False
    results = []

    for dataset, event_logs in schema_dataset_to_events.items():
        all_schema_dataset_mappings = schema[dataset]
        test_data_mappings: Dict = {}
        error_logs = set()
        for event_log in event_logs:
            for event_key, event_val in event_log.event_data.items():
                if (
                    event_val is None
                ):  # if event_val is None, warn and continue looping.

                    info = f"{event_key=} is null on {event_log.test_data_event_id} event for {dataset=}, ignoring {event_key=}"
                    logger.warning(f"[yellow]{info}[/yellow]", extra={"markup": True})
                    results.append(Skipped(info))
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
                        err = (
                            f"The testdata contains events with the same {event_key=} "
                            f"that have different types for dataset {dataset}"
                        )
                        error_logs.add(err)
                        results.append(Error(err))
                        errors_occurred = True
                        continue
                    else:
                        test_data_mappings[event_key] = test_data_key_mappings

                    if test_data_key_mappings != schema_key_mappings:
                        err = (
                            f"The field {event_key} has mismatch on type or is_array in "
                            f"event ID {event_log.test_data_event_id} between testdata and schema --- "
                            f'TestData Mapping "{test_data_key_mappings}" != Schema Mapping "{schema_key_mappings}"'
                        )
                        results.append(Error(err))
                        error_logs.add(
                            f"[red][bold]the field {event_key} has mismatch on type or is_array in "
                            f"event ID {event_log.test_data_event_id} between testdata and schema[/bold][red] --- "
                            f'TestData Mapping "{test_data_key_mappings}" != Schema Mapping "{schema_key_mappings}"[/red]'
                        )
                        errors_occurred = True

        if missing_test_data_keys := set(all_schema_dataset_mappings.keys()) - set(
            test_data_mappings.keys()
        ):
            skipped = (
                f"The following fields {missing_test_data_keys} are in schema for dataset {dataset}, but not "
                "in test-data, make sure to remove them from the schema or add them to test-data if necessary"
            )
            logger.warning(f"[yellow]{skipped}[/yellow]", extra={"markup": True})
            results.append(Skipped(skipped))

        if error_logs:
            for _log in error_logs:
                logger.error(_log, extra={"markup": True})
        else:
            logger.info(
                f"[green]Schema type mappings = Testdata type mappings for dataset {dataset}[/green]",
                extra={"markup": True},
            )
    return not errors_occurred, results


def check_dataset_exists(
    xsiam_client: XsiamApiClient,
    retrying_caller: Retrying,
    dataset: str,
    init_sleep_time: int = 30,
    print_errors: bool = True,
) -> TestCase:
    """Check if the dataset in the test data file exists in the tenant.

    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        retrying_caller (tenacity.Retrying): The retrying caller object.
        dataset (str): The data set name.
        init_sleep_time (int, optional): The number of seconds to wait for dataset installation. Defaults to 30.
        print_errors (bool): Whether to print errors.
    Returns:
        TestCase: Test case for checking if the dataset exists in the tenant.
    """
    process_failed = False
    dataset_set_test_case = TestCase(
        "Check if dataset exists in tenant", classname="Check dataset exists"
    )
    dataset_set_test_case_start_time = datetime.now(timezone.utc)
    test_case_results = []
    logger.debug(
        f"Sleeping for {init_sleep_time} seconds before query for the dataset, to make sure the dataset was installed correctly."
    )
    sleep(init_sleep_time)
    start_time = datetime.now(tz=pytz.UTC)
    results_exist = False
    dataset_exist = False
    logger.info(
        f'[cyan]Checking if dataset "{dataset}" exists on the tenant...[/cyan]',
        extra={"markup": True},
    )
    query = f"config timeframe = 10y | dataset = {dataset}"
    try:
        results = retrying_caller(xsiam_execute_query, xsiam_client, query)

        dataset_exist = True
        if results:
            logger.info(
                f"[green]Dataset {dataset} exists[/green]",
                extra={"markup": True},
            )
            results_exist = True
    except requests.exceptions.RequestException:
        results = []

    # There are no results from the dataset, but it exists.
    if not results:
        err = (
            f"Dataset {dataset} exists but no results were returned. This could mean that your testdata "
            "does not meet the criteria for an associated Parsing Rule and is therefore being dropped from "
            "the dataset. Check to see if a Parsing Rule exists for your dataset and that your testdata "
            "meets the criteria for that rule."
        )
        test_case_results.append(Error(err))
        if print_errors:
            logger.error(f"[red]{err}[/red]", extra={"markup": True})
    if not dataset_exist:
        err = f"[red]Dataset {dataset} does not exist[/red]"
        test_case_results.append(Error(err))
        if print_errors:
            logger.error(f"[red]{err}[/red]", extra={"markup": True})

    duration = datetime.now(tz=pytz.UTC) - start_time
    logger.info(
        f"Processing Dataset {dataset} finished after {duration.total_seconds():.2f} seconds"
    )
    # OR statement between existence var and results of each data set, if at least one of dataset_exist or results_exist are False process_failed will be true.
    process_failed |= not (dataset_exist and results_exist)

    if test_case_results:
        dataset_set_test_case.result += test_case_results
    dataset_set_test_case.time = duration_since_start_time(
        dataset_set_test_case_start_time
    )
    return dataset_set_test_case


def push_test_data_to_tenant(
    xsiam_client: XsiamApiClient,
    retrying_caller: Retrying,
    mr: ModelingRule,
    test_data: TestData,
) -> TestCase:
    """Push the test data to the tenant.

    Args:
        retrying_caller (tenacity.Retrying): The retrying caller object.
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        test_data (init_test_data.TestData): Test data object parsed from the test data file.
    Returns:
        TestCase: Test case for pushing the test data to the tenant.
    """
    push_test_data_test_case = TestCase(
        f"Push test data to tenant {mr.path}",
        classname="Push test data to tenant",
    )
    push_test_data_test_case_start_time = datetime.now(timezone.utc)
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
            retrying_caller(xsiam_push_to_dataset, xsiam_client, events_test_data, rule)
        except requests.exceptions.RequestException:
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
        push_test_data_test_case.result += [Failure(FAILURE_TO_PUSH_EXPLANATION)]
    else:
        system_out = f"Test data pushed successfully for Modeling rule:{get_relative_path_to_content(mr.path)}"
        push_test_data_test_case.system_out = system_out
        logger.info(f"[green]{system_out}[/green]", extra={"markup": True})
    push_test_data_test_case.time = duration_since_start_time(
        push_test_data_test_case_start_time
    )
    return push_test_data_test_case


def verify_pack_exists_on_tenant(
    xsiam_client: XsiamApiClient,
    retrying_caller: Retrying,
    mr: ModelingRule,
    interactive: bool,
) -> bool:
    """Verify that the pack containing the modeling rule exists on the tenant.

    Args:
        retrying_caller (tenacity.Retrying): The retrying caller object.
        xsiam_client (XsiamApiClient): Xsiam API client.
        mr (ModelingRule): Modeling rule object parsed from the modeling rule file.
        interactive (bool): Whether command is being run in interactive mode.
    """
    logger.info(
        "[cyan]Verifying pack installed on tenant[/cyan]", extra={"markup": True}
    )
    containing_pack = get_containing_pack(mr)
    containing_pack_id = containing_pack.id
    installed_packs = retrying_caller(xsiam_get_installed_packs, xsiam_client)
    if found_pack := next(
        (pack for pack in installed_packs if containing_pack_id == pack.get("id")),
        None,
    ):
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
            if typer.confirm(
                f"Would you like to upload {containing_pack_id} to the tenant?"
            ):
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
                "[red]Pack does not exist on the tenant. Please install or upload the pack and try again[/red]",
                extra={"markup": True},
            )
            logger.info(
                f"\ndemisto-sdk upload -z -x -i {containing_pack.path}\ndemisto-sdk modeling-rules test {mr.path.parent}"
            )
            return False
    return True


def is_test_data_exists_on_server(
    test_data_path: Path,
) -> Tuple[List[UUID], List[UUID]]:
    """Verify that the test data exists and is valid.

    Args:
        test_data_path (Path): Path to the test data file.

    Returns:
        Tuple[List[str], List[str]]: Tuple of lists where the first list is test event
            first list: ids that do not have example event data.
            second list is test event ids that do not have expected_values to check.
    """
    missing_event_data, missing_expected_values_data = [], []
    test_data = TestData.parse_file(test_data_path)
    for event_log in test_data.data:
        if not event_log.event_data:
            missing_event_data.append(event_log.test_data_event_id)
        if all(val is None for val in event_log.expected_values.values()):
            missing_expected_values_data.append(event_log.test_data_event_id)
    return missing_event_data, missing_expected_values_data


def verify_event_id_does_not_exist_on_tenant(
    xsiam_client: XsiamApiClient,
    modeling_rule: ModelingRule,
    test_data: TestData,
    retrying_caller: Retrying,
) -> List[TestCase]:
    """
    Verify that the event ID does not exist on the tenant.
    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        modeling_rule (ModelingRule): Modeling rule object parsed from the modeling rule file.
        test_data (init_test_data.TestData): Test data object parsed from the test data file.
        retrying_caller (Retrying): The retrying caller object.
    """
    logger.info(
        "[cyan]Verifying that the event IDs does not exist on the tenant[/cyan]",
        extra={"markup": True},
    )
    success_msg = "[green]The event IDs does not exists on the tenant[/green]"
    error_msg = "The event id already exists in the tenant"
    validate_expected_values_test_cases = []

    for rule in modeling_rule.rules:
        validate_event_id_does_not_exist_on_tenant_test_case = TestCase(
            f"Validate event_id_does_not_exist_on_tenant {get_relative_path_to_content(modeling_rule.path)} dataset:{rule.dataset} "
            f"vendor:{rule.vendor} product:{rule.product}",
            classname="Validate event id does not exist query",
        )
        test_data_event_ids = [
            f'"{d.test_data_event_id}"'
            for d in test_data.data
            if d.dataset == rule.dataset
        ]
        td_event_ids = ", ".join(test_data_event_ids)
        query = f"config timeframe = 10y | datamodel dataset in({rule.dataset}) | filter {rule.dataset}.test_data_event_id in({td_event_ids})"

        try:
            result = retrying_caller(xsiam_execute_query, xsiam_client, query)
        except requests.exceptions.HTTPError:
            logger.info(
                success_msg,
                extra={"markup": True},
            )
        else:
            if not result:
                logger.info(
                    success_msg,
                    extra={"markup": True},
                )
            else:
                logger.error(
                    error_msg,
                    extra={"markup": True},
                )
                validate_event_id_does_not_exist_on_tenant_test_case.result += [
                    Error(error_msg)
                ]
        validate_expected_values_test_cases.append(
            validate_event_id_does_not_exist_on_tenant_test_case
        )

    return validate_expected_values_test_cases


def delete_dataset(
    xsiam_client: XsiamApiClient,
    dataset_name: str,
):
    logger.info(
        f"[cyan]Deleting existing {dataset_name} dataset[/cyan]",
        extra={"markup": True},
    )
    xsiam_client.delete_dataset(dataset_name)
    logger.info(
        f"[green]Dataset {dataset_name} deleted successfully[/green]",
        extra={"markup": True},
    )


def delete_existing_dataset_flow(
    xsiam_client: XsiamApiClient, test_data: TestData, retrying_caller: Retrying
) -> None:
    """
    Delete existing dataset if it exists in the tenant.
    Args:
        xsiam_client (XsiamApiClient): Xsiam API client.
        test_data (TestData): Test data object parsed from the test data file.
        retrying_caller (Retrying): The retrying caller object.
    """
    dataset_to_check = list(set([data.dataset for data in test_data.data]))
    for dataset in dataset_to_check:
        dataset_set_test_case = check_dataset_exists(
            xsiam_client, retrying_caller, dataset, print_errors=False
        )
        if dataset_set_test_case.is_passed:
            delete_dataset(xsiam_client, dataset)
        else:
            logger.info("[cyan]Dataset does not exists on tenant[/cyan]")


def verify_data_sets_exists(xsiam_client, retrying_caller, test_data):
    datasets_test_case_ls = []
    for dataset in test_data.data:
        dataset_name = dataset.dataset
        dataset_test_case = check_dataset_exists(
            xsiam_client, retrying_caller, dataset_name
        )
        datasets_test_case_ls.append(dataset_test_case)
    return datasets_test_case_ls


def validate_modeling_rule(
    modeling_rule_directory: Path,
    xsiam_url: str,
    retrying_caller: Retrying,
    push: bool,
    interactive: bool,
    ctx: typer.Context,
    delete_existing_dataset: bool,
    xsiam_client: XsiamApiClient,
    tenant_demisto_version: Version,
) -> Tuple[bool, Union[TestSuite, None]]:
    """Validate a modeling rule.

    Args:
        modeling_rule_directory (Path): Path to the modeling rule directory.
        retrying_caller (tenacity.Retrying): The retrying caller object.
        xsiam_url (str): URL of the xsiam tenant.
        push (bool): Whether to push test event data to the tenant.
        interactive (bool): Whether command is being run in interactive mode.
        ctx (typer.Context): Typer context.
        delete_existing_dataset (bool): Whether to delete the existing dataset in the tenant.
        xsiam_client (XsiamApiClient): The XSIAM client used to do API calls to the tenant.
        tenant_demisto_version (Version): The demisto version of the XSIAM tenant.
    """
    modeling_rule = ModelingRule(modeling_rule_directory.as_posix())
    modeling_rule_file_name = Path(modeling_rule.path).name
    containing_pack = get_containing_pack(modeling_rule)
    executed_command = (
        f"{ctx.command_path} {get_relative_path_to_content(modeling_rule_directory)}"
    )

    modeling_rule_test_suite = TestSuite(
        f"Modeling Rule Test Results {modeling_rule_file_name}"
    )
    modeling_rule_test_suite.add_property(
        "file_name", modeling_rule_file_name
    )  # used in the convert to jira issue.
    modeling_rule_test_suite.filepath = get_relative_path_to_content(modeling_rule.path)
    modeling_rule_test_suite.add_property(
        "modeling_rule_path", get_relative_path_to_content(modeling_rule.path)
    )
    modeling_rule_test_suite.add_property(
        "modeling_rule_file_name", modeling_rule_file_name
    )
    modeling_rule_test_suite.add_property(
        "test_data_path",
        get_relative_path_to_content(modeling_rule.testdata_path)
        if modeling_rule.testdata_path
        else NOT_AVAILABLE,
    )
    modeling_rule_test_suite.add_property(
        "schema_path", get_relative_path_to_content(modeling_rule.schema_path)
    )
    modeling_rule_test_suite.add_property("push", push)
    modeling_rule_test_suite.add_property("interactive", interactive)
    modeling_rule_test_suite.add_property("xsiam_url", xsiam_url)
    modeling_rule_test_suite.add_property("from_version", modeling_rule.from_version)
    modeling_rule_test_suite.add_property("to_version", modeling_rule.to_version)
    modeling_rule_test_suite.add_property(
        "pack_id", containing_pack.id
    )  # used in the convert to jira issue.
    if CI_PIPELINE_ID:
        modeling_rule_test_suite.add_property("ci_pipeline_id", CI_PIPELINE_ID)
    if modeling_rule.testdata_path:
        logger.info(
            f"[cyan]Test data file found at {get_relative_path_to_content(modeling_rule.testdata_path)}\n"
            f"Checking that event data was added to the test data file[/cyan]",
            extra={"markup": True},
        )
        test_data = TestData.parse_file(modeling_rule.testdata_path.as_posix())
        modeling_rule_is_compatible = validate_modeling_rule_version_against_tenant(
            to_version=modeling_rule.to_version,
            from_version=modeling_rule.from_version,
            tenant_demisto_version=tenant_demisto_version,
        )
        if not modeling_rule_is_compatible:
            # Modeling rule version is not compatible with the demisto version of the tenant, skipping
            skipped = f"XSIAM Tenant's Demisto version doesn't match Modeling Rule {modeling_rule} version, skipping"
            logger.warning(f"[yellow]{skipped}[/yellow]", extra={"markup": True})
            test_case = TestCase(
                "Modeling Rule not compatible with XSIAM tenant's demisto version",
                classname=f"Modeling Rule {modeling_rule_file_name}",
            )
            test_case.result += [Skipped(skipped)]
            modeling_rule_test_suite.add_testcase(test_case)
            # Return True since we don't want to fail the command
            return True, modeling_rule_test_suite
        if (
            Validations.TEST_DATA_CONFIG_IGNORE.value
            not in test_data.ignored_validations
        ):
            logger.info(
                "[green]test data config is not ignored starting the test data validation...[/green]",
                extra={"markup": True},
            )
            missing_event_data, _ = is_test_data_exists_on_server(
                modeling_rule.testdata_path
            )
            if not verify_pack_exists_on_tenant(
                xsiam_client, retrying_caller, modeling_rule, interactive
            ):
                test_case = TestCase(
                    "Pack not installed on tenant", classname="Modeling Rule"
                )
                return add_result_to_test_case(
                    "Pack not installed on tenant",
                    test_case,
                    modeling_rule_test_suite,
                )
            if delete_existing_dataset:
                delete_existing_dataset_flow(xsiam_client, test_data, retrying_caller)
            schema_test_case = TestCase(
                "Validate Schema",
                classname=f"Modeling Rule {get_relative_path_to_content(modeling_rule.schema_path)}",
            )
            if schema_path := modeling_rule.schema_path:
                try:
                    schema = get_file(schema_path)
                except json.JSONDecodeError as ex:
                    err = f"Failed to parse schema file {get_relative_path_to_content(modeling_rule.schema_path)} as JSON"
                    logger.error(
                        f"[red]{err}[/red]",
                        extra={"markup": True},
                    )
                    schema_test_case.system_err = str(ex)
                    return add_result_to_test_case(
                        err, schema_test_case, modeling_rule_test_suite
                    )
            else:
                err = f"Schema file does not exist in path {get_relative_path_to_content(modeling_rule.schema_path)}"
                return log_error_to_test_case(
                    err, schema_test_case, modeling_rule_test_suite
                )
            if (
                Validations.SCHEMA_TYPES_ALIGNED_WITH_TEST_DATA.value
                not in test_data.ignored_validations
            ):
                logger.info(
                    f"[green]Validating that the schema {get_relative_path_to_content(schema_path)} "
                    "is aligned with TestData file.[/green]",
                    extra={"markup": True},
                )

                success, results = validate_schema_aligned_with_test_data(
                    test_data=test_data, schema=schema
                )
                schema_test_case.result += results
                if not success:
                    err = (
                        f"The schema {get_relative_path_to_content(schema_path)} is not aligned with the test data file "
                        f"{get_relative_path_to_content(modeling_rule.testdata_path)}"
                    )
                    return log_error_to_test_case(
                        err, schema_test_case, modeling_rule_test_suite
                    )
            else:
                skipped = (
                    f"Skipping the validation to check that the schema {get_relative_path_to_content(schema_path)} "
                    "is aligned with TestData file."
                )
                logger.info(f"[green]{skipped}[/green]", extra={"markup": True})
                schema_test_case.result += [Skipped(skipped)]
                modeling_rule_test_suite.add_testcase(schema_test_case)

            if push:
                event_id_exists_test_case = verify_event_id_does_not_exist_on_tenant(
                    xsiam_client, modeling_rule, test_data, retrying_caller
                )
                modeling_rule_test_suite.add_testcases(event_id_exists_test_case)
                if missing_event_data:
                    return handle_missing_event_data_in_modeling_rule(
                        missing_event_data,
                        modeling_rule,
                        modeling_rule_test_suite,
                        executed_command,
                    )
                push_test_data_test_case = push_test_data_to_tenant(
                    xsiam_client, retrying_caller, modeling_rule, test_data
                )
                modeling_rule_test_suite.add_testcase(push_test_data_test_case)
                if not push_test_data_test_case.is_passed:
                    return False, modeling_rule_test_suite
                datasets_test_case = verify_data_sets_exists(
                    xsiam_client, retrying_caller, test_data
                )
                modeling_rule_test_suite.add_testcases(datasets_test_case)
            else:
                logger.info(
                    '[cyan]The command flag "--no-push" was passed - skipping pushing of test data[/cyan]',
                    extra={"markup": True},
                )
            logger.info(
                "[cyan]Validating expected_values...[/cyan]", extra={"markup": True}
            )
            validate_expected_values_test_cases = validate_expected_values(
                xsiam_client, retrying_caller, modeling_rule, test_data
            )
            modeling_rule_test_suite.add_testcases(validate_expected_values_test_cases)
            if (
                not modeling_rule_test_suite.errors
                and not modeling_rule_test_suite.failures
            ):
                logger.info(
                    "[green]All mappings validated successfully[/green]",
                    extra={"markup": True},
                )
                return True, modeling_rule_test_suite
            return False, modeling_rule_test_suite
        else:
            logger.info(
                "[green]test data config is ignored skipping the test data validation[/green]",
                extra={"markup": True},
            )
            return True, modeling_rule_test_suite
    else:
        logger.warning(
            f"[yellow]No test data file found for {get_relative_path_to_content(modeling_rule_directory)}[/yellow]",
            extra={"markup": True},
        )
        if interactive:
            if typer.confirm(
                f"Would you like to generate a test data file for {get_relative_path_to_content(modeling_rule_directory)}?"
            ):
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
                        f"[green]Test data file generated for "
                        f"{get_relative_path_to_content(modeling_rule_directory)}"
                        f"Please complete the test data file at {get_relative_path_to_content(modeling_rule.testdata_path)} "
                        f"with test event(s) data and expected outputs and then run:\n[bold]{executed_command}[/bold][/green]",
                        extra={"markup": True},
                    )
                    return True, None
                logger.error(
                    f"[red]Failed to generate test data file for "
                    f"{get_relative_path_to_content(modeling_rule_directory)}[/red]",
                    extra={"markup": True},
                )
            else:
                logger.warning(
                    f"[yellow]Skipping test data file generation for "
                    f"{get_relative_path_to_content(modeling_rule_directory)}[/yellow]",
                    extra={"markup": True},
                )
                logger.error(
                    f"[red]Please create a test data file for "
                    f"{get_relative_path_to_content(modeling_rule_directory)} and then rerun\n{executed_command}[/red]",
                    extra={"markup": True},
                )
        else:
            err = (
                f"Please create a test data file for {get_relative_path_to_content(modeling_rule_directory)} "
                f"and then rerun\n{executed_command}"
            )
            logger.error(
                f"[red]{err}[/red]",
                extra={"markup": True},
            )
            test_data_test_case = TestCase(
                "Test data file does not exist",
                classname=f"Modeling Rule {get_relative_path_to_content(modeling_rule.schema_path)}",
            )
            test_data_test_case.result += [Error(err)]
            modeling_rule_test_suite.add_testcase(test_data_test_case)
            return False, modeling_rule_test_suite
        return False, None


def validate_modeling_rule_version_against_tenant(
    to_version: Version, from_version: Version, tenant_demisto_version: Version
) -> bool:
    """Checks if the version of the modeling rule is compatible with the XSIAM tenant's demisto version.
    Compatibility is checked by: from_version <= tenant_xsiam_version <= to_version

    Args:
        to_version (Version): The to version of the modeling rule
        from_version (Version): The from version of the modeling rule
        tenant_demisto_version (Version): The demisto version of the XSIAM tenant

    Returns:
        bool: True if the version of the modeling rule is compatible, else False
    """
    return (
        tenant_demisto_version >= from_version and tenant_demisto_version <= to_version
    )


def handle_missing_event_data_in_modeling_rule(
    missing_event_data: List[UUID],
    modeling_rule: ModelingRule,
    modeling_rule_test_suite: TestSuite,
    executed_command: str,
) -> Tuple[bool, TestSuite]:
    """Handle missing event data in the modeling rule.
    Args:
        missing_event_data (List[UUID]): List of event ids that do not have example event data.
        modeling_rule (ModelingRule): Modeling rule object parsed from the modeling rule file.
        modeling_rule_test_suite (TestSuite): Test suite for the modeling rule.
        executed_command (str): The executed command.
    Returns:
        Tuple[bool, TestSuite]: Tuple of a boolean indicating whether the test passed and the test suite.
    """
    missing_event_data_test_case = TestCase(
        "Missing Event Data", classname="Modeling Rule"
    )
    err = f"Missing Event Data for the following test data event ids: {missing_event_data}"
    missing_event_data_test_case.result += [Error(err)]
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
        system_errors.append(str(test_data_event_id))
    suffix = (
        f"Please complete the test data file at {get_relative_path_to_content(modeling_rule.testdata_path)} "
        f"with test event(s) data and expected outputs and then rerun"
    )
    logger.warning(
        f"[yellow]{suffix}[/yellow]\n[bold][yellow]{executed_command}[/yellow][/bold]",
        extra={"markup": True},
    )
    system_errors.extend([suffix, executed_command])
    missing_event_data_test_case.system_err = "\n".join(system_errors)
    modeling_rule_test_suite.add_testcase(missing_event_data_test_case)

    return False, modeling_rule_test_suite


def log_error_to_test_case(
    err: str, schema_test_case: TestCase, modeling_rule_test_suite: TestSuite
) -> Tuple[bool, TestSuite]:
    logger.error(
        f"[red]{err}[/red]",
        extra={"markup": True},
    )
    schema_test_case.system_err = err
    return add_result_to_test_case(err, schema_test_case, modeling_rule_test_suite)


def add_result_to_test_case(
    err: str, test_case: TestCase, modeling_rule_test_suite: TestSuite
) -> Tuple[bool, TestSuite]:
    test_case.result += [Error(err)]
    modeling_rule_test_suite.add_testcase(test_case)
    return False, modeling_rule_test_suite


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
    sleep_interval: int = typer.Option(
        XSIAM_CLIENT_SLEEP_INTERVAL,
        "-si",
        "--sleep_interval",
        min=0,
        show_default=True,
        help="The number of seconds to wait between requests to the server.",
    ),
    retry_attempts: int = typer.Option(
        XSIAM_CLIENT_RETRY_ATTEMPTS,
        "-ra",
        "--retry_attempts",
        min=0,
        show_default=True,
        help="The number of times to retry the request against the server.",
    ),
    delete_existing_dataset: bool = typer.Option(
        False,
        "--delete_existing_dataset",
        "-dd",
        help="Deletion of the existing dataset from the tenant. Default: False.",
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "-lp",
        "--log-file-path",
        help="Path to save log files onto.",
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
        "[cyan]Test Modeling Rules directories to test:[/cyan]",
        extra={"markup": True},
    )

    for modeling_rule_directory in inputs:
        logger.info(
            f"[cyan]\t{get_relative_path_to_content(modeling_rule_directory)}[/cyan]",
            extra={"markup": True},
        )

    retrying_caller = create_retrying_caller(retry_attempts, sleep_interval)

    errors = False
    xml = JUnitXml()
    start_time = datetime.now(timezone.utc)
    # initialize xsiam client
    xsiam_client_cfg = XsiamApiClientConfig(
        base_url=xsiam_url,  # type: ignore[arg-type]
        api_key=api_key,  # type: ignore[arg-type]
        auth_id=auth_id,  # type: ignore[arg-type]
        token=xsiam_token,  # type: ignore[arg-type]
        collector_token=collector_token,  # type: ignore[arg-type]
    )
    xsiam_client = XsiamApiClient(xsiam_client_cfg)
    tenant_demisto_version: Version = xsiam_client.get_demisto_version()
    for i, modeling_rule_directory in enumerate(inputs, start=1):
        logger.info(
            f"[cyan][{i}/{len(inputs)}] Test Modeling Rule: {get_relative_path_to_content(modeling_rule_directory)}[/cyan]",
            extra={"markup": True},
        )
        success, modeling_rule_test_suite = validate_modeling_rule(
            modeling_rule_directory,
            # can ignore the types since if they are not set to str values an error occurs
            xsiam_url,  # type: ignore[arg-type]
            retrying_caller,
            push,
            interactive,
            ctx,
            delete_existing_dataset,
            xsiam_client=xsiam_client,
            tenant_demisto_version=tenant_demisto_version,
        )
        if success:
            logger.info(
                f"[green]Test Modeling rule {get_relative_path_to_content(modeling_rule_directory)} passed[/green]",
                extra={"markup": True},
            )
        else:
            errors = True
            logger.error(
                f"[red]Test Modeling Rule {get_relative_path_to_content(modeling_rule_directory)} failed[/red]",
                extra={"markup": True},
            )
        if modeling_rule_test_suite:
            modeling_rule_test_suite.add_property("start_time", start_time)
            xml.add_testsuite(modeling_rule_test_suite)

    if output_junit_file:
        logger.info(
            f"[cyan]Writing JUnit XML to {get_relative_path_to_content(output_junit_file)}[/cyan]",
            extra={"markup": True},
        )
        xml.write(output_junit_file.as_posix(), pretty=True)
    else:
        logger.info(
            "[cyan]No JUnit XML file path was passed - skipping writing JUnit XML[/cyan]",
            extra={"markup": True},
        )

    duration = duration_since_start_time(start_time)
    if errors:
        logger.info(
            f"[red]Test Modeling Rules: Failed, took:{duration} seconds[/red]",
            extra={"markup": True},
        )
        raise typer.Exit(1)
    logger.info(
        f"[green]Test Modeling Rules: Passed, took:{duration} seconds[/green]",
        extra={"markup": True},
    )


if __name__ == "__main__":
    app()
