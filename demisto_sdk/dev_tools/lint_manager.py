import os
import sys
import threading
import subprocess
import concurrent.futures
from typing import Tuple, List
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.tools import print_color, LOG_COLORS

from demisto_sdk.dev_tools.linter import Linter

LOCK = threading.Lock()


class LintManager:
    """LintManager used to activate lint command using Linters in a single or multi thread.

    Attributes:
        project_dir_list (str): A CSV of directories to run lint on.
        no_test (bool): Whether to skip pytest.
        no_pylint (bool): Whether to skip pylint.
        no_flake8 (bool): Whether to skip flake8.
        no_mypy (bool): Whether to skip mypy.
        verbose (bool): Whether to output a detailed response.
        root (bool): Whether to run pytest container with root user.
        keep_container (bool): Whether to keep the test container.
        cpu_num (int): Number of CPUs to run pytest on.
        parallel (bool): Whether to run command on multiple threads.
        max_workers (int): How many workers to run for multi-thread run.
        configuration (Configuration): The system configuration.
    """

    def __init__(self, project_dir_list: str, no_test: bool = False, no_pylint: bool = False, no_flake8: bool = False,
                 no_mypy: bool = False, verbose: bool = False, root: bool = False, keep_container: bool = False,
                 cpu_num: int = 0, parallel: bool = False, max_workers: int = 10, no_bandit: bool = False,
                 configuration: Configuration = Configuration()):

        if no_test and no_pylint and no_flake8 and no_mypy:
            raise ValueError("Nothing to run as all --no-* options specified.")

        self.parallel = parallel
        self.log_verbose = verbose
        self.root = root
        self.parallel = parallel
        self.max_workers = 10 if max_workers is None else max_workers
        self.keep_container = keep_container
        self.cpu_num = cpu_num
        self.common_server_created = False
        self.run_args = {
            'pylint': not no_pylint,
            'flake8': not no_flake8,
            'mypy': not no_mypy,
            'tests': not no_test,
            'bandit': not no_bandit
        }
        self.pkgs = project_dir_list.split(',')
        self.configuration = configuration

    def run_dev_packages(self) -> int:
        """Runs the Lint command on all given packages.

        Returns:
            int. 0 on a successful run and 1 otherwise.
        """
        # if we dont run in parallel we run a single process
        if not self.parallel:
            linter = Linter(self.pkgs[0], no_test=not self.run_args['tests'],
                            no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                            no_mypy=not self.run_args['mypy'], verbose=self.log_verbose, root=self.root,
                            keep_container=self.keep_container, cpu_num=self.cpu_num, configuration=self.configuration,
                            no_bandit=not self.run_args['bandit'])

            return linter.run_dev_packages()

        # we run parallel processes
        else:
            return self.run_parallel_packages()

    def run_parallel_packages(self):
        """Runs the Lint command in parallel on several threads.

        Returns:
            int. 0 on a successful run and 1 otherwise.
        """
        max_workers = int(self.max_workers)
        pkgs_to_run = self._get_packages_to_run()

        print("Starting parallel run for [{}] packages with [{}] max workers.\n".format(len(pkgs_to_run), max_workers))
        fail_pkgs = []
        good_pkgs = []

        # run CommonServer non parallel to avoid conflicts
        # when we modify the file for mypy includes
        if 'Scripts/CommonServerPython' in pkgs_to_run:
            pkgs_to_run.remove('Scripts/CommonServerPython')
            res, _ = self._run_single_package_thread(package_dir='Scripts/CommonServerPython')
            if res == 0:
                good_pkgs.append('Scripts/CommonServerPython')

            else:
                fail_pkgs.append('Scripts/CommonServerPython')

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures_submit = [executor.submit(self._run_single_package_thread, directory) for directory in pkgs_to_run]
            for future in list(concurrent.futures.as_completed(futures_submit)):
                result = future.result()
                status_code = result[0]
                package_ran = result[1]
                if status_code == 0:
                    good_pkgs.append(package_ran)

                else:
                    fail_pkgs.append(package_ran)

            self._print_final_results(good_pkgs=good_pkgs, fail_pkgs=fail_pkgs)

    def _get_packages_to_run(self) -> List[str]:
        """Checks which packages had changes in them and should run on Lint.

        Returns:
            list[str]. A list of names of packages that should run.
        """
        pkg_dirs = self.pkgs
        pkgs_to_run = []
        for directory in pkg_dirs:
            if self._check_should_run_pkg(pkg_dir=directory):
                pkgs_to_run.append(directory)

        return pkgs_to_run

    def _check_should_run_pkg(self, pkg_dir: str) -> bool:
        """Checks if there is a difference in the package before this Lint run and after it.

        Args:
            pkg_dir: The package directory to check.

        Returns:
            bool. True if there is a difference and False otherwise.
        """
        diff_compare = os.getenv("DIFF_COMPARE")
        if not diff_compare:
            return True
        if os.getenv('CONTENT_PRECOMMIT_RUN_DEV_TASKS'):
            # if running in precommit we check against staged
            diff_compare = '--staged'
        res = subprocess.run(["git", "diff", "--name-only", diff_compare, "--", pkg_dir], text=True,
                             capture_output=True)
        if res.stdout:
            return True
        return False

    def _run_single_package_thread(self, package_dir: str) -> Tuple[int, str]:
        """Run a thread of lint command.

        Args:
            package_dir (str): The package directory to run the command on.

        Returns:
            Tuple[int, str]. The result code for the lint command and the package name.
        """
        linter = Linter(package_dir, no_test=not self.run_args['tests'],
                        no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                        no_mypy=not self.run_args['mypy'], verbose=self.log_verbose, root=self.root,
                        keep_container=self.keep_container, cpu_num=self.cpu_num, configuration=self.configuration,
                        lock=LOCK, no_bandit=not self.run_args['bandit'])

        return linter.run_dev_packages(), package_dir

    def _print_final_results(self, good_pkgs: List[str], fail_pkgs: List[str]):
        """Print the results of parallel lint command.

        Args:
            good_pkgs (list): A list of packages that passed lint.
            fail_pkgs (list): A list of packages that failed lint

        Returns:
            None.
        """
        if fail_pkgs:
            print_color("\n******* FAIL PKGS: *******", LOG_COLORS.RED)
            print_color("\n\t{}\n".format("\n\t".join(fail_pkgs)), LOG_COLORS.RED)

        if good_pkgs:
            print_color("\n******* SUCCESS PKGS: *******", LOG_COLORS.GREEN)
            print_color("\n\t{}\n".format("\n\t".join(good_pkgs)), LOG_COLORS.GREEN)

        if not good_pkgs and not fail_pkgs:
            print_color("\n******* No changed packages found *******\n", LOG_COLORS.YELLOW)

        if fail_pkgs:
            sys.exit(1)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = """Run lintings (flake8, mypy, pylint) and pytest. pylint and pytest will run within the docker
            image of an integration/script.
            Meant to be used with integrations/scripts that use the folder (package) structure.
            Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
            """
        parser = subparsers.add_parser('lint', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-d", "--dir", help="Specify directory of integration/script", required=True)
        parser.add_argument("--no-pylint", help="Do NOT run pylint linter", action='store_true')
        parser.add_argument("--no-mypy", help="Do NOT run mypy static type checking", action='store_true')
        parser.add_argument("--no-flake8", help="Do NOT run flake8 linter", action='store_true')
        parser.add_argument("--no-test", help="Do NOT test (skip pytest)", action='store_true')
        parser.add_argument("--no-bandit", help="Do NOT run bandit linter", action='store_true')
        parser.add_argument("-r", "--root", help="Run pytest container with root user", action='store_true')
        parser.add_argument("-k", "--keep-container", help="Keep the test container", action='store_true')
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
        parser.add_argument(
            "--cpu-num",
            help="Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs.)",
            default=0
        )
        parser.add_argument("-p", "--parallel", help="Run dev tasks in parallel", action='store_true')
        parser.add_argument("-m", "--max-workers", help="How many threads to run in parallel")
