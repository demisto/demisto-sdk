from io import StringIO
import traceback
import typer
from rich import print as printr
from typing import List
from pathlib import Path
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import ModelingRule
from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData, EventLog


app = typer.Typer()


@app.command(no_args_is_help=True)
def init_test_data(
    input: List[Path] = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=('The path to a directory of a modeling rule. May pass multiple paths to '
              'initialize test data files for multiple modeling rules.')
    ),
    count: int = typer.Option(
        1,
        '-c', '--count',
        min=1,
        show_default=True,
        help='The number of events to initialize the test data file for.',
    ),
    debug: bool = typer.Option(
        False,
        '-d', '--debug',
        show_default=True,
        help='Will re-raise caught exceptions.',
        hidden=True,
    )
):
    """
    Initializes a test data file for a modeling rule
    """
    errors = False
    mr_content_entities = [ModelingRule(fp.as_posix()) for fp in input]
    for mr_entity in mr_content_entities:
        try:
            all_mr_entity_fields = set()
            for mr in mr_entity.rules:
                all_mr_entity_fields = all_mr_entity_fields.union(mr.fields)

            operation_mode = 'create'
            default_event_mapping = dict.fromkeys(all_mr_entity_fields)
            default_dataset = mr_entity.rules[0].dataset
            default_vendor = mr_entity.rules[0].vendor
            default_product = mr_entity.rules[0].product
            test_data_file = mr_entity.testdata_path
            if test_data_file:
                operation_mode = 'update'
                printr(f'[cyan]Updating test data file: {test_data_file}[/cyan]')
                test_data = TestData.parse_file(test_data_file)
                for event_log in test_data.data:
                    if not event_log.vendor:
                        event_log.vendor = default_vendor
                    if not event_log.product:
                        event_log.product = default_product
                    if not event_log.dataset:
                        event_log.dataset = default_dataset
                # for expected in test_data.expected_values:
                    new_mapping = default_event_mapping.copy()

                    # remove xdm mapping fields that are no longer in the rule
                    if event_log.mapping:
                        keys_to_remove = []
                        for key in event_log.mapping:
                            if key not in new_mapping:
                                keys_to_remove.append(key)
                        for key in keys_to_remove:
                            event_log.mapping.pop(key)
                        new_mapping.update(event_log.mapping)

                    event_log.mapping = new_mapping

                if count > len(test_data.data):
                    # create the missing templated data and add it to the test data
                    templated_event_data_to_add = [
                        EventLog(
                            vendor=default_vendor,
                            product=default_product,
                            dataset=default_dataset,
                            mapping=default_event_mapping.copy()
                        ) for _ in range(count - len(test_data.data))
                    ]

                    test_data.data.extend(templated_event_data_to_add)
            else:
                printr(f'[cyan]Creating test data file for: {mr_entity.path.parent}[/cyan]')
                test_data = TestData(
                    data=[
                        EventLog(
                            vendor=default_vendor,
                            product=default_product,
                            dataset=default_dataset,
                            mapping=default_event_mapping.copy()
                        ) for _ in range(count)
                    ]
                )
                test_data_file = mr_entity.path.parent / f'{mr_entity.path.parent.stem}{mr_entity.TESTDATA_FILE_SUFFIX}'
            test_data_file.write_text(test_data.json(indent=4))
            printr(f'[green]Successfully {operation_mode}d {test_data_file}[/green]')
        except Exception:
            with StringIO() as sio:
                traceback.print_exc(file=sio)
                printr(f'[red]{sio.getvalue()}[/red]')
            errors = True
    if errors:
        typer.Exit(1)


if __name__ == "__main__":
    app()
