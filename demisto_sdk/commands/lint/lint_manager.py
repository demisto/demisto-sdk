# STD packages
import concurrent.futures
import os
import platform
import re
import sys
import textwrap
from typing import Any, Dict, List, Set, Tuple, Union

import docker
import docker.errors
import git
import requests.exceptions
import urllib3.exceptions
from packaging.version import Version
from wcmatch.pathlib import Path, PosixPath

import demisto_sdk
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    DEMISTO_GIT_PRIMARY_BRANCH,
    PACKS_PACK_META_FILE_NAME,
    TYPE_PWSH,
    TYPE_PYTHON,
    DemistoException,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.docker_helper import init_global_docker_client
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.timers import report_time_measurements
from demisto_sdk.commands.common.tools import (
    find_file,
    find_type,
    get_file_displayed_name,
    get_json,
    is_external_repository,
)
from demisto_sdk.commands.content_graph.commands.update import (
    update_content_graph,
)
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.lint.helpers import (
    EXIT_CODES,
    FAIL,
    PWSH_CHECKS,
    PY_CHCEKS,
    SUCCESS,
    build_skipped_exit_code,
    generate_coverage_report,
    get_test_modules,
)
from demisto_sdk.commands.lint.linter import DockerImageFlagOption, Linter

# Third party packages

# Local packages

sha1Regex = re.compile(r"\b[0-9a-fA-F]{40}\b", re.M)


