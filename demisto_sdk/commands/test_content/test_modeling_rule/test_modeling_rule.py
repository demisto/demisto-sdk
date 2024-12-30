import logging  # noqa: TID251 # specific case, passed as argument to 3rd party
import os
from datetime import datetime
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import dateparser
import demisto_client
import pytz
import requests
import typer
from google.cloud import storage  # type: ignore[attr-defined]
from junitparser import Error, JUnitXml, TestCase, TestSuite
from junitparser.junitparser import Failure, Result, Skipped
from packaging.version import Version
from tabulate import tabulate
from tenacity import (
    Retrying,
)
from typer.main import get_command_from_info

from demisto_sdk.commands.common.constants import (
    TEST_MODELING_RULES,
    XSIAM_SERVER_TYPE,
)
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
    ModelingRule,
    SingleModelingRule,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.common.tools import (
    get_file,
    get_json_file,
    is_epoch_datetime,
    string_to_bool,
)
from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.test_modeling_rule.constants import (
    EXPECTED_SCHEMA_MAPPINGS,
    FAILURE_TO_PUSH_EXPLANATION,
    NOT_AVAILABLE,
    SYNTAX_ERROR_IN_MODELING_RULE,
    TIME_ZONE_WARNING,
    XQL_QUERY_ERROR_EXPLANATION,
)
from demisto_sdk.commands.test_content.tools import (
    XSIAM_CLIENT_RETRY_ATTEMPTS,
    XSIAM_CLIENT_SLEEP_INTERVAL,
    create_retrying_caller,
    day_suffix,
    duration_since_start_time,
    get_relative_path_to_content,
    get_type_pretty_name,
    get_ui_url,
    get_utc_now,
    logs_token_cb,
    tenant_config_cb,
    xsiam_get_installed_packs,
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


app = typer.Typer()


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
        tablefmt="grid",
        headers=["Model Field", "Expected Value", "Received Value"],
        colalign=("left", "left", "left"),
    )


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


