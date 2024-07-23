from pathlib import Path
from typing import Iterable, List

import typer
from more_itertools import first, map_reduce
from tabulate import tabulate
from typing_extensions import Annotated

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.validate.validators.base_validator import (
    VALIDATION_CATEGORIES,
    BaseValidator,
    get_all_validators,
)


def generate_validate_docs() -> str:
    result: List[str] = []
    for category, validators in dict(
        sorted(  # sort categories
            map_reduce(  # group validators by category
                get_all_validators(),
                keyfunc=lambda validator: validator.error_category,
            ).items()
        )
    ).items():
        result.extend(
            (
                f"## `{category}`: {VALIDATION_CATEGORIES[category]}",  # test_validation_prefix prevents KeyErrors here
                _create_table(validators),
            )
        )
    return "\n".join(result)


def _create_table(validators: Iterable[BaseValidator]) -> str:
    unique_validators = (
        # dedupe per error code, by choosing the one with the "smaller" description (ordered alphabetically)
        first(sorted(validators, key=lambda validator: validator.description))
        for validators in map_reduce(
            # group validators by code, in case there are multiple implementations
            validators,
            keyfunc=lambda validator: validator.error_code,
        ).values()
    )

    def clean_newlines(string: str) -> str:
        return string.replace("\n", ". ")

    table_rows = [
        {
            "Code": validator.error_code,
            "Description": clean_newlines(validator.description),
            "Rationale": clean_newlines(validator.rationale),
            "Autofixable": "Yes" if validator.is_auto_fixable else "",
        }
        for validator in sorted(
            unique_validators, key=lambda validator: validator.error_code
        )
    ]
    return tabulate(table_rows, headers="keys", tablefmt="github")


def cli(
    output_path: Annotated[Path, typer.Argument(dir_okay=False, exists=False)],
) -> None:
    TextFile.write(generate_validate_docs(), output_path)


if __name__ == "__main__":
    typer.run(cli)
