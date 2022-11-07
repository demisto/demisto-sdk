import typer
from typing import List
from pathlib import Path
from demisto_sdk.commands.common.content.objects.pack_objects.modeling_rule.modeling_rule import ModelingRule
from demisto_sdk.commands.test_content.xsiam_tools.test_data import TestData, EventLog, ExpectedOutputs


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
    )
):
    """
    Initializes a test data file for a modeling rule
    """
    errors = []
    mr_content_entities = [ModelingRule(fp.as_posix()) for fp in input]
    try:
        for mr_entity in mr_content_entities:
            all_mr_entity_fields = set()
            for mr in mr_entity.rules:
                all_mr_entity_fields = all_mr_entity_fields.union(mr.fields)

            default_event_mapping = dict.fromkeys(all_mr_entity_fields)
            test_data_file = mr_entity.testdata_path
            if test_data_file:
                typer.echo(f'Updating test data file: {test_data_file}')
                test_data = TestData.parse_file(test_data_file)
                for expected in test_data.expected_values:
                    new_mapping = default_event_mapping.copy()
                    new_mapping.update(expected.mapping)
                    expected.mapping = new_mapping

                if count > len(test_data.data):
                    test_data.data.extend([EventLog() for _ in range(count - len(test_data.data))])
                    test_data.expected_values.extend(
                        [ExpectedOutputs(mapping=default_event_mapping) for _ in range(count - len(test_data.data))]
                    )
            else:
                typer.echo(f'Creating test data file for: {mr_entity.path}')
                test_data = TestData(
                    data=[EventLog() for _ in range(count)],
                    expected_values=[ExpectedOutputs(mapping=default_event_mapping) for _ in range(count)],
                )
                test_data_file = mr_entity.path.parent / f'{mr_entity.path.parent.stem}{mr_entity.TESTDATA_FILE_SUFFIX}'
            test_data_file.write_text(test_data.json(indent=4))
    except Exception as e:
        errors.append(e)
    for error in errors:
        typer.echo(f'Error: {error}')
    raise errors[0] if errors else typer.Exit(0)


if __name__ == "__main__":
    app()
