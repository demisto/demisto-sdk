import os
import yaml
import threading
import concurrent.futures
from typing import Tuple, List

from demisto_sdk.dev_tools.linter import Linter
from demisto_sdk.common.constants import Errors
from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.constants import PACKS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, BETA_INTEGRATIONS_DIR
from demisto_sdk.common.tools import print_v, get_docker_images, get_python_version, get_dev_requirements,\
    print_color, LOG_COLORS, get_yml_paths_in_dir, run_command


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
        no_bc_check (bool): Whether to skip backwards compatibility checks.
        verbose (bool): Whether to output a detailed response.
        root (bool): Whether to run pytest container with root user.
        keep_container (bool): Whether to keep the test container.
        cpu_num (int): Number of CPUs to run pytest on.
        parallel (bool): Whether to run command on multiple threads.
        max_workers (int): How many workers to run for multi-thread run.
        run_all_tests (bool): Whether to run all tests.
        configuration (Configuration): The system configuration.
    """

    def __init__(self, project_dir_list: str, no_test: bool = False, no_pylint: bool = False, no_flake8: bool = False,
                 no_mypy: bool = False, verbose: bool = False, root: bool = False, keep_container: bool = False,
                 cpu_num: int = 0, parallel: bool = False, max_workers: int = 10, no_bandit: bool = False,
                 no_bc_check: bool = False, run_all_tests: bool = False,
                 configuration: Configuration = Configuration()):

        if no_test and no_pylint and no_flake8 and no_mypy and no_bandit:
            raise ValueError("Nothing to run as all --no-* options specified.")

        self.parallel = parallel
        self.log_verbose = verbose
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
            'bandit': not no_bandit
        }
        self.no_bc_check = no_bc_check

        if run_all_tests:
            self.pkgs = self.get_all_directories()
            self.no_bc_check = True

        else:
            self.pkgs = project_dir_list.split(',')
            if not self.no_bc_check:
                self.pkgs = self._get_packages_to_run()

        self.configuration = configuration
        self.requirements_for_python3 = get_dev_requirements(3.7, self.configuration.envs_dirs_base, self.log_verbose)
        self.requirements_for_python2 = get_dev_requirements(2.7, self.configuration.envs_dirs_base, self.log_verbose)

    @staticmethod
    def get_all_directories() -> List[str]:
        """Gets all integration, script and beta_integrations in packages and packs in content repo.

        Returns:
            List. A list of integration, script and beta_integration names.
        """
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
                py_num = self._get_package_python_number(project_dir)
                if py_num == 2.7:
                    requirements = self.requirements_for_python2
                else:
                    requirements = self.requirements_for_python3

                linter = Linter(project_dir, no_test=not self.run_args['tests'],
                                no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                                no_mypy=not self.run_args['mypy'], verbose=self.log_verbose, root=self.root,
                                keep_container=self.keep_container, cpu_num=self.cpu_num,
                                configuration=self.configuration, no_bandit=not self.run_args['bandit'],
                                requirements=requirements)

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
        if 'Scripts/CommonServerPython' in pkgs_to_run:
            pkgs_to_run.remove('Scripts/CommonServerPython')
            res, _ = self._run_single_package_thread(package_dir='Scripts/CommonServerPython')
            if res == 0:
                good_pkgs.append('Scripts/CommonServerPython')

            else:
                fail_pkgs.append('Scripts/CommonServerPython')

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

    def _get_package_python_number(self, package: str) -> float:
        """Gets the python version number of the package.

        Args:
            package: the package to check its python version number.

        Returns:
            float. The python version used by the package.
        """
        _, yml_path = get_yml_paths_in_dir(package, Errors.no_yml_file(package))
        if not yml_path:
            return 1
        print_v('Using yaml file: {}'.format(yml_path))
        with open(yml_path, 'r') as yml_file:
            yml_data = yaml.safe_load(yml_file)
        script_obj = yml_data
        if isinstance(script_obj.get('script'), dict):
            script_obj = script_obj.get('script')

        dockers = get_docker_images(script_obj)
        py_num = get_python_version(dockers[0], self.log_verbose, no_prints=True)
        return py_num

    def _get_packages_to_run(self) -> List[str]:
        """Checks which packages had changes in them and should run on Lint.

        Returns:
            list[str]. A list of names of packages that should run.
        """
        pkgs_to_run = []
        for directory in self.pkgs:
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

        res = run_command(f"git diff --name-only {diff_compare} -- {pkg_dir}")
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
        py_num = self._get_package_python_number(package_dir)
        if py_num == 2.7:
            requirements = self.requirements_for_python2
        else:
            requirements = self.requirements_for_python3

        linter = Linter(package_dir, no_test=not self.run_args['tests'],
                        no_pylint=not self.run_args['pylint'], no_flake8=not self.run_args['flake8'],
                        no_mypy=not self.run_args['mypy'], verbose=self.log_verbose, root=self.root,
                        keep_container=self.keep_container, cpu_num=self.cpu_num, configuration=self.configuration,
                        lock=LOCK, no_bandit=not self.run_args['bandit'], requirements=requirements)

        return linter.run_dev_packages(), package_dir

    def _print_final_results(self, good_pkgs: List[str], fail_pkgs: List[str]) -> int:
        """Print the results of parallel lint command.

        Args:
            good_pkgs (list): A list of packages that passed lint.
            fail_pkgs (list): A list of packages that failed lint

        Returns:
            int. 0 on success and 1 if any package failed
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
            return 1

        else:
            return 0

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = """Run lintings (flake8, mypy, pylint) and pytest. pylint and pytest will run within the docker
            image of an integration/script.
            Meant to be used with integrations/scripts that use the folder (package) structure.
            Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
            """
        parser = subparsers.add_parser('lint', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-d", "--dir", help="Specify directory of integration/script")
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
        parser.add_argument("-p", "--parallel", help="Run tests in parallel", action='store_true')
        parser.add_argument("-m", "--max-workers", help="How many threads to run in parallel")
        parser.add_argument("--no-bc", help="Check diff with $DIFF_COMPARE env variable", action='store_true')
        parser.add_argument("-a", "--run-all-tests", help="Run lint on all directories in content repo",
                            action='store_true')
