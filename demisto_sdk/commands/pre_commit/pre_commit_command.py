import multiprocessing
import os
import re
import subprocess
import sys
from collections import defaultdict
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import more_itertools
from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    DEFAULT_PYTHON_VERSION,
    INTEGRATIONS_DIR,
    PACKS_FOLDER,
    SCRIPTS_DIR,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import should_disable_multiprocessing, write_dict
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.pre_commit.hooks.docker import DockerHook
from demisto_sdk.commands.pre_commit.hooks.hook import GeneratedHooks, Hook, join_files
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.pycln import PyclnHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.sourcery import SourceryHook
from demisto_sdk.commands.pre_commit.hooks.system import SystemHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook
from demisto_sdk.commands.pre_commit.pre_commit_context import (
    DEFAULT_PRE_COMMIT_TEMPLATE_PATH,
    PRECOMMIT_CONFIG_MAIN_PATH,
    PRECOMMIT_TEMPLATE_PATH,
    PreCommitContext,
)

SKIPPED_HOOKS = {"format", "validate", "secrets"}

INTEGRATION_SCRIPT_REGEX = re.compile(r"^Packs/.*/(?:Integrations|Scripts)/.*.yml$")
INTEGRATIONS_BATCH = 300

PY_TEST_FILE_SUFFIX = "_test.py"
PS1_TEST_FILE_SUFFIX = ".Tests.ps1"