class LintManager:
    """LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        input(str): Directories to run lint on.
        git(bool): Perform lint and test only on chaged packs.
        all_packs(bool): Whether to run on all packages.
        log_path(str): Path to all levels of logs.
        prev_ver(str): Previous branch or SHA1 commit to run checks against.
        json_file_path(str): Path to a json file to write the run resutls to.
        id_set_path(str): Path to an existing id_set.json.
        check_dependent_api_module(bool): Whether to run lint also on the packs dependent on the modified api modules
        files.
    """

    def __init__(
        self,
        input: str,
        git: bool,
        all_packs: bool,
        prev_ver: str,
        json_file_path: str = "",
        check_dependent_api_module: bool = False,
    ):

        # Gather facts for manager
        self._facts: dict = self._gather_facts()
        self._prev_ver = prev_ver
        self._all_packs = all_packs
        # Set 'git' to true if no packs have been specified, 'lint' should operate as 'lint -g'
        lint_no_packs_command = not git and not all_packs and not input
        git = True if lint_no_packs_command else git
        # Filter packages to lint and test check
        self._pkgs: List[PosixPath] = self._get_packages(
            content_repo=self._facts["content_repo"],
            input=input,
            git=git,
            all_packs=all_packs,
            base_branch=self._prev_ver,
        )

        if check_dependent_api_module:
            dependent_on_api_module = self._get_api_module_dependent_items()
            self._pkgs.extend(
                [
                    dependent_item
                    for dependent_item in dependent_on_api_module
                    if Path(dependent_item).parent not in self._pkgs
                ]
            )

            # Remove duplicates
            self._pkgs = list(set(self._pkgs))

        if json_file_path:
            if os.path.isdir(json_file_path):
                json_file_path = os.path.join(json_file_path, "lint_outputs.json")
        self.json_file_path = json_file_path
        self.linters_error_list: list = []
        self._git_modified_files = git

    def _get_api_module_dependent_items(self) -> list:
        changed_api_modules = {
            pkg.name for pkg in self._pkgs if API_MODULES_PACK in pkg.parts
        }
        if changed_api_modules:
            dependent_items = []
            for changed_api_module in changed_api_modules:
                logger.info(
                    f"Checking for packages dependent on the modified API module {changed_api_module}..."
                )

                with ContentGraphInterface() as graph:
                    logger.info("Updating graph...")
                    update_content_graph(graph, use_git=True, dependencies=True)

                    api_module_nodes = graph.search(object_id=changed_api_module)
                    api_module_node = api_module_nodes[0] if api_module_nodes else None
                    if not api_module_node:
                        raise ValueError(
                            f"The modified API module `{changed_api_module}` was not found in the "
                            f"content graph. Please check that it is up to date, and run"
                            f" `demisto-sdk update-content-graph` if necessary."
                        )

                    dependent_items += [
                        dependency.path for dependency in api_module_node.imported_by
                    ]

            dependent_on_api_module = self._get_packages(
                content_repo=self._facts["content_repo"], input=dependent_items
            )

            if dependent_on_api_module:
                logger.info(
                    f"Found [cyan]{len(dependent_on_api_module)}[/cyan] dependent packages. "
                    f"Executing lint and test on those as well."
                )
                return dependent_on_api_module
            logger.info("No dependent packages found.")
        return []

    @staticmethod
    def _gather_facts() -> Dict[str, Any]:
        """Gather shared required facts for lint command execution - Also perform mandatory resource checkup.
            1. Content repo object.
            2. Requirements file for docker images.
            3. Mandatory test modules - demisto-mock.py etc
            3. Docker daemon check.

        Returns:
            dict: facts
        """
        global logger
        facts = {
            "content_repo": None,
            "requirements_3": None,
            "requirements_2": None,
            "test_modules": None,
            "docker_engine": True,
        }
        # Get content repo object
        is_external_repo = False
        try:
            git_repo = GitUtil()
            remote_url = git_repo.repo.remote().urls.__next__()
            is_fork_repo = "content" in remote_url
            is_external_repo = is_external_repository()

            if not is_fork_repo and not is_external_repo:
                raise git.InvalidGitRepositoryError

            facts["content_repo"] = git_repo  # type: ignore
            logger.debug(f"Content path {git_repo.repo.working_dir}")
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            logger.info(
                "[yellow]You are running demisto-sdk lint not in content repository![yellow]"
            )
            logger.warning(f"can't locate content repo {e}")
        # Get global requirements file
        # ￿Get mandatory modulestest modules and Internet connection for docker usage
        try:
            facts["test_modules"] = get_test_modules(
                content_repo=facts["content_repo"],  # type: ignore
                is_external_repo=is_external_repo,
            )
            logger.debug("Test mandatory modules successfully collected.")
        except (git.GitCommandError, DemistoException) as e:
            if is_external_repo:
                logger.error(
                    "When running on an external repository, you are required to first run "
                    "the '.hooks/bootstrap' script before running the demisto-sdk lint command.\n"
                    "For additional information, refer to: https://xsoar.pan.dev/docs/concepts/dev-setup"
                )
            else:
                logger.error(
                    "Unable to fetch mandatory files (test-modules, demisto-mock.py, etc.) - "
                    "corrupt repository or pull from master. Aborting!"
                )
            logger.error(
                f"demisto-sdk-unable to fetch mandatory files (test-modules, demisto-mock.py, etc.): {e}"
            )
            sys.exit(1)
        except (
            requests.exceptions.ConnectionError,
            urllib3.exceptions.NewConnectionError,
        ) as e:
            logger.info(
                "[red]Unable to get mandatory test-modules demisto-mock.py etc - Aborting! (Check your internet "
                "connection)[/red]"
            )
            logger.error(
                f"demisto-sdk-unable to get mandatory test-modules demisto-mock.py etc {e}"
            )
            sys.exit(1)
        # Validating docker engine connection
        logger.debug("creating docker client from env")

        try:
            docker_client: docker.DockerClient = init_global_docker_client(log_prompt="LintManager")  # type: ignore
            logger.debug("pinging docker daemon")
            docker_client.ping()
        except (
            docker.errors.DockerException,
            demisto_sdk.commands.common.docker_helper.DockerException,
            requests.exceptions.ConnectionError,
            urllib3.exceptions.ProtocolError,
            docker.errors.APIError,
        ) as ex:
            if os.getenv("CI") and os.getenv("CIRCLE_PROJECT_REPONAME") == "content":
                # when running lint in content we fail if docker isn't available for some reason
                raise ValueError(
                    "Docker engine not available and we are in content CI env. Can not run lint!!"
                ) from ex
            facts["docker_engine"] = False
            logger.info(
                "[yellow]Can't communicate with Docker daemon - check your docker Engine is ON - Skipping lint, "
                "test which require docker![yellow]"
            )
            logger.info("can not communicate with Docker daemon")
        logger.debug("Docker daemon test passed")
        return facts

    def _get_packages(
        self,
        content_repo: GitUtil,
        input: Union[str, List[str]],
        git: bool = False,
        all_packs: bool = False,
        base_branch: str = DEMISTO_GIT_PRIMARY_BRANCH,
    ) -> List[PosixPath]:
        """Get packages paths to run lint command.

        Args:
            content_repo(git.Repo): Content repository object.
            input(str): dir pack specified as argument.
            git(bool): Perform lint and test only on changed packs.
            all_packs(bool): Whether to run on all packages.
            base_branch (str): Name of the branch or sha1 commit to run the diff on.

        Returns:
            List[PosixPath]: Pkgs to run lint
        """
        pkgs: list
        if all_packs or git:
            pkgs = LintManager._get_all_packages(content_dir=content_repo.repo.working_dir)  # type: ignore
        else:  # specific pack as input, -i flag has been used
            pkgs = []
            if isinstance(input, str):
                input = input.split(",")
            for item in input:
                is_pack = (
                    Path(item).is_dir()
                    and Path(item, PACKS_PACK_META_FILE_NAME).exists()
                )
                if is_pack:
                    pkgs.extend(LintManager._get_all_packages(content_dir=item))
                else:
                    pkgs.append(Path(item))
        if git:
            pkgs = self._filter_changed_packages(
                content_repo=content_repo, pkgs=pkgs, base_branch=base_branch
            )
            for pkg in pkgs:
                logger.debug(f"Found changed package [cyan]{pkg}[/cyan]")
        if pkgs:
            pkgs_str = ", ".join(map(str, pkgs))
            logger.info(
                f"Executing lint and test on integrations and scripts in [cyan]{pkgs_str}[/cyan]"
            )

        return pkgs

    @staticmethod
    def _get_all_packages(content_dir: str) -> List[str]:
        """Gets all integration, script in packages and packs in content repo.

        Returns:
            list: A list of integration, script and beta_integration names.
        """
        # Get packages from main content path
        content_main_pkgs: set = set(
            Path(content_dir).glob(
                [
                    "Integrations/*/",
                    "Scripts/*/",
                ]
            )
        )
        # Get packages from packs path
        packs_dir: Path = Path(content_dir) / "Packs"
        content_packs_pkgs: set = set(
            packs_dir.glob(["*/Integrations/*/", "*/Scripts/*/"])
        )
        all_pkgs = content_packs_pkgs.union(content_main_pkgs)

        return list(all_pkgs)

    @staticmethod
    def _get_packages_from_modified_files(modified_files):
        r"""
        Out of all modified files, return only the files relevant for linting, which are the packages
        (scripts\integrations) under the pack.
        Args:
            modified_files: A list of paths of files recognized as modified.

        Returns:
            A list of paths of modified packages (scripts/integrations)
        """
        return [
            path
            for path in modified_files
            if "Scripts" in path.parts or "Intergations" in path.parts
        ]

    @staticmethod
    def _filter_changed_packages(
        content_repo: GitUtil, pkgs: List[PosixPath], base_branch: str
    ) -> List[PosixPath]:
        """Checks which packages had changes in them and should run on Lint.
        The diff is calculated using git, and is done by the following cases:
        - case 1: If the active branch is 'master', the diff is between master and the previous commit.
        - case 2: If the active branch is not master, and no other base branch is specified to comapre to,
         the diff is between the active branch and master.
        - case 3: If the base branch is specified, the diff is between the active branch (master\not master) and the given base branch.

        Args:
            pkgs(List[PosixPath]): pkgs to check
            base_branch (str): Name of the branch or sha1 commit to run the diff on.

        Returns:
            List[PosixPath]: A list of names of packages that should run.
        """
        try:
            active_branch = content_repo.repo.active_branch
            commit = active_branch.commit
            branch_name = active_branch.name
        except TypeError as error:
            logger.debug(f"Could not get active branch, {error}")
            commit = content_repo.get_commit(
                content_repo.repo.head.object.hexsha, from_remote=False
            )
            branch_name = ""

        logger.debug(f"{commit=}, {branch_name=}")

        staged_files = {
            content_repo.repo.working_dir / Path(item.b_path).parent  # type: ignore[operator]
            for item in commit.tree.diff(None, paths=pkgs)
        }

        if (
            base_branch == DEMISTO_GIT_PRIMARY_BRANCH
            and branch_name == DEMISTO_GIT_PRIMARY_BRANCH
        ):
            # case 1: comparing master against the latest previous commit
            last_common_commit = (
                content_repo.repo.remote().refs[base_branch].commit.parents[0]
            )
            logger.info(
                f"Comparing [cyan]master[/cyan] to its [cyan]previous commit: "
                f"{last_common_commit}"
            )

        else:
            # cases 2+3: compare the active branch (master\not master) against the given base branch (master\not master)
            if sha1Regex.match(
                base_branch
            ):  # if the base branch is given as a commit hash
                last_common_commit = base_branch
            else:
                last_common_commit = content_repo.repo.merge_base(
                    commit,
                    f"{content_repo.repo.remote()}/{base_branch}",
                )[0]
            if branch_name:
                logger.info(
                    f"Comparing [cyan]{branch_name}[/cyan] to"
                    f" last common commit with [cyan]{last_common_commit}[/cyan]"
                )

        changed_from_base = {
            content_repo.repo.working_dir / Path(item.b_path).parent  # type: ignore[operator]
            for item in commit.tree.diff(last_common_commit, paths=pkgs)
        }
        all_changed = staged_files.union(changed_from_base)
        pkgs_to_check = all_changed.intersection(pkgs)

        return list(pkgs_to_check)  # type: ignore

    def execute_all_packages(
        self,
        parallel: int,
        no_flake8: bool,
        no_xsoar_linter: bool,
        no_bandit: bool,
        no_mypy: bool,
        no_pylint: bool,
        no_coverage: bool,
        no_vulture: bool,
        no_test: bool,
        no_pwsh_analyze: bool,
        no_pwsh_test: bool,
        keep_container: bool,
        test_xml: str,
        docker_timeout: int,
        docker_image_flag: str,
        docker_image_target: str,
        lint_status: dict,
        pkgs_status: dict,
        pkgs_type: list,
    ) -> Tuple[int, int]:
        """Runs the Lint command on all given packages.

        Args:
            parallel(int): Whether to run command on multiple threads
            no_flake8(bool): Whether to skip flake8
            no_xsoar_linter(bool): Whether to skip xsoar linter
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint
            no_coverage(bool): Run pytest without coverage report
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            docker_timeout(int): timeout for docker requests
            docker_image_flag(str): indicates the desirable docker image to run lint on
            docker_image_target(str): The docker image to lint native supported content with
            pkgs_type: List of the pack types
            pkgs_status: Dictionary for pack status (keys are packs, the values are their status)
            lint_status: Dictionary for the lint status  (the keys are the linters, the values are a list of packs)

        Returns:
            Tuple[int, int]: exit code, warning code
        """
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=parallel
            ) as executor:
                return_exit_code: int = 0
                return_warning_code: int = 0
                results = []
                # Executing lint checks in different threads
                for pack in sorted(self._pkgs):
                    linter: Linter = Linter(
                        pack_dir=pack,
                        content_repo=""
                        if not self._facts["content_repo"]
                        else Path(  # type: ignore
                            self._facts["content_repo"].repo.working_dir
                        ),
                        docker_engine=self._facts["docker_engine"],
                        docker_timeout=docker_timeout,
                        docker_image_flag=docker_image_flag,
                        docker_image_target=docker_image_target,
                        all_packs=self._all_packs,
                        use_git=self._git_modified_files,
                    )
                    results.append(
                        executor.submit(
                            linter.run_pack,
                            no_flake8=no_flake8,
                            no_bandit=no_bandit,
                            no_mypy=no_mypy,
                            no_vulture=no_vulture,
                            no_xsoar_linter=no_xsoar_linter,
                            no_pylint=no_pylint,
                            no_test=no_test,
                            no_pwsh_analyze=no_pwsh_analyze,
                            no_pwsh_test=no_pwsh_test,
                            modules=self._facts["test_modules"],
                            keep_container=keep_container,
                            test_xml=test_xml,
                            no_coverage=no_coverage,
                        )
                    )

                logger.debug("Waiting for futures to complete")
                for i, future in enumerate(concurrent.futures.as_completed(results)):
                    logger.debug(f"checking output of future {i=}")
                    pkg_status = future.result()
                    logger.debug(f'Got lint results for {pkg_status["pkg"]}')
                    pkgs_status[pkg_status["pkg"]] = pkg_status
                    if pkg_status["exit_code"]:
                        for check, code in EXIT_CODES.items():
                            if pkg_status["exit_code"] & code:
                                lint_status[f"fail_packs_{check}"].append(
                                    pkg_status["pkg"]
                                )

                        if not return_exit_code & pkg_status["exit_code"]:
                            return_exit_code += pkg_status["exit_code"]
                    if pkg_status["warning_code"]:
                        for check, code in EXIT_CODES.items():
                            if pkg_status["warning_code"] & code:
                                lint_status[f"warning_packs_{check}"].append(
                                    pkg_status["pkg"]
                                )
                        if not return_warning_code & pkg_status["warning_code"]:
                            return_warning_code += pkg_status["warning_code"]
                    if pkg_status["pack_type"] not in pkgs_type:
                        pkgs_type.append(pkg_status["pack_type"])
                logger.debug("Finished all futures")
                return return_exit_code, return_warning_code
        except KeyboardInterrupt:
            msg = "Stop demisto-sdk lint - Due to 'Ctrl C' signal"
            logger.info(f"[yellow]{msg}[/yellow]")
            logger.warning(msg)
            executor.shutdown(
                wait=False
            )  # If keyboard interrupt no need to wait to clean resources
            return 1, 0
        except Exception as e:
            msg = f"Stop demisto-sdk lint - {e}"
            logger.debug(f"[yellow]{msg}[/yellow]", exc_info=True)

            if Version(platform.python_version()) > Version("3.9"):
                executor.shutdown(wait=True, cancel_futures=True)  # type: ignore[call-arg]
            else:
                logger.info("Using Python under 3.8, we will cancel futures manually.")
                executor.shutdown(
                    wait=True
                )  # Note that `cancel_futures` not supported in python 3.8
                for res in results:
                    res.cancel()
            return 1, 0

    def run(
        self,
        parallel: int,
        no_flake8: bool,
        no_xsoar_linter: bool,
        no_bandit: bool,
        no_mypy: bool,
        no_pylint: bool,
        no_coverage: bool,
        coverage_report: str,
        no_vulture: bool,
        no_test: bool,
        no_pwsh_analyze: bool,
        no_pwsh_test: bool,
        keep_container: bool,
        test_xml: str,
        failure_report: str,
        docker_timeout: int,
        docker_image_flag: str,
        docker_image_target: str,
        time_measurements_dir: str = None,
    ) -> int:
        """Runs the Lint command on all given packages.

        Args:
            parallel(int): Whether to run command on multiple threads
            no_flake8(bool): Whether to skip flake8
            no_xsoar_linter(bool): Whether to skip xsoar linter
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint
            no_coverage(bool): Run pytest without coverage report
            coverage_report(str): the directory fo exporting the coverage data
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            failure_report(str): Path for store failed packs report
            docker_timeout(int): timeout for docker requests
            docker_image_flag(str): indicates the desirable docker image to run lint on
            docker_image_target(str): The docker image to lint native supported content with
            time_measurements_dir(str): the directory fo exporting the time measurements info
            total_timeout (int): amount of seconds for the task

        Returns:
            int: exit code by fail exit codes by var EXIT_CODES
        """
        lint_status: Dict = {
            "fail_packs_flake8": [],
            "fail_packs_XSOAR_linter": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_vulture": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_pwsh_analyze": [],
            "fail_packs_pwsh_test": [],
            "fail_packs_image": [],
            "warning_packs_flake8": [],
            "warning_packs_XSOAR_linter": [],
            "warning_packs_bandit": [],
            "warning_packs_mypy": [],
            "warning_packs_vulture": [],
            "warning_packs_pylint": [],
            "warning_packs_pytest": [],
            "warning_packs_pwsh_analyze": [],
            "warning_packs_pwsh_test": [],
            "warning_packs_image": [],
        }

        # Python or powershell or both
        pkgs_type: list = []

        # Detailed packages status
        pkgs_status: dict = {}

        # Check docker image flags are in order
        if (
            docker_image_target
            and docker_image_flag != DockerImageFlagOption.NATIVE_TARGET.value
        ):
            raise ValueError(
                f"Recieved docker image target {docker_image_target} without docker "
                f"image flag {DockerImageFlagOption.NATIVE_TARGET.value}. Aborting."
            )

        # Skipped lint and test codes
        skipped_code = build_skipped_exit_code(
            no_flake8=no_flake8,
            no_bandit=no_bandit,
            no_mypy=no_mypy,
            no_vulture=no_vulture,
            no_xsoar_linter=no_xsoar_linter,
            no_pylint=no_pylint,
            no_test=no_test,
            no_pwsh_analyze=no_pwsh_analyze,
            no_pwsh_test=no_pwsh_test,
            docker_engine=self._facts["docker_engine"],
        )

        return_exit_code, return_warning_code = self.execute_all_packages(
            parallel=parallel,
            no_flake8=no_flake8,
            no_xsoar_linter=no_xsoar_linter,
            no_bandit=no_bandit,
            no_mypy=no_mypy,
            no_pylint=no_pylint,
            no_coverage=no_coverage,
            no_vulture=no_vulture,
            no_test=no_test,
            no_pwsh_test=no_pwsh_test,
            keep_container=keep_container,
            test_xml=test_xml,
            docker_timeout=docker_timeout,
            docker_image_flag=docker_image_flag,
            docker_image_target=docker_image_target,
            no_pwsh_analyze=no_pwsh_analyze,
            lint_status=lint_status,
            pkgs_status=pkgs_status,
            pkgs_type=pkgs_type,
        )

        if time_measurements_dir:
            report_time_measurements(
                group_name="lint", time_measurements_dir=time_measurements_dir
            )

        self._report_results(
            lint_status=lint_status,
            pkgs_status=pkgs_status,
            return_exit_code=return_exit_code,
            return_warning_code=return_warning_code,
            skipped_code=int(skipped_code),
            pkgs_type=pkgs_type,
            no_coverage=no_coverage,
            coverage_report=coverage_report,
        )

        self._create_failed_packs_report(lint_status=lint_status, path=failure_report)

        # check if there were any errors during lint run , if so set to FAIL as some error codes are bigger
        # then 512 and will not cause failure on the exit code.
        if return_exit_code:
            # allow all_packs to fail on mypy
            if self._all_packs and return_exit_code == EXIT_CODES["mypy"]:
                return_exit_code = SUCCESS
            else:
                return_exit_code = FAIL
        return return_exit_code

    def _report_results(
        self,
        lint_status: dict,
        pkgs_status: dict,
        return_exit_code: int,
        return_warning_code: int,
        skipped_code: int,
        pkgs_type: list,
        no_coverage: bool,
        coverage_report: str,
    ):
        """Log report to console

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
            return_warning_code(int): warning code will indicate which lint or test caused warning messages
            skipped_code(int): skipped test code
            pkgs_type(list): list determine which pack type exits.
            no_coverage(bool): Do NOT create coverage report.

        """
        if not no_coverage:
            if coverage_report:
                generate_coverage_report(html=True, xml=True, cov_dir=coverage_report)
            else:
                generate_coverage_report()

        self.report_pass_lint_checks(
            return_exit_code=return_exit_code,
            skipped_code=skipped_code,
            pkgs_type=pkgs_type,
        )
        self.report_warning_lint_checks(
            return_warning_code=return_warning_code,
            pkgs_status=pkgs_status,
            lint_status=lint_status,
            all_packs=self._all_packs,
        )
        self.report_unit_tests(
            return_exit_code=return_exit_code,
            pkgs_status=pkgs_status,
            lint_status=lint_status,
        )
        self.report_failed_lint_checks(
            return_exit_code=return_exit_code,
            pkgs_status=pkgs_status,
            lint_status=lint_status,
        )

        self.report_failed_image_creation(
            return_exit_code=return_exit_code,
            pkgs_status=pkgs_status,
            lint_status=lint_status,
        )

        self.report_summary(
            pkg=self._pkgs,
            pkgs_status=pkgs_status,
            lint_status=lint_status,
            all_packs=self._all_packs,
        )
        self.create_json_output()

    @staticmethod
    def report_pass_lint_checks(
        return_exit_code: int, skipped_code: int, pkgs_type: list
    ):
        """Log PASS/FAIL on each lint/test

        Args:
            return_exit_code(int): exit code will indicate which lint or test failed
            skipped_code(int): skipped test code.
            pkgs_type(list): list determine which pack type exits.
        """
        longest_check_key = len(max(EXIT_CODES.keys(), key=len))
        for check, code in EXIT_CODES.items():
            spacing = longest_check_key - len(check)
            if "XSOAR_linter" in check:
                check_str = check.replace("_", " ")
            else:
                check_str = check.capitalize().replace("_", " ")
            if (check in PY_CHCEKS and TYPE_PYTHON in pkgs_type) or (
                check in PWSH_CHECKS and TYPE_PWSH in pkgs_type
            ):
                if code & skipped_code:
                    logger.info(f"{check_str} {' ' * spacing}- [cyan][SKIPPED][/cyan]")
                elif code & return_exit_code:
                    logger.info(f"{check_str} {' ' * spacing}- [red][FAIL][/red]")
                else:
                    logger.info(f"{check_str} {' ' * spacing}- [green][PASS][/green]")
            elif check != "image":
                logger.info(f"{check_str} {' ' * spacing}- [cyan][SKIPPED][/cyan]")

    def report_failed_lint_checks(
        self, lint_status: dict, pkgs_status: dict, return_exit_code: int
    ):
        """Log failed lint log if exsits

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        for check in ["flake8", "XSOAR_linter", "bandit", "mypy", "vulture"]:
            if EXIT_CODES[check] & return_exit_code:
                sentence = f" {check.capitalize()} errors "
                logger.info(f"\n[red]{'#' * len(sentence)}[/red]")
                logger.info(f"[red]{sentence}[/red]")
                logger.info(f"[red]{'#' * len(sentence)}[/red]\n")
                for fail_pack in lint_status[f"fail_packs_{check}"]:
                    logger.info(f"[red]{pkgs_status[fail_pack]['pkg']}[/red]")
                    logger.info(pkgs_status[fail_pack][f"{check}_errors"])
                    self.linters_error_list.append(
                        {
                            "linter": check,
                            "pack": fail_pack,
                            "type": "error",
                            "messages": pkgs_status[fail_pack][f"{check}_errors"],
                        }
                    )

        for check in ["pylint", "pwsh_analyze", "pwsh_test"]:
            check_str = check.capitalize().replace("_", " ")
            if EXIT_CODES[check] & return_exit_code:
                sentence = f" {check_str} errors "
                logger.info(f"\n[red]{'#' * len(sentence)}[/red]")
                logger.info(f"[red]{sentence}[/red]")
                logger.info(f"[red]{'#' * len(sentence)}[/red]\n")
                for fail_pack in lint_status[f"fail_packs_{check}"]:
                    logger.info(f"[red]{fail_pack}[/red]")
                    for image in pkgs_status[fail_pack]["images"]:
                        logger.info(image[f"{check}_errors"])

    def report_warning_lint_checks(
        self,
        lint_status: dict,
        pkgs_status: dict,
        return_warning_code: int,
        all_packs: bool,
    ):
        """Log warnings lint log if exists

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_warning_code(int): exit code will indicate which lint or test caused warnings
            all_packs(bool) if all packs runs then no need for warnings messages.
        """
        if not all_packs:
            for check in ["flake8", "XSOAR_linter", "bandit", "mypy", "vulture"]:
                if EXIT_CODES[check] & return_warning_code:
                    sentence = f" {check.capitalize()} warnings "
                    logger.info(f"\n[orange]{'#' * len(sentence)}[/orange]")
                    logger.info(f"[orange]{sentence}[/orange]")
                    logger.info(f"[orange]{'#' * len(sentence)}[/orange]\n")
                    for fail_pack in lint_status[f"warning_packs_{check}"]:
                        logger.info(f"[orange]{pkgs_status[fail_pack]['pkg']}[/orange]")
                        logger.info(pkgs_status[fail_pack][f"{check}_warnings"])
                        self.linters_error_list.append(
                            {
                                "linter": check,
                                "pack": fail_pack,
                                "type": "warning",
                                "messages": pkgs_status[fail_pack][f"{check}_warnings"],
                            }
                        )

    def report_unit_tests(
        self, lint_status: dict, pkgs_status: dict, return_exit_code: int
    ):
        """Log failed unit-tests , if verbosity specified will log also success unit-tests

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        # Indentation config
        preferred_width = 100
        pack_indent = 2
        pack_prefix = " " * pack_indent + "- Package: "
        wrapper_pack = textwrap.TextWrapper(
            initial_indent=pack_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(pack_prefix),
        )
        docker_indent = 6
        docker_prefix = " " * docker_indent + "- Image: "
        wrapper_docker_image = textwrap.TextWrapper(
            initial_indent=docker_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(docker_prefix),
        )
        test_indent = 9
        test_prefix = " " * test_indent + "- "
        wrapper_test = textwrap.TextWrapper(
            initial_indent=test_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(test_prefix),
        )
        error_indent = 9
        error_first_prefix = " " * error_indent + "  Error: "
        error_sec_prefix = " " * error_indent + "         "
        wrapper_first_error = textwrap.TextWrapper(
            initial_indent=error_first_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(error_first_prefix),
        )
        wrapper_sec_error = textwrap.TextWrapper(
            initial_indent=error_sec_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(error_sec_prefix),
        )

        # Log passed unit-tests
        headline_printed = False
        passed_printed = False
        for pkg, status in pkgs_status.items():
            if status.get("images"):
                if (
                    status.get("images")[0]
                    .get("pytest_json", {})
                    .get("report", {})
                    .get("tests")
                ):
                    if (not headline_printed) and (
                        EXIT_CODES["pytest"] & return_exit_code
                    ):
                        # Log unit-tests
                        sentence = " Unit Tests "
                        logger.debug(f"\n[cyan]{'#' * len(sentence)}")
                        logger.debug(f"{sentence}")
                        logger.debug(f"{'#' * len(sentence)}")
                        headline_printed = True
                    if not passed_printed:
                        logger.debug("\n[green]Passed Unit-tests:[/green]")
                        passed_printed = True
                    logger.debug(wrapper_pack.fill(f"[green]{pkg}[/green]"))
                    for image in status["images"]:
                        if not image.get("image_errors"):
                            tests = (
                                image.get("pytest_json", {})
                                .get("report", {})
                                .get("tests")
                            )
                            if tests:
                                logger.debug(wrapper_docker_image.fill(image["image"]))
                                for test_case in tests:
                                    outcome = test_case.get("call", {}).get("outcome")
                                    if outcome != "failed":
                                        name = re.sub(
                                            pattern=r"\[.*\]",
                                            repl="",
                                            string=test_case.get("name"),
                                        )
                                        if outcome and outcome != "passed":
                                            name = f"{name} ({outcome.upper()})"
                                        logger.debug(wrapper_test.fill(name))

        # Log failed unit-tests
        if EXIT_CODES["pytest"] & return_exit_code:
            if not headline_printed:
                # Log unit-tests
                sentence = " Unit Tests "
                logger.info(f"\n[cyan]{'#' * len(sentence)}")
                logger.info(f"{sentence}")
                logger.info(f"{'#' * len(sentence)}")
            logger.info("\n[red]Failed Unit-tests:[/red]")
            for fail_pack in lint_status["fail_packs_pytest"]:
                logger.info(wrapper_pack.fill(f"[red]{fail_pack}[/red]"))
                for image in pkgs_status[fail_pack]["images"]:
                    tests = image.get("pytest_json", {}).get("report", {}).get("tests")
                    if tests:
                        for test_case in tests:
                            if test_case.get("call", {}).get("outcome") == "failed":
                                name = re.sub(
                                    pattern=r"\[.*\]",
                                    repl="",
                                    string=test_case.get("name"),
                                )
                                logger.info(wrapper_test.fill(name))
                                if test_case.get("call", {}).get("longrepr"):
                                    logger.info(
                                        wrapper_docker_image.fill(image["image"])
                                    )
                                    for i in range(
                                        len(test_case.get("call", {}).get("longrepr"))
                                    ):
                                        if i == 0:
                                            logger.info(
                                                wrapper_first_error.fill(
                                                    test_case.get("call", {}).get(
                                                        "longrepr"
                                                    )[i]
                                                )
                                            )
                                        else:
                                            logger.info(
                                                wrapper_sec_error.fill(
                                                    test_case.get("call", {}).get(
                                                        "longrepr"
                                                    )[i]
                                                )
                                            )
                                    logger.info("\n")
                    else:
                        logger.info(wrapper_docker_image.fill(image["image"]))
                        errors = image.get("pytest_errors", {})
                        if errors:
                            logger.info(wrapper_sec_error.fill(errors))

    @staticmethod
    def report_failed_image_creation(
        lint_status: dict, pkgs_status: dict, return_exit_code: int
    ):
        """Log failed image creation if occured

        Args:
            lint_status(dict): Overall lint status
            pkgs_status(dict): All pkgs status dict
            return_exit_code(int): exit code will indicate which lint or test failed
        """
        # Indentation config
        preferred_width = 100
        indent = 2
        pack_prefix = " " * indent + "- Package: "
        wrapper_pack = textwrap.TextWrapper(
            initial_indent=pack_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(pack_prefix),
        )
        image_prefix = " " * indent + "  Image: "
        wrapper_image = textwrap.TextWrapper(
            initial_indent=image_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(image_prefix),
        )
        indent_error = 4
        error_prefix = " " * indent_error + "  Error: "
        wrapper_error = textwrap.TextWrapper(
            initial_indent=error_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(error_prefix),
        )
        # Log failed images creation
        if EXIT_CODES["image"] & return_exit_code:
            sentence = " Image creation errors "
            logger.info(f"\n[red]{'#' * len(sentence)}[/red]")
            logger.info(f"[red]{sentence}[/red]")
            logger.info(f"[red]{'#' * len(sentence)}[/red]")
            for fail_pack in lint_status["fail_packs_image"]:
                logger.info(wrapper_pack.fill(f"[cyan]{fail_pack}[/cyan]"))
                for image in pkgs_status[fail_pack]["images"]:
                    logger.info(wrapper_image.fill(image["image"]))
                    logger.info(wrapper_error.fill(image["image_errors"]))

    @staticmethod
    def report_summary(
        pkg, pkgs_status: dict, lint_status: dict, all_packs: bool = False
    ):
        """Log failed image creation if occured

        Args:
            pkgs_status: The packs status
            lint_status(dict): Overall lint status
            all_packs(bool): True when running lint command with -a flag.
        """
        preferred_width = 100
        fail_pack_indent = 3
        fail_pack_prefix = " " * fail_pack_indent + "- "
        wrapper_fail_pack = textwrap.TextWrapper(
            initial_indent=fail_pack_prefix,
            width=preferred_width,
            subsequent_indent=" " * len(fail_pack_prefix),
        )
        # intersection of all failed packages
        failed: Set[str] = set()

        # intersection of all warnings packages
        warnings: Set[str] = set()
        # each pack is checked for warnings and failures . A certain pack can appear in both failed packages and
        # warnings packages.
        for key in lint_status:
            # ignore mypy errors in all_packs report
            if all_packs and "mypy" in key:
                continue

            if key.startswith("fail"):
                failed = failed.union(lint_status[key])
            if key.startswith("warning"):
                warnings = warnings.union(lint_status[key])
        if all_packs:
            num_passed = len(
                [
                    pack
                    for pack, result in pkgs_status.items()
                    if result.get("exit_code") == 0
                    or result.get("exit_code") == EXIT_CODES["mypy"]
                ]
            )
        else:
            num_passed = len(
                [
                    pack
                    for pack, result in pkgs_status.items()
                    if result.get("exit_code") == 0
                ]
            )
        # Log unit-tests summary
        sentence = " Summary "
        logger.info(f"\n[cyan]{'#' * len(sentence)}")
        logger.info(f"{sentence}")
        logger.info(f"{'#' * len(sentence)}")
        logger.info(f"Packages: {len(pkg)}")
        logger.info(f"Packages PASS: [green]{num_passed}[/green]")
        logger.info(f"Packages FAIL: [red]{len(failed)}[/red]")
        logger.info(
            f"Packages WARNING (can either PASS or FAIL): [orange]{len(warnings)}[/orange]\n"
        )

        if not all_packs:
            if warnings:
                logger.info("Warning packages:")
            for warning in warnings:
                logger.info(f"[orange]{wrapper_fail_pack.fill(warning)}[/orange]")

        if failed:
            logger.info("Failed packages:")
        for fail_pack in failed:
            if fail_pack:
                logger.info(f"[red]{wrapper_fail_pack.fill(fail_pack)}[/red]")

    @staticmethod
    def _create_failed_packs_report(lint_status: dict, path: str):
        """
        Creates and saves a file containing all lint failed packs
        :param lint_status: dict
            Dictionary containing type of failures and corresponding failing tests. Looks like this:
             lint_status = {
            "fail_packs_flake8": [],
            "fail_packs_bandit": [],
            "fail_packs_mypy": [],
            "fail_packs_vulture": [],
            "fail_packs_pylint": [],
            "fail_packs_pytest": [],
            "fail_packs_pwsh_analyze": [],
            "fail_packs_pwsh_test": [],
            "fail_packs_image": []
        }
        :param path: str
            The path to save the report.
        """
        failed_ut: set = set()
        for key in lint_status:
            if (
                key.startswith("fail") and "mypy" not in key
            ):  # TODO remove this when reduce the number of failed `mypy` packages.
                failed_ut = failed_ut.union(lint_status[key])
        failed_unit_tests = [str(item) for item in failed_ut if item is not None]
        if path and failed_unit_tests:
            file_path = Path(path) / "failed_lint_report.txt"
            file_path.write_text("\n".join(failed_unit_tests))

    def create_json_output(self):
        """Creates a JSON file output for lints"""
        if not self.json_file_path:
            return

        if Path(self.json_file_path).exists():
            json_contents = get_json(self.json_file_path)
            if not (isinstance(json_contents, list)):
                json_contents = []
        else:
            json_contents = []
        logger.info("Collecting results to write to file")
        # format all linters to JSON format -
        # if any additional linters are added, please add a formatting function here
        for check in self.linters_error_list:
            if check.get("linter") == "flake8":
                self.flake8_error_formatter(check, json_contents)
            elif check.get("linter") == "mypy":
                self.mypy_error_formatter(check, json_contents)
            elif check.get("linter") == "bandit":
                self.bandit_error_formatter(check, json_contents)
            elif check.get("linter") == "vulture":
                self.vulture_error_formatter(check, json_contents)
            elif check.get("linter") == "XSOAR_linter":
                self.xsoar_linter_error_formatter(check, json_contents)
        with open(self.json_file_path, "w+") as f:
            json.dump(json_contents, f, indent=4)

        logger.info(f"Logs saved to {self.json_file_path}")

    def flake8_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format flake8 error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing flake8 error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get("messages", "")
        error_messages = error_messages.split("\n") if error_messages else []
        for message in error_messages:
            if message:
                file_path, line_number, column_number, _ = message.split(":", 3)
                code = message.split()[1]
                output = {
                    "linter": "flake8",
                    "severity": errors.get("type"),
                    "errorCode": code,
                    "message": message.split(code)[1].lstrip(),
                    "row": line_number,
                    "col": column_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def gather_mypy_errors(error_messages: List) -> List:
        """Gather multi-line mypy errors to a single line

        Args:
            error_messages (List): A list of mypy error outputs

        Returns:
            List. A list of strings, each element is a full mypy error message
        """
        mypy_errors: list = []
        gather_error: list = []
        for line in error_messages:
            if Path(line.split(":")[0]).is_file():
                if gather_error:
                    mypy_errors.append("\n".join(gather_error))
                    gather_error = []
            gather_error.append(line)

        # handle final error
        # last line is irrelevant
        if gather_error:
            mypy_errors.append("\n".join(gather_error[:-1]))

        return mypy_errors

    def mypy_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format mypy error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing mypy error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get("messages", "")
        error_messages = error_messages.split("\n") if error_messages else []
        mypy_errors = self.gather_mypy_errors(error_messages)

        for message in mypy_errors:
            if message:
                file_path, line_number, column_number, _ = message.split(":", 3)
                output_message = message  # default
                for prefix in ("error:", "note:"):
                    if prefix in message:
                        output_message = message.split(prefix)[1].lstrip()
                        break
                output = {
                    "linter": "mypy",
                    "severity": errors.get("type"),
                    "message": output_message,
                    "row": line_number,
                    "col": column_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    def bandit_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format bandit error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing bandit error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get("messages", "")
        error_messages = error_messages.split("\n") if error_messages else []
        for message in error_messages:
            if message:
                file_path, line_number, _ = message.split(":", 2)
                output = {
                    "linter": "bandit",
                    "severity": errors.get("type"),
                    "errorCode": message.split(" ")[1],
                    "message": message.split("[")[1].replace("]", " -"),
                    "row": line_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def get_full_file_path_for_vulture(file_name: str, content_path: str) -> str:
        """Get the full file path to a file with a given name from the content path

        Args:
            file_name (str): The file name of the file to find
            content_path (str): The content file path

        Returns:
            str. The path to the file
        """
        file_extension = Path(file_name).suffix
        if not file_extension:
            file_name = f"{file_name}.py"
        elif file_extension != ".py":
            file_name = file_name.replace(file_extension, ".py")
        return find_file(content_path, file_name)

    def vulture_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format vulture error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing vulture error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get("messages", "")
        error_messages = error_messages.split("\n") if error_messages else []
        content_path = CONTENT_PATH
        for message in error_messages:
            if message:
                file_name, line_number, error_contents = message.split(":", 2)
                file_path = self.get_full_file_path_for_vulture(file_name, content_path)  # type: ignore
                output = {
                    "linter": "vulture",
                    "severity": errors.get("type"),
                    "message": error_contents.lstrip(),
                    "row": line_number,
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    def xsoar_linter_error_formatter(self, errors: Dict, json_contents: List) -> None:
        """Format XSOAR linter error strings to JSON format and add them the json_contents

        Args:
            errors (Dict): A dictionary containing XSOAR linter error strings
            json_contents (List): The JSON file outputs
        """
        error_messages = errors.get("messages", "")
        error_messages = error_messages.split("\n") if error_messages else []
        for message in error_messages:
            if message:
                split_message = message.split(":")
                file_path = split_message[0] if len(split_message) >= 1 else ""
                code = message.split(" ")[1] if len(message.split(" ")) >= 2 else ""
                output = {
                    "linter": "xsoar_linter",
                    "severity": errors.get("type"),
                    "errorCode": code,
                    "message": message.split(code)[-1].lstrip()
                    if len(message.split(code)) >= 1
                    else "",
                    "row": split_message[1] if len(split_message) >= 2 else "",
                    "col": split_message[2] if len(split_message) >= 3 else "",
                }
                self.add_to_json_outputs(output, file_path, json_contents)

    @staticmethod
    def add_to_json_outputs(output: Dict, file_path: str, json_contents: List):
        """Adds an error entry to the JSON file contents

        Args:
            output (Dict): The information about an error entry
            file_path (str): The file path where the error occurred
            json_contents (List): The JSON file outputs
        """
        yml_file_path = file_path.replace(".py", ".yml").replace(".ps1", ".yml")
        file_type = find_type(yml_file_path)
        full_error_output = {
            "filePath": file_path,
            "fileType": os.path.splitext(file_path)[1].replace(".", ""),
            "entityType": file_type.value if file_type else "",
            "errorType": "Code",
            "name": get_file_displayed_name(yml_file_path),  # type: ignore[arg-type]
            **output,
        }
        json_contents.append(full_error_output)
