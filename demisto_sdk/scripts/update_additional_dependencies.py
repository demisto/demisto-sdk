import argparse
from pathlib import Path
from typing import List, Optional, Sequence

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file

yaml = YAML_Handler()


def update_additional_dependencies(
    pre_commit_config_path: Path, requirements_path: Path
) -> int:
    try:
        requirements = requirements_path.read_text().splitlines()
        pre_commit = get_file(pre_commit_config_path)
        additional_dependencies = pre_commit.get("additional_dependencies", [])
        additional_dependencies.clear()
        additional_dependencies.extend(requirements)
        with pre_commit_config_path.open("w") as f:
            yaml.dump(pre_commit, f)
        return 0
    except Exception as e:
        logger.error("Failed to update additional dependencies: %s", e)
        return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the additional dependencies of precommit"
    )
    parser.add_argument(
        "--pre_commit_config",
        help="The path to the pre-commit config file",
        default=".pre-commit-config.yaml",
    )
    parser.add_argument(
        "--requirements",
        help="The path to the requirements file",
        default="requirements.txt",
    )
    parser.add_argument(
        "hooks", help="The hooks to update", nargs="*", default=["mypy"]
    )
    args = parser.parse_args(argv)
    return update_additional_dependencies(
        Path(args.pre_commit_config), Path(args.requirements), args.hooks
    )


if __name__ == "__main__":
    SystemExit(main())