class PreCommitRunner:
    original_hook_id_to_generated_hook_ids: Dict[str, GeneratedHooks] = {}

    @staticmethod
    def prepare_hooks(pre_commit_context: PreCommitContext) -> None:
        """
        Prepares the hooks for a pre-commit execution.

        Note:
            The hooks execution will be ordered according to their order definition at the template file.

        Args:
            pre_commit_context: pre-commit context object.
        """
        hooks = pre_commit_context.hooks

        custom_hooks_to_classes = {
            "pycln": PyclnHook,
            "ruff": RuffHook,
            "sourcery": SourceryHook,
            "validate": ValidateFormatHook,
            "format": ValidateFormatHook,
            "mypy": MypyHook,
        }

        for hook_id in hooks.copy():
            if hook_id in custom_hooks_to_classes:
                PreCommitRunner.original_hook_id_to_generated_hook_ids[hook_id] = (
                    custom_hooks_to_classes[
                        hook_id
                    ](**hooks.pop(hook_id), context=pre_commit_context).prepare_hook()
                )
            elif hook_id.endswith("in-docker"):
                PreCommitRunner.original_hook_id_to_generated_hook_ids[hook_id] = (
                    DockerHook(
                        **hooks.pop(hook_id), context=pre_commit_context
                    ).prepare_hook()
                )
            else:
                # this is used to handle the mode property correctly even for non-custom hooks which do not require
                # special preparation
                PreCommitRunner.original_hook_id_to_generated_hook_ids[hook_id] = Hook(
                    **hooks.pop(hook_id), context=pre_commit_context
                ).prepare_hook()

            logger.debug(f"Prepared hook {hook_id} successfully")

        # get the hooks again because we want to get all the hooks, including the once that already prepared
        hooks = pre_commit_context._get_hooks(pre_commit_context.precommit_template)
        system_hooks = [
            hook_id
            for hook_id, hook in hooks.items()
            if hook["hook"].get("language") == "system"
        ]
        for hook_id in system_hooks.copy():
            SystemHook(**hooks[hook_id], context=pre_commit_context).prepare_hook()
            logger.debug(f"Prepared system hook {hook_id} successfully")

    @staticmethod
    def run_hook(
        hook_id: str,
        precommit_env: dict,
        verbose: bool = False,
        stdout: Optional[int] = subprocess.PIPE,
        json_output_path: Optional[Path] = None,
    ) -> int:
        """This function runs the pre-commit process and waits until finished.
        We run this function in multithread.

        Args:
            hook_id (str): The hook ID to run
            precommit_env (dict): The pre-commit environment variables
            verbose (bool, optional): Whether print verbose output. Defaults to False.
            stdout (Optional[int], optional): The way to handle stdout. Defaults to subprocess.PIPE.
            json_output_path (Optional[Path]): Optional path to a JSON formatted output file/dir where pre-commit hooks
                results are stored. None by deafult, and file is not created.
        Returns:
            int: return code - 0 if hook passed, 1 if failed
        """
        logger.debug(f"Running hook {hook_id}")

        if json_output_path and json_output_path.is_dir():
            json_output_path = json_output_path / f"{hook_id}.json"

        process = PreCommitRunner._run_pre_commit_process(
            PRECOMMIT_CONFIG_MAIN_PATH,
            precommit_env,
            verbose,
            stdout,
            command=["run", "-a", hook_id],
            json_output_path=json_output_path,
        )

        if process.stdout:
            logger.info("{}", process.stdout)  # noqa: PLE1205 see https://github.com/astral-sh/ruff/issues/13390
        if process.stderr:
            logger.error("{}", process.stderr)  # noqa: PLE1205 see https://github.com/astral-sh/ruff/issues/13390
        return process.returncode

    @staticmethod
    def _run_pre_commit_process(
        path: Path,
        precommit_env: dict,
        verbose: bool,
        stdout=None,
        command: Optional[List[str]] = None,
        json_output_path: Optional[Path] = None,
    ) -> subprocess.CompletedProcess:
        """Runs a process of pre-commit

        Args:
            path (Path): Pre commit path
            precommit_env (dict): Environment variables set on pre-commit
            verbose (bool): whether to print verbose output
            stdout (optional): use `subprocess.PIPE` to capture stdout. Use None to print it. Defaults to None.
            command (Optional[List[str]], optional): The pre-commit command to run. Defaults to None.
            json_output_path (Optional[Path]): Optional path to a JSON formatted output file/dir where pre-commit hooks
                results are stored. None by deafult, and file is not created.
        Returns:
            _type_: _description_
        """
        if command is None:
            command = ["run", "-a"]
        output = subprocess.PIPE if json_output_path else stdout
        completed_process = subprocess.run(
            list(
                filter(
                    None,
                    [
                        sys.executable,
                        "-m",
                        "pre_commit",
                        *command,
                        "-c",
                        str(path),
                        "-v" if verbose and "run" in command else "",
                    ],
                )
            ),
            env=precommit_env,
            cwd=CONTENT_PATH,
            stdout=output,
            stderr=output,
            universal_newlines=True,
        )
        # Only writing failed hook results.
        if json_output_path and completed_process.returncode != 0:
            with open(json_output_path, "w") as json_file:
                json = JSON_Handler()
                json.dump(completed_process.__dict__, json_file, indent=4)

        return completed_process

    @staticmethod
    def run(
        pre_commit_context: PreCommitContext,
        precommit_env: dict,
        verbose: bool,
        show_diff_on_failure: bool,
        json_output_path: Optional[Path] = None,
    ) -> int:
        """Execute the pre-commit hooks on the files.

        Args:
            pre_commit_context (PreCommitContext): The precommit context object (This data is shared between all hooks).
            precommit_env (dict): The environment variables dict.
            verbose (bool):  Whether run pre-commit in verbose mode.
            show_diff_on_failure (bool): Whether to show diff when a hook fail or not.
            json_output_path (Optional[Path]): Optional path to a JSON formatted output file/dir where pre-commit hooks
                results are stored. None by deafult, and file is not created.
        Returns:
            int: The exit code - 0 if everything is valid.
        """
        if pre_commit_context.mode:
            logger.info(
                f"<yellow>Running pre-commit hooks in `{pre_commit_context.mode}` mode.</yellow>"
            )
        if pre_commit_context.run_hook:
            logger.info(f"<yellow>Running hook {pre_commit_context.run_hook}</yellow>")

        write_dict(PRECOMMIT_CONFIG_MAIN_PATH, pre_commit_context.precommit_template)
        # we don't need the context anymore, we can clear it to free up memory for the pre-commit checks
        del pre_commit_context

        # install dependencies of all hooks in advance
        PreCommitRunner._run_pre_commit_process(
            PRECOMMIT_CONFIG_MAIN_PATH,
            precommit_env,
            verbose,
            command=["install-hooks"],
            json_output_path=json_output_path
            if not json_output_path or json_output_path.is_file()
            else json_output_path / "install-hooks.json",
        )

        num_processes = cpu_count()
        all_hooks_exit_codes = []
        hooks_to_run = PreCommitRunner.original_hook_id_to_generated_hook_ids.items()
        logger.debug(f"run {hooks_to_run=}")

        for original_hook_id, generated_hooks in hooks_to_run:
            if generated_hooks:
                logger.debug(f"Running hook {original_hook_id} with {generated_hooks}")
                hook_ids = generated_hooks.hook_ids
                if (
                    generated_hooks.parallel
                    and len(hook_ids) > 1
                    and not should_disable_multiprocessing()
                ):
                    # We shall not write results to the same file if running hooks in parallel, therefore,
                    # writing the results to a parallel directory.
                    if json_output_path and not json_output_path.is_dir():
                        json_output_path = (
                            json_output_path.parent / json_output_path.stem
                        )
                        json_output_path.mkdir(exist_ok=True)
                    with ThreadPool(num_processes) as pool:
                        current_hooks_exit_codes = pool.map(
                            partial(
                                PreCommitRunner.run_hook,
                                precommit_env=precommit_env,
                                verbose=verbose,
                                stdout=subprocess.PIPE,
                                json_output_path=json_output_path,
                            ),
                            hook_ids,
                        )
                else:
                    current_hooks_exit_codes = [
                        PreCommitRunner.run_hook(
                            hook_id,
                            precommit_env=precommit_env,
                            verbose=verbose,
                            json_output_path=json_output_path,
                        )
                        for hook_id in hook_ids
                    ]

                all_hooks_exit_codes.extend(current_hooks_exit_codes)

            else:
                logger.debug(
                    f"Skipping hook {original_hook_id} as it does not have any generated-hook-ids"
                )

        return_code = int(any(all_hooks_exit_codes))
        if return_code and show_diff_on_failure:
            logger.info(
                "Pre-Commit changed the following. If you experience this in CI, please run `demisto-sdk pre-commit`"
            )
            git_diff = subprocess.run(
                ["git", "--no-pager", "diff", "--no-ext-diff"],
                stdout=subprocess.PIPE,
                universal_newlines=True,
            )
            logger.info(git_diff.stdout)
        return return_code

    @staticmethod
    def prepare_and_run(
        pre_commit_context: PreCommitContext,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
        exclude_files: Optional[Set[Path]] = None,
        dry_run: bool = False,
        json_output_path: Optional[Path] = None,
    ) -> int:
        """Trigger the relevant hooks.

        Args:
            pre_commit_context (PreCommitContext): The precommit context object (This data is shared between all hooks).
            verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
            show_diff_on_failure (bool, optional): Whether to show diff when a hook fail or not. Defaults to False.
            exclude_files (Optional[Set[Path]], optional): Files to exclude when running. Defaults to None.
            dry_run (bool, optional): Whether to run the pre-commit hooks in dry-run mode. Defaults to False.
            json_output_path (Path, optional): Optional path to a JSON formatted output file/dir where pre-commit hooks
                results are stored. None by default, and file is not created.
        Returns:
            int: The exit code, 0 if nothing failed.
        """

        ret_val = 0
        pre_commit_context.dry_run = dry_run
        precommit_env = os.environ.copy()
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
        # The PYTHONPATH should be the same as the PYTHONPATH, but without the site-packages because MYPY does not support it
        precommit_env["MYPYPATH"] = ":".join(
            str(path) for path in sorted(PYTHONPATH) if "site-packages" not in str(path)
        )
        precommit_env["DEMISTO_SDK_CONTENT_PATH"] = str(CONTENT_PATH)
        precommit_env["SYSTEMD_COLORS"] = "1"  # for colorful output
        precommit_env["PRE_COMMIT_COLOR"] = "always"

        if pre_commit_context.all_files:
            logger.info("Running pre-commit on all files")

        else:
            for (
                python_version,
                changed_files_by_version,
            ) in pre_commit_context.python_version_to_files.items():
                changed_files_string = "\n".join(
                    sorted(str(file) for file in changed_files_by_version)
                )
                logger.info(
                    f"Running pre-commit with Python {python_version} on:\n{changed_files_string}"
                )

        PreCommitRunner.prepare_hooks(pre_commit_context)

        if pre_commit_context.all_files:
            if exclude_files:
                pre_commit_context.precommit_template["exclude"] += (
                    f"|{join_files(exclude_files)}"
                )
        else:
            pre_commit_context.precommit_template["files"] = join_files(
                pre_commit_context.files_to_run
            )

        if dry_run:
            write_dict(
                PRECOMMIT_CONFIG_MAIN_PATH, data=pre_commit_context.precommit_template
            )
            logger.info(
                f"Dry run, skipping pre-commit.\nConfig file saved to {PRECOMMIT_CONFIG_MAIN_PATH}"
            )
            return ret_val
        ret_val = PreCommitRunner.run(
            pre_commit_context,
            precommit_env,
            verbose,
            show_diff_on_failure,
            json_output_path,
        )
        return ret_val