def xsiam_execute_query(xsiam_client: XsiamApiClient, query: str) -> List[dict]:
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
            f"<red>{SYNTAX_ERROR_IN_MODELING_RULE}</red>",
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
        logger.error(
            f"<red>{err}</red>",
        )
        return [test_case]

    test_cases = []
    for i, result in enumerate(results, start=1):
        td_event_id = result.pop(f"{tested_dataset}.test_data_event_id")
        msg = (
            f"Modeling rule - {get_relative_path_to_content(modeling_rule.path)} {i}/{len(results)}"
            f" test_data_event_id:{td_event_id}"
        )
        logger.info("{}", f"<cyan>{msg}</cyan>")  # noqa: PLE1205
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
        logger.warning(f"<yellow>{TIME_ZONE_WARNING}</yellow>")
    if expected_values:
        if (
            expected_time_value := expected_values.get(SingleModelingRule.TIME_FIELD)
        ) and (time_value := result.get(SingleModelingRule.TIME_FIELD)):
            result[SingleModelingRule.TIME_FIELD] = convert_epoch_time_to_string_time(
                time_value, "." in expected_time_value, tenant_timezone
            )
        table_result = create_table(expected_values, result)
        logger.info("{}", f"\n{table_result}")  # noqa: PLE1205
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
                logger.debug("{}", f"<cyan>{out}</cyan>")  # noqa: PLE1205
                result_test_case_system_out.append(out)
                if (
                    received_value_sanitized == expected_value
                    and received_value_type_sanitized == expected_value_type
                ):
                    out = f"Value:{received_value_sanitized} and Type:{received_value_type_sanitized} Matched for key {expected_key}"
                    result_test_case_system_out.append(out)
                    logger.debug("{}", out)  # noqa: PLE1205
                else:
                    if received_value_type_sanitized == expected_value_type:
                        err = (
                            f"Expected value does not match for key {expected_key}: - expected: {expected_value} - "
                            f"received: {received_value_sanitized} Types match:{received_value_type_sanitized}"
                        )
                        logger.error(  # noqa: PLE1205
                            "{}",
                            f'<red><bold>{expected_key}</bold> --- "{received_value_sanitized}" != "{expected_value}" '
                            f"Types match:{received_value_type_sanitized}</red>",
                        )
                    else:
                        # Types don't match, so values are not matching either,
                        # so it means that both do not match.
                        err = (
                            f"Expected value and type do not match for key {expected_key}: - expected: {expected_value} - "
                            f"received: {received_value_sanitized} expected type: {expected_value_type} "
                            f"received type: {received_value_type_sanitized}"
                        )
                        logger.error(  # noqa: PLE1205
                            "{}",
                            f'<red><bold>{expected_key}</bold><red> --- "{received_value_sanitized}" != "{expected_value}"\n'
                            f' <bold>{expected_key}</bold><red> --- Received value type: "{received_value_type_sanitized}" '
                            f'!= Expected value type: "{expected_value_type}"</red>',
                        )
                    result_test_case_system_err.append(err)
                    result_test_case_results.append(Failure(err))
            else:
                err = f"No mapping for key {expected_key} - skipping checking match"
                result_test_case_system_out.append(err)
                result_test_case_results.append(Skipped(err))  # type:ignore[arg-type]
                logger.debug(  # noqa: PLE1205
                    "{}",
                    f"<cyan>{err}</cyan>",
                )
    else:
        err = f"No matching expected_values found for test_data_event_id={td_event_id} in test_data {test_data}"
        logger.error("{}", f"<red>{err}</red>")  # noqa: PLE1205
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
        logger.debug("{}", query_info)  # noqa: PLE1205
        validate_expected_values_test_case_system_out = [query_info]
        try:
            results = retrying_caller(xsiam_execute_query, xsiam_client, query)
        except requests.exceptions.RequestException:
            logger.error(
                f"<red>{XQL_QUERY_ERROR_EXPLANATION}</red>",
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
    results: List[Result] = []

    for dataset, event_logs in schema_dataset_to_events.items():
        all_schema_dataset_mappings = schema[dataset]
        test_data_mappings: Dict = {}
        error_logs = set()
        for event_log in event_logs:
            for (
                event_key,
                event_val,
            ) in event_log.event_data.items():  # type:ignore[union-attr]
                if (
                    event_val is None
                ):  # if event_val is None, warn and continue looping.
                    info = f"{event_key=} is null on {event_log.test_data_event_id} event for {dataset=}, ignoring {event_key=}"
                    logger.warning("{}", f"<yellow>{info}</yellow>")  # noqa: PLE1205
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
                        results.append(Error(err))  # type:ignore[arg-type]
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
                        results.append(Error(err))  # type:ignore[arg-type]
                        error_logs.add(
                            f"<red><bold>the field {event_key} has mismatch on type or is_array in "
                            f"event ID {event_log.test_data_event_id} between testdata and schema</bold><red> --- "
                            f'TestData Mapping "{test_data_key_mappings}" != Schema Mapping "{schema_key_mappings}"</red>'
                        )
                        errors_occurred = True

        if missing_test_data_keys := set(all_schema_dataset_mappings.keys()) - set(
            test_data_mappings.keys()
        ):
            skipped = (
                f"The following fields {missing_test_data_keys} are in schema for dataset {dataset}, but not "
                "in test-data, make sure to remove them from the schema or add them to test-data if necessary"
            )
            logger.warning(f"<yellow>{skipped}</yellow>")
            results.append(Skipped(skipped))

        if error_logs:
            for _log in error_logs:
                logger.error("{}", _log)  # noqa: PLE1205
        else:
            logger.info(
                f"<green>Schema type mappings = Testdata type mappings for dataset {dataset}</green>",
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
    dataset_set_test_case_start_time = get_utc_now()
    test_case_results = []
    logger.debug(
        f"Sleeping for {init_sleep_time} seconds before query for the dataset, to make sure the dataset was installed correctly."
    )
    sleep(init_sleep_time)
    start_time = get_utc_now()
    results_exist = False
    dataset_exist = False
    logger.info(
        f'<cyan>Checking if dataset "{dataset}" exists on the tenant...</cyan>',
    )
    query = f"config timeframe = 10y | dataset = {dataset}"
    try:
        results = retrying_caller(xsiam_execute_query, xsiam_client, query)

        dataset_exist = True
        if results:
            logger.info(
                f"<green>Dataset {dataset} exists</green>",
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
            logger.error("<red>{}</red>", err)  # noqa: PLE1205
    if not dataset_exist:
        err = f"Dataset {dataset} does not exist"
        test_case_results.append(Error(err))
        if print_errors:
            logger.error("<red>{}</red>", err)  # noqa: PLE1205

    duration = duration_since_start_time(start_time)
    logger.info(f"Processing Dataset {dataset} finished after {duration:.2f} seconds")
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
    push_test_data_test_case_start_time = get_utc_now()
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
        logger.info(f"<cyan>Pushing test data for {rule.dataset} to tenant...</cyan>")
        try:
            retrying_caller(xsiam_push_to_dataset, xsiam_client, events_test_data, rule)
        except requests.exceptions.RequestException:
            system_err = (
                f"Failed pushing test data to tenant for dataset {rule.dataset}"
            )
            system_errors.append(system_err)
            logger.error(
                f"<red>{system_err}</red>",
            )

    if system_errors:
        logger.error(f"<red>{FAILURE_TO_PUSH_EXPLANATION}</red>")
        push_test_data_test_case.system_err = "\n".join(system_errors)
        push_test_data_test_case.result += [Failure(FAILURE_TO_PUSH_EXPLANATION)]
    else:
        system_out = f"Test data pushed successfully for Modeling rule:{get_relative_path_to_content(mr.path)}"
        push_test_data_test_case.system_out = system_out
        logger.info(
            f"<green>{system_out}</green>",
        )
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
        "<cyan>Verifying pack installed on tenant</cyan>",
    )
    containing_pack = get_containing_pack(mr)
    containing_pack_id = containing_pack.id
    installed_packs = retrying_caller(xsiam_get_installed_packs, xsiam_client)
    if found_pack := next(
        (pack for pack in installed_packs if containing_pack_id == pack.get("id")),
        None,
    ):
        logger.debug(f"<cyan>Found pack on tenant:\n{found_pack}</cyan>")
    else:
        logger.error(f"<red>Pack {containing_pack_id} was not found on tenant</red>")

        upload_result = 0
        if interactive:
            if typer.confirm(
                f"Would you like to upload {containing_pack_id} to the tenant?"
            ):
                logger.info(
                    f'<cyan><underline>Upload "{containing_pack_id}"</underline></cyan>'
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
                        f"Failed to upload pack {containing_pack_id} to tenant"
                    )
                # wait for pack to finish installing
                sleep(1)
            else:
                upload_result = 1
        if not interactive or upload_result != 0:
            logger.error(
                "Pack does not exist on the tenant. Please install or upload the pack and try again"
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
        "<cyan>Verifying that the event IDs does not exist on the tenant</cyan>"
    )
    success_msg = "The event IDs does not exists on the tenant"
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
            logger.info("<green>{}</green>", success_msg)  # noqa: PLE1205
        else:
            if not result:
                logger.info("<green>{}</green>", success_msg)  # noqa: PLE1205
            else:
                logger.error("{}", error_msg)  # noqa: PLE1205
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
        f"<cyan>Deleting existing {dataset_name} dataset</cyan>",
    )
    xsiam_client.delete_dataset(dataset_name)
    logger.info(
        f"<green>Dataset {dataset_name} deleted successfully</green>",
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
            logger.info("<cyan>Dataset does not exists on tenant</cyan>")


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
    is_nightly: bool,
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
        is_nightly (bool): Whether the command is being run in nightly mode.
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
    modeling_rule_test_suite.filepath = get_relative_path_to_content(  # type:ignore[arg-type]
        modeling_rule.path
    )
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
        "schema_path",
        get_relative_path_to_content(
            modeling_rule.schema_path  # type:ignore[arg-type]
        ),
    )
    modeling_rule_test_suite.add_property("push", push)  # type:ignore[arg-type]
    modeling_rule_test_suite.add_property(
        "interactive",
        interactive,  # type:ignore[arg-type]
    )
    modeling_rule_test_suite.add_property("xsiam_url", xsiam_url)
    modeling_rule_test_suite.add_property(
        "from_version",
        modeling_rule.from_version,  # type:ignore[arg-type]
    )  #
    modeling_rule_test_suite.add_property(
        "to_version",
        modeling_rule.to_version,  # type:ignore[arg-type]
    )  #
    modeling_rule_test_suite.add_property(
        "pack_id", containing_pack.id
    )  # used in the convert to jira issue.
    if CI_PIPELINE_ID:
        modeling_rule_test_suite.add_property("ci_pipeline_id", CI_PIPELINE_ID)
    if modeling_rule.testdata_path:
        logger.info(
            f"<cyan>Test data file found at {get_relative_path_to_content(modeling_rule.testdata_path)}\n"
            f"Checking that event data was added to the test data file</cyan>",
        )
        try:
            test_data = TestData.parse_file(modeling_rule.testdata_path.as_posix())
        except ValueError as ex:
            err = f"Failed to parse test data file {get_relative_path_to_content(modeling_rule.testdata_path)} as JSON"
            logger.error(
                f"<red>{err}</red>",
            )
            test_case = TestCase(
                "Failed to parse test data file as JSON",
                classname="Modeling Rule",
            )
            test_case.system_err = str(ex)
            test_case.result += [Error(err)]
            modeling_rule_test_suite.add_testcase(test_case)
            return False, modeling_rule_test_suite

        modeling_rule_is_compatible = validate_modeling_rule_version_against_tenant(
            to_version=modeling_rule.to_version,
            from_version=modeling_rule.from_version,
            tenant_demisto_version=tenant_demisto_version,
        )
        if not modeling_rule_is_compatible:
            # Modeling rule version is not compatible with the demisto version of the tenant, skipping
            skipped = f"XSIAM Tenant's Demisto version doesn't match Modeling Rule {modeling_rule} version, skipping"
            logger.warning(
                f"<yellow>{skipped}</yellow>",
            )
            test_case = TestCase(
                "Modeling Rule not compatible with XSIAM tenant's demisto version",
                classname=f"Modeling Rule {modeling_rule_file_name}",
            )
            test_case.result += [Skipped(skipped)]  # type:ignore[arg-type]
            modeling_rule_test_suite.add_testcase(test_case)
            # Return True since we don't want to fail the command
            return True, modeling_rule_test_suite
        if (
            Validations.TEST_DATA_CONFIG_IGNORE.value
            not in test_data.ignored_validations
        ):
            logger.info(
                "<green>test data config is not ignored starting the test data validation...</green>",
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
                classname=f"Modeling Rule {get_relative_path_to_content(modeling_rule.schema_path)}",  # type:ignore[arg-type]
            )
            if schema_path := modeling_rule.schema_path:
                try:
                    schema = get_file(schema_path)
                except json.JSONDecodeError as ex:
                    err = f"Failed to parse schema file {get_relative_path_to_content(modeling_rule.schema_path)} as JSON"
                    logger.error(err)
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
                    f"<green>Validating that the schema {get_relative_path_to_content(schema_path)} "
                    "is aligned with TestData file.</green>",
                )

                success, results = validate_schema_aligned_with_test_data(
                    test_data=test_data,
                    schema=schema,  # type:ignore[arg-type]
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
                logger.info(
                    f"<green>{skipped}</green>",
                )
                schema_test_case.result += [Skipped(skipped)]  # type:ignore[arg-type]
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
                    '<cyan>The command flag "--no-push" was passed - skipping pushing of test data</cyan>',
                )
            logger.info(
                "<cyan>Validating expected_values...</cyan>",
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
                    "<green>All mappings validated successfully</green>",
                )
                return True, modeling_rule_test_suite
            return False, modeling_rule_test_suite
        else:
            logger.info(
                "<green>test data config is ignored skipping the test data validation</green>",
            )
            return True, modeling_rule_test_suite
    else:
        logger.warning(
            f"<yellow>No test data file found for {get_relative_path_to_content(modeling_rule_directory)}</yellow>",
        )
        if interactive:
            if typer.confirm(
                f"Would you like to generate a test data file for {get_relative_path_to_content(modeling_rule_directory)}?"
            ):
                logger.info(
                    "<cyan><underline>Generate Test Data File</underline></cyan>",
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
                        '<red>Failed to load the "init-test-data" typer application to interactively create a '
                        "testdata file.</red>"
                    )
                    logger.error(
                        err,
                    )
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
                        f"<green>Test data file generated for "
                        f"{get_relative_path_to_content(modeling_rule_directory)}"
                        f"Please complete the test data file at {get_relative_path_to_content(modeling_rule.testdata_path)} "
                        f"with test event(s) data and expected outputs and then run:\n<bold>{executed_command}</bold></green>",
                    )
                    return True, None
                logger.error(
                    f"<red>Failed to generate test data file for "
                    f"{get_relative_path_to_content(modeling_rule_directory)}</red>",
                )
            else:
                logger.warning(
                    f"<yellow>Skipping test data file generation for "
                    f"{get_relative_path_to_content(modeling_rule_directory)}</yellow>",
                )
                logger.error(
                    f"<red>Please create a test data file for "
                    f"{get_relative_path_to_content(modeling_rule_directory)} and then rerun\n{executed_command}</red>",
                )
        else:
            if is_nightly:
                # Running in nightly mode, don't fail the test if no test data file is found.
                err = f"No test data file for {get_relative_path_to_content(modeling_rule_directory)} found. "
                logger.warning(
                    f"<red>{err}</red>",
                )
                test_data_test_case = TestCase(
                    "Test data file does not exist",
                    classname=f"Modeling Rule {get_relative_path_to_content(modeling_rule.schema_path)}",  # type:ignore[arg-type]
                )
                test_data_test_case.result += [Skipped(err)]  # type:ignore[arg-type]
                modeling_rule_test_suite.add_testcase(test_data_test_case)
                return True, modeling_rule_test_suite

            # Not running in nightly mode, fail the test if no test data file is found.
            err = (
                f"Please create a test data file for {get_relative_path_to_content(modeling_rule_directory)} "
                f"and then rerun\n{executed_command}"
            )
            logger.error(
                f"<red>{err}</red>",
            )
            test_data_test_case = TestCase(
                "Test data file does not exist",
                classname=f"Modeling Rule {get_relative_path_to_content(modeling_rule.schema_path)}",  # type:ignore[arg-type]
            )
            test_data_test_case.result += [Error(err)]  # type:ignore[arg-type]
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
    return from_version <= tenant_demisto_version <= to_version


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
    missing_event_data_test_case.result += [Error(err)]  # type:ignore[arg-type]
    prefix = "Event log test data is missing for the following ids:"
    system_errors = [prefix]
    logger.warning(
        f"<yellow>{prefix}</yellow>",
    )
    for test_data_event_id in missing_event_data:
        logger.warning(
            f"<yellow> - {test_data_event_id}</yellow>",
        )
        system_errors.append(str(test_data_event_id))
    suffix = (
        f"Please complete the test data file at {get_relative_path_to_content(modeling_rule.testdata_path)} "  # type:ignore[arg-type]
        f"with test event(s) data and expected outputs and then rerun"
    )
    logger.warning(
        f"<yellow>{suffix}</yellow>\n<bold><yellow>{executed_command}</yellow></bold>",
    )
    system_errors.extend([suffix, executed_command])
    missing_event_data_test_case.system_err = "\n".join(system_errors)
    modeling_rule_test_suite.add_testcase(missing_event_data_test_case)

    return False, modeling_rule_test_suite


