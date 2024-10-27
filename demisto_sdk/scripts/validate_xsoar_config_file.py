from pathlib import Path

import typer
from pydantic import ValidationError

from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.objects.xsoar_conf_file import (
    XSOAR_Configuration,
)

FILE_NAME = "xsoar_config.json"


class NotAJSONError(Exception): ...


def _validate(path: Path = Path(FILE_NAME)) -> None:
    if path.suffix != ".json":
        raise NotAJSONError
    XSOAR_Configuration.validate(get_file(path))


def validate(path: Path) -> None:
    try:
        _validate(path)
        logger.info(f"<green>{path} is valid </green>")

    except FileNotFoundError:
        logger.error(f"File {path} does not exist")
        raise typer.Exit(1)

    except NotAJSONError:
        logger.error(f"Path {path} is not to a JSON file")
        raise typer.Exit(1)

    except JSONDecodeError:
        logger.error(f"Could not parse JSON from {path}")
        raise typer.Exit(1)

    except ValidationError:
        logger.exception(f"{path} is not a valid XSOAR configuration file")
        raise typer.Exit(1)


if __name__ == "__main__":
    logging_setup(calling_function=Path(__file__).stem)
    typer.run(validate)
