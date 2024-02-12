import argparse
from copy import deepcopy
from pathlib import Path
from typing import Optional, Sequence

from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.common.tools import get_file, is_external_repository


def update_additional_dependencies(
    pre_commit_config_path: Path, requirements_path: Path, hooks: Sequence[str]
) -> int:
    """This function updates the additional dependencies of selected pre-commit hooks according to a requirements file

    Args:
        pre_commit_config_path (Path): The path of the pre-commit-config
        requirements_path (Path): The path of the requirements file
        hooks (Sequence[str]): The hooks to update

    Returns:
        int: 1 if failed, 0 if succeeded (OR not in a content-likerepository)
    """
    logging_setup()
    if is_external_repository():
        logger.warning("Cannot detect repo, skipping update_additional_dependencies")
        return 0
    try:
        if not requirements_path.exists():
            logger.info(
                "Skipping update of additional dependencies since requirements.txt was not found"
            )
            return 0
        requirements = requirements_path.read_text().splitlines()
        logger.info(f"Updating additional dependencies of {hooks} to {requirements}")
        pre_commit = get_file(pre_commit_config_path)
        pre_commit_orig = deepcopy(pre_commit)
        for repo in pre_commit["repos"]:
            for hook in repo["hooks"]:
                if hook["id"] in hooks:
                    hook["additional_dependencies"] = requirements
        if pre_commit != pre_commit_orig:
            logger.info(
                f"Detected changes in pre-commit config:{pre_commit_config_path}, updating it"
            )
            with pre_commit_config_path.open("w") as f:
                yaml.dump(pre_commit, f, sort_keys=True)
        return 0
    except Exception:
        logger.exception("Failed to update additional dependencies")
        return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the additional dependencies of precommit hooks"
    )
    parser.add_argument(
        "--pre_commit_config",
        help="The path to the pre-commit config file",
        default=".pre-commit-config.yaml",
    )
    parser.add_argument(
        "--requirements",
        help="Path to the requirements file",
        default="requirements.txt",
    )
    parser.add_argument(
        "hooks",
        help="The hooks to update, separated by spaces",
        nargs="*",
        default=["mypy"],
    )
    args = parser.parse_args(argv)
    return update_additional_dependencies(
        Path(args.pre_commit_config), Path(args.requirements), args.hooks
    )


if __name__ == "__main__":
    SystemExit(main())
