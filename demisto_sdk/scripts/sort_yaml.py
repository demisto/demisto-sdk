from pathlib import Path
from typing import Annotated, Any

import typer
from typer import Argument

from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml

PRIORITY_FIELDS = ("display", "name", "id")


def sort(value: Any) -> Any:
    if isinstance(value, dict):
        return sort_dict({k: sort(v) for k, v in value.items()})
    elif isinstance(value, list):
        return [sort(v) for v in value]
    else:
        return value


def sort_dict(in_dict: dict) -> dict:
    in_dict = in_dict.copy()  # avoid mutating the original dictionary
    result = {}

    for key in PRIORITY_FIELDS:
        # First add the priority fields
        if key in in_dict:
            result[key] = in_dict.pop(key)

    for key in sorted(in_dict.keys()):
        # not removing PRIORITY_FIELDS keys as they have already been popped out of in_dict
        result[key] = in_dict[key]

    return result


def sort_file(path: Path) -> None:
    if path.suffix not in (".yml", ".yaml"):
        typer.echo("The file must be a YAML file.", err=True)
        raise typer.Exit(1)

    yaml_content = yaml.load(path.read_text())
    sorted_yaml_content = sort(yaml_content)
    path.write_text(yaml.dumps(sorted_yaml_content, sort_keys=False))


def _main(
    path: Annotated[
        Path,
        Argument(
            help="The file to sort, or a directory containing files to sort.",
            file_okay=True,
            dir_okay=True,
            exists=True,
            readable=True,
            writable=True,
        ),
    ],
) -> None:
    if path.is_file():
        sort_file(path)
    else:
        for file in set(path.glob("*.yml")).union(path.glob("*.yaml")):
            sort_file(file)


def main():
    typer.run(_main)


if __name__ == "__main__":
    main()