def group_by_language(
    files: Set[Path],
) -> Tuple[Dict[str, Set[Tuple[Path, Optional[IntegrationScript]]]], Set[Path]]:
    """This function groups the files to run pre-commit on by the python version.

    Args:
        files (Set[Path]): files to run pre-commit on.

    Raises:
        Exception: If invalid files were given.

    Returns:
        Tuple[Dict[str, Set[Tuple[Path, Optional[IntegrationScript]]]], Set[Path]]:
        The files grouped by their python version, and a set of excluded paths,
        The excluded files (due to deprecation).
    """
    integrations_scripts_mapping = defaultdict(set)
    infra_files = []
    api_modules = []
    for file in files:
        if file.is_dir():
            continue
        if (
            set(file.parts) & {INTEGRATIONS_DIR, SCRIPTS_DIR}
            and file.parts[0] == PACKS_FOLDER  # this is relative path so it works
        ):
            find_path_index = (
                i + 1
                for i, part in enumerate(file.parts)
                if part in {INTEGRATIONS_DIR, SCRIPTS_DIR}
            )
            if not find_path_index:
                raise Exception(f"Could not find Integrations/Scripts path for {file}")
            code_file_path = CONTENT_PATH / Path(
                *file.parts[: next(find_path_index) + 1]
            )
            if not code_file_path.is_dir():
                continue
            integrations_scripts_mapping[code_file_path].add(file)
        else:
            infra_files.append(file)

    language_to_files: Dict[str, Set] = defaultdict(set)
    integrations_scripts: Set[IntegrationScript] = set()
    logger.debug("Pre-Commit: Starting to parse all integrations and scripts")
    for integration_script_paths in more_itertools.chunked_even(
        integrations_scripts_mapping.keys(), INTEGRATIONS_BATCH
    ):
        if should_disable_multiprocessing():
            # Run sequentially
            content_items: List[Optional[BaseContent]] = list(
                map(BaseContent.from_path, integration_script_paths)
            )
        else:
            # Use multiprocessing (not supported when running within Content scripts/integrations).
            with multiprocessing.Pool(processes=cpu_count()) as pool:
                content_items = list(
                    pool.map(BaseContent.from_path, integration_script_paths)
                )

        for content_item in content_items:
            if isinstance(content_item, IntegrationScript):
                integrations_scripts.add(content_item)

    logger.debug("Pre-Commit: Finished parsing all integrations and scripts")
    exclude_integration_script = set()
    for integration_script in integrations_scripts:
        if (pack := integration_script.in_pack) and pack.object_id == API_MODULES_PACK:
            # add api modules to the api_modules list, we will handle them later
            api_modules.append(integration_script)
            continue

    if api_modules:
        logger.debug("Pre-Commit: Starting to handle API Modules")
        with ContentGraphInterface() as graph:
            update_content_graph(graph)
            api_modules: List[Script] = graph.search(  # type: ignore[no-redef]
                object_id=[api_module.object_id for api_module in api_modules]
            )
        for api_module in api_modules:
            assert isinstance(api_module, Script)
            for imported_by in api_module.imported_by:
                # we need to add the api module for each integration that uses it, so it will execute the api module check
                integrations_scripts.add(imported_by)
                integrations_scripts_mapping[imported_by.path.parent].update(
                    add_related_files(
                        api_module.path
                        if not api_module.path.is_absolute()
                        else api_module.path.relative_to(CONTENT_PATH)
                    )
                    | add_related_files(
                        imported_by.path
                        if not imported_by.path.is_absolute()
                        else imported_by.path.relative_to(CONTENT_PATH)
                    )
                )
        logger.debug("Pre-Commit: Finished handling API Modules")
    for integration_script in integrations_scripts:
        if (pack := integration_script.in_pack) and pack.object_id == API_MODULES_PACK:
            # we dont need to lint them individually, they will be run with the integrations that uses them
            continue
        if integration_script.deprecated:
            # we exclude deprecate integrations and scripts from pre-commit.
            # the reason we maintain this set is for performance when running with --all-files. It is much faster to exclude.
            if integration_script.is_unified:
                exclude_integration_script.add(
                    integration_script.path.relative_to(CONTENT_PATH)
                )
            else:
                exclude_integration_script.add(
                    integration_script.path.parent.relative_to(CONTENT_PATH)
                )
            continue

        code_file_path = integration_script.path.parent
        if python_version := integration_script.python_version:
            version = Version(python_version)
            language = f"{version.major}.{version.minor}"
        else:
            language = integration_script.type
        language_to_files[language].update(
            {
                (path, integration_script)
                for path in integrations_scripts_mapping[code_file_path]
            },
            {
                (
                    integration_script.path.relative_to(CONTENT_PATH)
                    if integration_script.path.is_absolute()
                    else integration_script.path,
                    integration_script,
                )
            },
        )

    if infra_files:
        language_to_files[DEFAULT_PYTHON_VERSION].update(
            [(infra, None) for infra in infra_files]
        )

    if exclude_integration_script:
        logger.info(
            f"Skipping deprecated integrations or scripts: {join_files(exclude_integration_script, ', ')}"
        )
    return language_to_files, exclude_integration_script


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    commited_only: bool = False,
    git_diff: bool = False,
    prev_version: Optional[str] = None,
    all_files: bool = False,
    mode: str = "",
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    secrets: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    dry_run: bool = False,
    run_docker_hooks: bool = True,
    image_ref: Optional[str] = None,
    docker_image: Optional[str] = None,
    run_hook: Optional[str] = None,
    pre_commit_template_path: Optional[Path] = None,
    json_output_path: Optional[Path] = None,
) -> int:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        staged_only (bool, optional): Whether to run on staged files only. Defaults to False.
        commited_only (bool, optional): Whether to run on commited files only. Defaults to False.
        git_diff (bool, optional): Whether use git to determine precommit files. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        mode (str): The mode to run pre-commit in. Defaults to empty str.
        skip_hooks (Optional[List[str]], optional): List of hooks to skip. Defaults to None.
        force_run_hooks (Optional[List[str]], optional): List for hooks to force run. Defaults to None.
        verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
        show_diff_on_failure (bool, optional): Whether show git diff after pre-commit failure. Defaults to False.
        dry_run (bool, optional): Whether to run the pre-commit hooks in dry-run mode, which will only create the
            config file.
        run_docker_hooks (bool, optional): Whether to run docker based hooks or not.
        image_ref: (str, optional): Override the image from YAML / native config file with this image reference.
        docker_image: (str, optional): Override the `docker_image` property in the template file. This is a comma
            separated list of: `from-yml`, `native:dev`, `native:ga`, `native:candidate`.
        pre_commit_template_path (Path, optional): Path to the template pre-commit file.
        json_output_path (Path, optional): Optional path to a JSON formatted output file/dir where pre-commit hooks results
            are stored. None by default, and file is not created.
    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, staged_only, git_diff, all_files)):
        logger.info("No arguments were given, running on staged files and git changes.")
        git_diff = True

    files_to_run = preprocess_files(
        input_files=input_files,
        staged_only=staged_only,
        commited_only=commited_only,
        use_git=git_diff,
        all_files=all_files,
        prev_version=prev_version,
    )
    if not files_to_run:
        logger.info("No files were changed, skipping pre-commit.")
        return 0

    language_to_files_with_objects, exclude_files = group_by_language(files_to_run)
    if not language_to_files_with_objects:
        logger.info("No files to run pre-commit on, skipping pre-commit.")
        return 0

    skipped_hooks: set = SKIPPED_HOOKS
    skipped_hooks.update(set(skip_hooks or ()))
    if validate and "validate" in skipped_hooks:
        skipped_hooks.remove("validate")
    if format and "format" in skipped_hooks:
        skipped_hooks.remove("format")
    if secrets and "secrets" in skipped_hooks:
        skipped_hooks.remove("secrets")

    if not pre_commit_template_path:
        if PRECOMMIT_TEMPLATE_PATH.exists():
            pre_commit_template_path = PRECOMMIT_TEMPLATE_PATH
        else:
            pre_commit_template_path = DEFAULT_PRE_COMMIT_TEMPLATE_PATH
    if pre_commit_template_path and not pre_commit_template_path.exists():
        logger.error(
            f"pre-commit template {pre_commit_template_path} does not exist, enter a valid pre-commit template"
        )
        return 1

    logger.info(f"Running pre-commit using template {pre_commit_template_path}")

    pre_commit_context = PreCommitContext(
        list(input_files) if input_files else None,
        all_files,
        mode,
        language_to_files_with_objects,
        run_hook,
        skipped_hooks,
        run_docker_hooks,
        image_ref,
        docker_image,
        pre_commit_template_path=pre_commit_template_path,
    )

    return PreCommitRunner.prepare_and_run(
        pre_commit_context,
        verbose,
        show_diff_on_failure,
        exclude_files,
        dry_run,
        json_output_path,
    )


