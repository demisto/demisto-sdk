import traceback
from io import StringIO
from pathlib import Path
from typing import List, Optional

import typer

from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import (
    ModelingRule,
)
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
)
from demisto_sdk.commands.test_content.xsiam_tools.test_data import EventLog, TestData

app = typer.Typer()


@app.command(
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
)
def init_test_data(
    ctx: typer.Context,
    input: List[Path] = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=(
            "The path to a directory of a modeling rule. May pass multiple paths to "
            "initialize/update test data files for multiple modeling rules."
        ),
    ),
    count: int = typer.Option(
        1,
        "-c",
        "--count",
        min=1,
        show_default=True,
        help="The number of events to initialize the test data file for.",
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
    Initialize or update a test data file for a modeling rule
    """
    logging_setup(
        console_threshold=console_log_threshold,
        file_threshold=file_log_threshold,
        path=log_file_path,
        calling_function=__name__,
    )
    handle_deprecated_args(ctx.args)

    errors = False
    for fp in input:
        try:
            mr_entity = ModelingRule(fp.as_posix())

            operation_mode = "create"
            test_data_file = mr_entity.testdata_path

            if test_data_file:
                operation_mode = "update"
                logger.info(
                    f"<cyan>Updating test data file: {test_data_file}</cyan>",
                )
                test_data = TestData.parse_file(test_data_file)
                dataset_to_fields_map = {
                    mr.dataset: dict.fromkeys(mr.fields) for mr in mr_entity.rules
                }

                # set the default values from the first rule if there is only one, otherwise it should populated manually
                default_rule = mr_entity.rules[0] if len(mr_entity.rules) == 1 else None
                default_vendor = default_rule.vendor if default_rule else ""
                default_product = default_rule.product if default_rule else ""
                default_dataset = default_rule.dataset if default_rule else ""

                for event_log in test_data.data:
                    if not event_log.vendor:
                        event_log.vendor = default_vendor
                    if not event_log.product:
                        event_log.product = default_product
                    if not event_log.dataset:
                        event_log.dataset = default_dataset

                    new_mapping = dataset_to_fields_map.get(
                        event_log.dataset, {}
                    ).copy()
                    if not new_mapping:
                        logger.error(
                            f"<red>Ignoring update the event log {event_log.test_data_event_id} as no dataset is provided for it</red>",
                        )
                        continue
                    # update existing values and remove fields from expected_values that are no longer in the rule
                    if event_log.expected_values:
                        new_mapping = {
                            key: event_log.expected_values.get(key)
                            for key in new_mapping.keys()
                        }

                    event_log.expected_values = new_mapping

                rules_count = len(mr_entity.rules)
                data_entries_count = len(test_data.data)
                expected_entries_count = count * rules_count

                if expected_entries_count > data_entries_count:
                    # create the missing templated data and add it to the test data

                    for mr in mr_entity.rules:
                        test_data.data.extend(
                            [
                                EventLog(
                                    vendor=mr.vendor,
                                    product=mr.product,
                                    dataset=mr.dataset,
                                    expected_values=dict.fromkeys(mr.fields),
                                )
                                for _ in range(
                                    int(
                                        (expected_entries_count - data_entries_count)
                                        / rules_count
                                    )
                                )
                            ]
                        )
            else:
                logger.info(
                    f"<cyan>Creating test data file for: {mr_entity.path.parent}</cyan>",
                )
                data: List[TestData] = []
                for mr in mr_entity.rules:
                    data.extend(
                        [
                            EventLog(
                                vendor=mr.vendor,
                                product=mr.product,
                                dataset=mr.dataset,
                                expected_values=dict.fromkeys(mr.fields),
                            )
                            for _ in range(count)
                        ]
                    )
                test_data = TestData(data=data)
                test_data_file = (
                    mr_entity.path.parent
                    / f"{mr_entity.path.parent.stem}{mr_entity.TESTDATA_FILE_SUFFIX}"
                )
            test_data_file.write_text(test_data.json(indent=4))
            logger.info(
                f"<green>Successfully {operation_mode}d {test_data_file}</green>",
            )
        except Exception:
            with StringIO() as sio:
                traceback.print_exc(file=sio)
                logger.error(
                    f"<red>{sio.getvalue()}</red>",
                )
            errors = True
    if errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
