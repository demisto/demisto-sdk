import traceback
from io import StringIO
from pathlib import Path
from typing import List, Set

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
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
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
        "--console_log_threshold",
        help=("Minimum logging threshold for the console logger."),
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file_log_threshold",
        help=("Minimum logging threshold for the file logger."),
    ),
    log_file_path: str = typer.Option(
        "demisto_sdk_debug.log",
        "-lp",
        "--log_file_path",
        help=("Path to the log file. Default: ./demisto_sdk_debug.log."),
    ),
):
    """
    Initialize or update a test data file for a modeling rule
    """
    logging_setup(
        console_log_threshold=console_log_threshold,
        file_log_threshold=file_log_threshold,
        log_file_path=log_file_path,
    )
    handle_deprecated_args(ctx.args)

    errors = False
    for fp in input:
        try:
            mr_entity = ModelingRule(fp.as_posix())
            all_mr_entity_fields: Set[str] = set()
            for mr in mr_entity.rules:
                all_mr_entity_fields = all_mr_entity_fields.union(mr.fields)

            operation_mode = "create"
            default_event_mapping = dict.fromkeys(all_mr_entity_fields)
            default_dataset = mr_entity.rules[0].dataset
            default_vendor = mr_entity.rules[0].vendor
            default_product = mr_entity.rules[0].product
            test_data_file = mr_entity.testdata_path
            if test_data_file:
                operation_mode = "update"
                logger.info(
                    f"[cyan]Updating test data file: {test_data_file}[/cyan]",
                    extra={"markup": True},
                )
                test_data = TestData.parse_file(test_data_file)
                for event_log in test_data.data:
                    if not event_log.vendor:
                        event_log.vendor = default_vendor
                    if not event_log.product:
                        event_log.product = default_product
                    if not event_log.dataset:
                        event_log.dataset = default_dataset
                    new_mapping = default_event_mapping.copy()

                    # remove xdm expected_values fields that are no longer in the rule
                    if event_log.expected_values:
                        keys_to_remove = []
                        for key in event_log.expected_values:
                            if key not in new_mapping:
                                keys_to_remove.append(key)
                        for key in keys_to_remove:
                            event_log.expected_values.pop(key)
                        new_mapping.update(event_log.expected_values)

                    event_log.expected_values = new_mapping

                if count > len(test_data.data):
                    # create the missing templated data and add it to the test data
                    templated_event_data_to_add = [
                        EventLog(
                            vendor=default_vendor,
                            product=default_product,
                            dataset=default_dataset,
                            expected_values=default_event_mapping.copy(),
                        )
                        for _ in range(count - len(test_data.data))
                    ]

                    test_data.data.extend(templated_event_data_to_add)
            else:
                logger.info(
                    f"[cyan]Creating test data file for: {mr_entity.path.parent}[/cyan]",
                    extra={"markup": True},
                )
                test_data = TestData(
                    data=[
                        EventLog(
                            vendor=default_vendor,
                            product=default_product,
                            dataset=default_dataset,
                            expected_values=default_event_mapping.copy(),
                        )
                        for _ in range(count)
                    ]
                )
                test_data_file = (
                    mr_entity.path.parent
                    / f"{mr_entity.path.parent.stem}{mr_entity.TESTDATA_FILE_SUFFIX}"
                )
            test_data_file.write_text(test_data.json(indent=4))
            logger.info(
                f"[green]Successfully {operation_mode}d {test_data_file}[/green]",
                extra={"markup": True},
            )
        except Exception:
            with StringIO() as sio:
                traceback.print_exc(file=sio)
                logger.error(f"[red]{sio.getvalue()}[/red]", extra={"markup": True})
            errors = True
    if errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