def log_error_to_test_case(
    err: str, schema_test_case: TestCase, modeling_rule_test_suite: TestSuite
) -> Tuple[bool, TestSuite]:
    logger.error(
        f"<red>{err}</red>",
    )
    schema_test_case.system_err = err
    return add_result_to_test_case(err, schema_test_case, modeling_rule_test_suite)


def add_result_to_test_case(
    err: str, test_case: TestCase, modeling_rule_test_suite: TestSuite
) -> Tuple[bool, TestSuite]:
    test_case.result += [Error(err)]  # type:ignore[arg-type]
    modeling_rule_test_suite.add_testcase(test_case)
    return False, modeling_rule_test_suite


# ====================== test-modeling-rule ====================== #


class TestResults:
    def __init__(
        self,
        service_account: str = None,
        artifacts_bucket: str = None,
    ):
        self.test_results_xml_file = JUnitXml()
        self.errors = False
        self.service_account = service_account
        self.artifacts_bucket = artifacts_bucket

    def upload_modeling_rules_result_json_to_bucket(
        self,
        repository_name: str,
        file_name,
        original_file_path: Path,
        logging_module: Union[Any, ParallelLoggingManager] = logging,
    ):
        """Uploads a JSON object to a specified path in the GCP bucket.

        Args:
          original_file_path: The path to the JSON file to upload.
          repository_name: The name of the repository within the bucket.
          file_name: The desired filename for the uploaded JSON data.
          logging_module: Logging module to use for upload_modeling_rules_result_json_to_bucket.
        """
        logging_module.info("Start uploading modeling rules results file to bucket")

        storage_client = storage.Client.from_service_account_json(self.service_account)
        storage_bucket = storage_client.bucket(self.artifacts_bucket)

        blob = storage_bucket.blob(
            f"content-test-modeling-rules/{repository_name}/{file_name}"
        )
        blob.upload_from_filename(
            original_file_path.as_posix(),
            content_type="application/xml",
        )

        logging_module.info("Finished uploading modeling rules results file to bucket")


