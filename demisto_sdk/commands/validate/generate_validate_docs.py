from pathlib import Path
from typing import Iterable, List

import typer
from more_itertools import map_reduce
from tabulate import tabulate
from typing_extensions import Annotated

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.validate.validators.base_validator import (
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
        result.extend((f"## {category}", _create_table(validators)))
    return "\n".join(result)


def _create_table(validators: Iterable[BaseValidator]) -> str:
    return tabulate(
        (
            {
                "Code": validator.error_code,
                "Description": validator.description.replace("\n", ". "),
                "Autofixable": "Yes" if validator.is_auto_fixable else "No",
            }
            for validator in sorted(validators, key=lambda v: v.error_code)
        ),
        headers="keys",
        tablefmt="github",
    )


def cli(
    output_path: Annotated[Path, typer.Argument(dir_okay=False, exists=False)]
) -> None:
    TextFile.write(generate_validate_docs(), output_path)


if __name__ == "__main__":
    typer.run(cli)
