import os
import threading
import concurrent.futures
from typing import Tuple, List

from demisto_sdk.commands.lint.linter import Linter
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import PACKS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, BETA_INTEGRATIONS_DIR
from demisto_sdk.commands.common.tools import get_dev_requirements, print_color, LOG_COLORS, run_command, \
    set_log_verbose, print_error, \
    get_common_server_dir, get_common_server_dir_pwsh


LOCK = threading.Lock()


class LintManager:
    """LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        project_dir_list (str): A CSV of directories to run lint on.
        no_test (bool): Whether to skip pytest.
        no_pylint (bool): Whether to skip pylint.
        no_flake8 (bool): Whether to skip flake8.
        no_mypy (bool): Whether to skip mypy.
        no_bandit (bool): Whether to skip bandit.
        no_pslint (bool): Whether to skip powershell lint.
        no_vulture (bool): Whether to skip vulture.
        verbose (bool): Whether to output a detailed response.
        root (bool): Whether to run pytest container with root user.
        keep_container (bool): Whether to keep the test container.
        cpu_num (int): Number of CPUs to run pytest on.
        parallel (bool): Whether to run command on multiple threads.
        max_workers (int): How many workers to run for multi-thread run.
        run_all_tests (bool): Whether to run all tests.
        outfile (str): file path to save failed package list.
        configuration (Configuration): The system configuration.
    """

    def __init__(self, project_dir_list: str, no_test: bool = False, no_pylint: bool = False, no_flake8: bool = False,
                 no_mypy: bool = False, verbose: bool = False, root: bool = False, keep_container: bool = False,
                 cpu_num: int = 0, parallel: bool = False, max_workers: int = 10, no_bandit: bool = False,
                 no_pslint: bool = False,
                 no_vulture: bool = False, git: bool = False, run_all_tests: bool = False, outfile: str = '',
                 configuration: Configuration = Configuration()):

        if no_test and no_pylint and no_flake8 and no_mypy and no_bandit:
            raise ValueError("Nothing to run as all --no-* options specified.")

        self.parallel = parallel
        set_log_verbose(verbose)
        self.root = root
        self.max_workers = 10 if max_workers is None else int(max_workers)
        self.keep_container = keep_container
        self.cpu_num = cpu_num
        self.common_server_created = False
        self.run_args = {
            'pylint': not no_pylint,
            'flake8': not no_flake8,
            'mypy': not no_mypy,
            'tests': not no_test,
            'bandit': not no_bandit,
            'pslint': not no_pslint,
            'vulture': not no_vulture,
        }

        if run_all_tests or (not project_dir_list and git):
            self.pkgs = self.get_all_directories()

        else:
            self.pkgs = project_dir_list.split(',')

        if git:
            self.pkgs = self._get_packages_to_run()

        self.configuration = configuration
        self.requirements_for_python3 = get_dev_requirements(3.7, self.configuration.envs_dirs_base)
        self.requirements_for_python2 = get_dev_requirements(2.7, self.configuration.envs_dirs_base)
        self.outfile = outfile

    @staticmethod
    def get_all_directories() -> List[str]:
        """Gets all integration, script and beta_integrations in packages and packs in content repo.

        Returns:
            List. A list of integration, script and beta_integration names.
        """
        print("Getting all directory names")
        all_directories = []
        # get all integrations, scripts and beta_integrations from packs
        for root, _, _ in os.walk(PACKS_DIR):
            if 'Packs/' in root:
                if ('Integrations/' in root or 'Scripts/' in root or 'Beta_Integrations/' in root) \
                        and len(root.split('/')) == 4:
                    all_directories.append(root)

        for root, _, _ in os.walk(INTEGRATIONS_DIR):
            if 'Integrations/' in root and len(root.split('/')) == 2:
                all_directories.append(root)

        for root, _, _ in os.walk(SCRIPTS_DIR):
            if 'Scripts/' in root and len(root.split('/')) == 2:
                all_directories.append(root)

        for root, _, _ in os.walk(BETA_INTEGRATIONS_DIR):
            if 'Beta_Integrations/' in root and len(root.split('/')) == 2:
                all_directories.append(root)

        return all_directories

    def run_dev_packages(self) -> int:
        """Runs the Lint command on all given packages.

        Returns:
            int. 0 on success and 1 if any package failed
        """
        good_pkgs = []
        fail_pkgs = []
        if not self.parallel:
            for project_dir in self.pkgs:

                linter = Linter(project_dir, no_test=not self.run_args['tests'],
                                no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                                no_mypy=not self.run_args['mypy'], root=self.root,
                                keep_container=self.keep_container, cpu_num=self.cpu_num,
                                configuration=self.configuration, no_bandit=not self.run_args['bandit'],
                                no_pslint=not self.run_args['pslint'],
                                no_vulture=not self.run_args['vulture'],
                                requirements_3=self.requirements_for_python3,
                                requirements_2=self.requirements_for_python2)
                run_status_code = linter.run_dev_packages()
                if run_status_code > 0:
                    fail_pkgs.append(project_dir)
                else:
                    good_pkgs.append(project_dir)

            self._print_final_results(good_pkgs=good_pkgs, fail_pkgs=fail_pkgs)

            return 1 if fail_pkgs else 0

        else:  # we run parallel processes
            return self.run_parallel_packages(self.pkgs)

    def run_parallel_packages(self, pkgs_to_run: List[str]) -> int:
        """Runs the Lint command in parallel on several threads.

        Args:
            pkgs_to_run: The packages to run in parallel

        Returns:
            int. 0 on success and 1 if any package failed
        """
        print("Starting parallel run for [{}] packages with [{}] max workers.\n".format(len(pkgs_to_run),
                                                                                        self.max_workers))
        fail_pkgs = []
        good_pkgs = []

        # run CommonServer non parallel to avoid conflicts
        # when we modify the file for mypy includes
        single_thread_script = [
            get_common_server_dir(''),
            get_common_server_dir_pwsh('')
        ]
        for script_dir in single_thread_script:
            if script_dir in pkgs_to_run:
                pkgs_to_run.remove(script_dir)
                print(f'Running single threaded dir: {script_dir}')
                res, _ = self._run_single_package_thread(package_dir=script_dir)
                if res == 0:
                    good_pkgs.append(script_dir)

                else:
                    fail_pkgs.append(script_dir)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures_submit = [executor.submit(self._run_single_package_thread, directory) for directory in pkgs_to_run]
            for future in list(concurrent.futures.as_completed(futures_submit)):
                result = future.result()
                status_code = result[0]
                package_ran = result[1]
                if status_code == 0:
                    good_pkgs.append(package_ran)

                else:
                    fail_pkgs.append(package_ran)

            return self._print_final_results(good_pkgs=good_pkgs, fail_pkgs=fail_pkgs)

    def _get_packages_to_run(self) -> List[str]:
        """Checks which packages had changes in them and should run on Lint.

        Returns:
            list[str]. A list of names of packages that should run.
        """
        print("Filtering out directories that did not change")
        pkgs_to_run = []

        current_branch = run_command(f"git rev-parse --abbrev-ref HEAD")
        print(f'current_branch = {current_branch}')

        if os.environ.get('CIRCLE_COMPARE_URL'):
            print(f"CIRCLE_COMPARE_URL = {os.environ['CIRCLE_COMPARE_URL']}")

        for directory in self.pkgs:
            if self._check_should_run_pkg(pkg_dir=directory, current_branch=current_branch):
                pkgs_to_run.append(directory)

        return pkgs_to_run

    def _check_should_run_pkg(self, pkg_dir: str, current_branch: str) -> bool:
        """Checks if there is a difference in the package before this Lint run and after it.

        Args:
            pkg_dir: The package directory to check.

        Returns:
            bool. True if there is a difference and False otherwise.
        """

        # This will check if there are any changes between current master version and the last commit in master
        if os.environ.get('CIRCLE_COMPARE_URL') and current_branch == "master":
            changes_from_last_commit_vs_master = run_command("git diff --name-only HEAD..HEAD^")
        else:
            # This will return a list of all files that changed up until the last commit (not including any changes
            # which were made but not yet committed).
            changes_from_last_commit_vs_master = run_command(f"git diff origin/master...{current_branch} --name-only")

        # This will check if any changes were made to the files in the package (pkg_dir) but are yet to be committed.
        changes_since_last_commit = run_command(f"git diff --name-only -- {pkg_dir}")

        # if the package is in the list of changed files or if any files within the package were changed
        # but not yet committed, return True
        if pkg_dir in changes_from_last_commit_vs_master or len(changes_since_last_commit) > 0:
            return True

        # if no changes were made to the package - return False.
        return False

    def _run_single_package_thread(self, package_dir: str) -> Tuple[int, str]:
        """Run a thread of lint command.

        Args:
            package_dir (str): The package directory to run the command on.

        Returns:
            Tuple[int, str]. The result code for the lint command and the package name.
        """
        try:
            linter = Linter(package_dir, no_test=not self.run_args['tests'],
                            no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                            no_mypy=not self.run_args['mypy'], root=self.root,
                            keep_container=self.keep_container, cpu_num=self.cpu_num, configuration=self.configuration,
                            lock=LOCK, no_bandit=not self.run_args['bandit'],
                            no_vulture=not self.run_args['vulture'],
                            no_pslint=not self.run_args['pslint'],
                            requirements_3=self.requirements_for_python3,
                            requirements_2=self.requirements_for_python2)
            return linter.run_dev_packages(), package_dir
        except Exception as ex:
            print_error(f'Failed running lint for: {package_dir}. Exception: {ex}')
            return 1, package_dir

    @staticmethod
    def create_failed_unittests_file(failed_unittests, outfile):
        """
        Creates a file with failed unittests.
        The file will be read in slack_notifier script - which will send the failed unittests to the content-team
        channel.
        """
        with open(outfile, "w") as failed_unittests_file:
            failed_unittests_file.write('\n'.join(failed_unittests))

    def _print_final_results(self, good_pkgs: List[str], fail_pkgs: List[str]) -> int:
        """Print the results of parallel lint command.

        Args:
            good_pkgs (list): A list of packages that passed lint.
            fail_pkgs (list): A list of packages that failed lint

        Returns:
            int. 0 on success and 1 if any package failed
        """
        if self.outfile:
            self.create_failed_unittests_file(fail_pkgs, self.outfile)

        if fail_pkgs:
            print_color("\n******* FAIL PKGS: *******", LOG_COLORS.RED)
            print_color("\n\t{}\n".format("\n\t".join(fail_pkgs)), LOG_COLORS.RED)

        if good_pkgs:
            print_color("\n******* SUCCESS PKGS: *******", LOG_COLORS.GREEN)
            print_color("\n\t{}\n".format("\n\t".join(good_pkgs)), LOG_COLORS.GREEN)

        if not good_pkgs and not fail_pkgs:
            print_color("\n******* No changed packages found *******\n", LOG_COLORS.YELLOW)

        if fail_pkgs:
            return 1

        else:
            return 0