class BuildContext:
    def __init__(
        self,
        nightly: bool,
        build_number: Optional[str],
        branch_name: Optional[str],
        retry_attempts: int,
        sleep_interval: int,
        logging_module: ParallelLoggingManager,
        cloud_servers_path: str,
        cloud_servers_api_keys: str,
        service_account: Optional[str],
        artifacts_bucket: Optional[str],
        xsiam_url: Optional[str],
        xsiam_token: Optional[str],
        api_key: Optional[str],
        auth_id: Optional[str],
        collector_token: Optional[str],
        inputs: Optional[List[Path]],
        machine_assignment: str,
        push: bool,
        interactive: bool,
        delete_existing_dataset: bool,
        ctx: typer.Context,
    ):
        self.logging_module: ParallelLoggingManager = logging_module
        self.retrying_caller = create_retrying_caller(retry_attempts, sleep_interval)
        self.ctx = ctx

        # --------------------------- overall build configuration -------------------------------
        self.is_nightly = nightly
        self.build_number = build_number
        self.build_name = branch_name

        # -------------------------- Manual run on a single instance --------------------------
        self.xsiam_url = xsiam_url
        self.xsiam_token = xsiam_token
        self.api_key = api_key
        self.auth_id = auth_id
        self.collector_token = collector_token
        self.inputs = inputs

        # --------------------------- Pushing data settings -------------------------------

        self.push = push
        self.interactive = interactive
        self.delete_existing_dataset = delete_existing_dataset

        # --------------------------- Machine preparation -------------------------------

        self.cloud_servers_path_json = get_json_file(cloud_servers_path)
        self.cloud_servers_api_keys_json = get_json_file(cloud_servers_api_keys)
        self.machine_assignment_json = get_json_file(machine_assignment)

        # --------------------------- Testing preparation -------------------------------

        self.tests_data_keeper = TestResults(
            service_account,
            artifacts_bucket,
        )

        # --------------------------- Machine preparation logic -------------------------------

        self.servers = self.create_servers()

    @staticmethod
    def prefix_with_packs(path_str: Union[str, Path]) -> Path:
        path = Path(path_str)
        if path.parts[0] == "Packs":
            return path
        return Path("Packs") / path

    def create_servers(self):
        """
        Create servers object based on build type.
        """
        # If xsiam_url is provided we assume it's a run on a single server.
        if self.xsiam_url:
            return [
                CloudServerContext(
                    self,
                    base_url=self.xsiam_url,
                    api_key=self.api_key,  # type: ignore[arg-type]
                    auth_id=self.auth_id,  # type: ignore[arg-type]
                    token=self.xsiam_token,  # type: ignore[arg-type]
                    collector_token=self.collector_token,
                    ui_url=get_ui_url(self.xsiam_url),
                    tests=[BuildContext.prefix_with_packs(test) for test in self.inputs]
                    if self.inputs
                    else [],
                )
            ]
        servers_list = []
        for machine, assignment in self.machine_assignment_json.items():
            tests = [
                BuildContext.prefix_with_packs(test)
                for test in assignment.get("tests", {}).get(TEST_MODELING_RULES, [])
            ]
            if not tests:
                logger.info(f"No modeling rules found for machine {machine}")
                continue
            servers_list.append(
                CloudServerContext(
                    self,
                    base_url=self.cloud_servers_path_json.get(machine, {}).get(
                        "base_url", ""
                    ),
                    ui_url=self.cloud_servers_path_json.get(machine, {}).get(
                        "ui_url", ""
                    ),
                    tests=tests,
                    api_key=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "api-key"
                    ),
                    auth_id=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "x-xdr-auth-id"
                    ),
                    token=self.cloud_servers_api_keys_json.get(machine, {}).get(
                        "token"
                    ),
                )
            )
        return servers_list