def add_related_files(file: Path) -> Set[Path]:
    """This returns the related files set, including the original file
    If the file is `.yml`, it will add the `.py` file and the test file.
    If the file is `.py` or `.ps1`, it will add the tests file.

    Args:
        file (Path): The file to add related files for.

    Returns:
        Set[Path]: The set of related files.
    """
    files_to_run = {file}
    if ".yml" in file.suffix:
        py_file_path = file.with_suffix(".py")
        if py_file_path.exists():
            files_to_run.add(py_file_path)

    # Identifying test files by their suffix.
    if not {".py", ".ps1"}.intersection({file.suffix for file in files_to_run}):
        return files_to_run

    test_file_suffix = (
        PY_TEST_FILE_SUFFIX
        if ".py" in (file.suffix for file in files_to_run)
        else PS1_TEST_FILE_SUFFIX
    )
    test_files = []
    if file.parent.exists():
        test_files = [
            _file
            for _file in file.parent.iterdir()
            if _file.name.endswith(test_file_suffix)
        ]
        files_to_run.update(test_files)

    return files_to_run


def preprocess_files(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    commited_only: bool = False,
    use_git: bool = False,
    all_files: bool = False,
    prev_version: Optional[str] = None,
) -> Set[Path]:
    """Collect the list of files to run pre-commit on.

    Args:
        input_files (Optional[Iterable[Path]], optional): List of specific files. Defaults to None.
        staged_only (bool, optional): Whether to run only on staged files. Defaults to False.
        commited_only (bool, optional): Whether to run only on commited files. Defaults to False.
        use_git (bool, optional): Whether to only collect files using git. Defaults to False.
        all_files (bool, optional): Whether to collect all files. Defaults to False.
        prev_version (Optional[str], optional): The previous version to use as a delta when using git. Defaults to None.

    Raises:
        ValueError: If no input was given.

    Returns:
        Set[Path]: The set of files to run pre-commit on.
    """
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    all_git_files = git_util.get_all_files().union(staged_files)
    contribution_flow = os.getenv("CONTRIB_BRANCH")
    if input_files:
        raw_files = set(input_files)
    elif staged_only:
        raw_files = staged_files
    elif use_git:
        raw_files = git_util._get_all_changed_files(prev_version)
        if not commited_only:
            raw_files = raw_files.union(staged_files)
        if contribution_flow:
            """
            If this command runs on a build triggered by an external contribution PR,
            the relevant modified files initially have an "untracked" status in git.
            They are staged by Utils/update_contribution_pack_in_base_branch.py (Infra) which runs before pre-commit is triggered,
            so that pre-commit hooks can detect and run on said files.
            See CIAC-10968 for more info.
            """
            logger.info(
                "\n<cyan>CONTRIB_BRANCH environment variable found, running pre-commit in contribution flow "
                "on files staged by Utils/update_contribution_pack_in_base_branch.py (Infra repository)</cyan>"
            )
    elif all_files:
        raw_files = all_git_files
    else:
        raise ValueError(
            "No files were given to run pre-commit on, and no flags were given."
        )

    files_to_run: Set[Path] = set()
    for file in raw_files:
        if file.is_dir():
            files_to_run.update({path for path in file.rglob("*") if path.is_file()})
        else:
            files_to_run.update(add_related_files(file))
    # convert to relative file to content path
    relative_paths = {
        file.relative_to(CONTENT_PATH) if file.is_absolute() else file
        for file in files_to_run
    }
    # filter out files that are not in the content git repo (e.g in .gitignore)
    return relative_paths & all_git_files