class CloudServerContext:
    def __init__(
        self,
        build_context: BuildContext,
        base_url: str,
        api_key: str,
        auth_id: str,
        token: str,
        ui_url: str,
        tests: List[Path],
        collector_token: Optional[str] = None,
    ):
        self.build_context = build_context
        self.client = None
        self.base_url = base_url
        self.api_key = api_key
        self.auth_id = auth_id
        self.token = token
        self.collector_token = collector_token
        os.environ.pop(
            "DEMISTO_USERNAME", None
        )  # we use client without demisto username
        self.configure_new_client()
        self.ui_url = ui_url
        self.tests = tests

    def configure_new_client(self):
        if self.client:
            self.client.api_client.pool.close()
            self.client.api_client.pool.terminate()
            del self.client
        self.client = demisto_client.configure(
            base_url=self.base_url,
            api_key=self.api_key,
            auth_id=self.auth_id,
            verify_ssl=False,
        )

    def execute_tests(self):
        try:
            self.build_context.logging_module.info(
                f"Starts tests with server url - {get_ui_url(self.ui_url)}",
                real_time=True,
            )
            start_time = get_utc_now()
            self.build_context.logging_module.info(
                f"Running the following tests: {self.tests}",
                real_time=True,
            )

            xsiam_client_cfg = XsiamApiClientConfig(
                base_url=self.base_url,  # type: ignore[arg-type]
                api_key=self.api_key,  # type: ignore[arg-type]
                auth_id=self.auth_id,  # type: ignore[arg-type]
                token=self.token,  # type: ignore[arg-type]
                collector_token=self.collector_token,  # type: ignore[arg-type]
            )
            xsiam_client = XsiamApiClient(xsiam_client_cfg)
            tenant_demisto_version: Version = xsiam_client.get_demisto_version()
            for i, modeling_rule_directory in enumerate(self.tests, start=1):
                logger.info(
                    f"<cyan>[{i}/{len(self.tests)}] Test Modeling Rule: {get_relative_path_to_content(modeling_rule_directory)}</cyan>",
                )
                success, modeling_rule_test_suite = validate_modeling_rule(
                    modeling_rule_directory,
                    # can ignore the types since if they are not set to str values an error occurs
                    self.base_url,  # type: ignore[arg-type]
                    self.build_context.retrying_caller,
                    self.build_context.push,
                    self.build_context.interactive,
                    self.build_context.ctx,
                    self.build_context.delete_existing_dataset,
                    self.build_context.is_nightly,
                    xsiam_client=xsiam_client,
                    tenant_demisto_version=tenant_demisto_version,
                )
                if success:
                    logger.info(
                        f"<green>Test Modeling rule {get_relative_path_to_content(modeling_rule_directory)} passed</green>",
                    )
                else:
                    self.build_context.tests_data_keeper.errors = True
                    logger.error(
                        f"<red>Test Modeling Rule {get_relative_path_to_content(modeling_rule_directory)} failed</red>",
                    )
                if modeling_rule_test_suite:
                    modeling_rule_test_suite.add_property(
                        "start_time",
                        start_time,  # type:ignore[arg-type]
                    )
                    self.build_context.tests_data_keeper.test_results_xml_file.add_testsuite(
                        modeling_rule_test_suite
                    )

                    self.build_context.logging_module.info(
                        f"Finished tests with server url - " f"{self.ui_url}",
                        real_time=True,
                    )
            duration = duration_since_start_time(start_time)
            self.build_context.logging_module.info(
                f"Finished tests with server url - {self.ui_url}, Took: {duration} seconds",
                real_time=True,
            )
        except Exception:
            self.build_context.logging_module.exception("~~ Thread failed ~~")
            self.build_context.tests_data_keeper.errors = True
        finally:
            self.build_context.logging_module.execute_logs()


@app.command(
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
)
def test_modeling_rule(
    ctx: typer.Context,
    inputs: List[Path] = typer.Argument(
        None,
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
    service_account: Optional[str] = typer.Option(
        None,
        "-sa",
        "--service_account",
        envvar="GCP_SERVICE_ACCOUNT",
        help="GCP service account.",
        show_default=False,
    ),
    cloud_servers_path: str = typer.Option(
        "",
        "-csp",
        "--cloud_servers_path",
        help="Path to secret cloud server metadata file.",
        show_default=False,
    ),
    cloud_servers_api_keys: str = typer.Option(
        "",
        "-csak",
        "--cloud_servers_api_keys",
        help="Path to file with cloud Servers api keys.",
        show_default=False,
    ),
    machine_assignment: str = typer.Option(
        "",
        "-ma",
        "--machine_assignment",
        help="the path to the machine assignment file.",
        show_default=False,
    ),
    branch_name: str = typer.Option(
        "master",
        "-bn",
        "--branch_name",
        help="The current content branch name.",
        show_default=True,
    ),
    build_number: str = typer.Option(
        "",
        "-bn",
        "--build_number",
        help="The build number.",
        show_default=True,
    ),
    nightly: str = typer.Option(
        "false",
        "--nightly",
        "-n",
        help="Whether the command is being run in nightly mode.",
    ),
    artifacts_bucket: str = typer.Option(
        None,
        "-ab",
        "--artifacts_bucket",
        help="The artifacts bucket name to upload the results to",
        show_default=False,
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
        console_threshold=console_log_threshold,  # type: ignore[arg-type]
        file_threshold=file_log_threshold,  # type: ignore[arg-type]
        path=log_file_path,
        calling_function=__name__,
    )
    handle_deprecated_args(ctx.args)

    logging_module = ParallelLoggingManager(
        "test_modeling_rules.log", real_time_logs_only=not nightly
    )

    if machine_assignment:
        if inputs:
            logger.error(
                "You cannot pass both machine_assignment and inputs arguments."
            )
            raise typer.Exit(1)
        if xsiam_url:
            logger.error(
                "You cannot pass both machine_assignment and xsiam_url arguments."
            )
            raise typer.Exit(1)

    start_time = get_utc_now()
    is_nightly = string_to_bool(nightly)
    build_context = BuildContext(
        nightly=is_nightly,
        build_number=build_number,
        branch_name=branch_name,
        retry_attempts=retry_attempts,
        sleep_interval=sleep_interval,
        logging_module=logging_module,
        cloud_servers_path=cloud_servers_path,
        cloud_servers_api_keys=cloud_servers_api_keys,
        service_account=service_account,
        artifacts_bucket=artifacts_bucket,
        machine_assignment=machine_assignment,
        push=push,
        interactive=interactive,
        delete_existing_dataset=delete_existing_dataset,
        ctx=ctx,
        xsiam_url=xsiam_url,
        xsiam_token=xsiam_token,
        api_key=api_key,
        auth_id=auth_id,
        collector_token=collector_token,
        inputs=inputs,
    )

    logging_module.info(
        "Test Modeling Rules to test:",
    )

    for build_context_server in build_context.servers:
        for modeling_rule_directory in build_context_server.tests:
            logging_module.info(
                f"\tmachine:{build_context_server.base_url} - "
                f"{get_relative_path_to_content(modeling_rule_directory)}"
            )

    threads_list = []
    for index, server in enumerate(build_context.servers, start=1):
        thread_name = f"Thread-{index} (execute_tests)"
        threads_list.append(Thread(target=server.execute_tests, name=thread_name))

    logging_module.info("Finished creating configurations, starting to run tests.")
    for thread in threads_list:
        thread.start()

    for t in threads_list:
        t.join()

    logging_module.info("Finished running tests.")

    if output_junit_file:
        logger.info(
            f"<cyan>Writing JUnit XML to {get_relative_path_to_content(output_junit_file)}</cyan>",
        )
        build_context.tests_data_keeper.test_results_xml_file.write(
            output_junit_file.as_posix(), pretty=True
        )
        if nightly:
            if service_account and artifacts_bucket:
                build_context.tests_data_keeper.upload_modeling_rules_result_json_to_bucket(
                    XSIAM_SERVER_TYPE,
                    f"test_modeling_rules_report_{build_number}.xml",
                    output_junit_file,
                    logging_module,
                )
            else:
                logger.warning(
                    "<yellow>Service account or artifacts bucket not provided, skipping uploading JUnit XML to bucket</yellow>",
                )
    else:
        logger.info(
            "<cyan>No JUnit XML file path was passed - skipping writing JUnit XML</cyan>",
        )

    duration = duration_since_start_time(start_time)
    if build_context.tests_data_keeper.errors:
        logger.error(
            f"Test Modeling Rules: Failed, took:{duration} seconds",
        )
        raise typer.Exit(1)

    logger.success(
        f"Test Modeling Rules: Passed, took:{duration} seconds",
    )


if __name__ == "__main__":
    app()
