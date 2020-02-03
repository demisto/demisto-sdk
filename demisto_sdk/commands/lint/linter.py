import os
import io
import sys
import yaml
import time
import shutil
import hashlib
import threading
import subprocess
from datetime import datetime
import requests

from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.tools import print_v, get_all_docker_images, get_python_version, \
    print_error, print_color, LOG_COLORS, get_yml_paths_in_dir, run_command


class Linter:
    """Linter used to activate lint command.

        Attributes:
            project_dir (str): The directory to run lint on.
            no_test (bool): Whether to skip pytest.
            no_pylint (bool): Whether to skip pylint.
            no_flake8 (bool): Whether to skip flake8.
            no_mypy (bool): Whether to skip mypy.
            verbose (bool): Whether to output a detailed response.
            root (bool): Whether to run pytest container with root user.
            keep_container (bool): Whether to keep the test container.
            cpu_num (int): Number of CPUs to run pytest on.
            configuration (Configuration): The system configuration.
            lock (threading.Lock): A mutex lock to be used for multi-thread lint.
        """
    common_server_target_path = "CommonServerPython.py"
    common_server_remote_path = "https://raw.githubusercontent.com/demisto/content/master/Scripts/" \
                                "CommonServerPython/CommonServerPython.py"

    def __init__(self, project_dir: str, no_test: bool = False, no_pylint: bool = False, no_flake8: bool = False,
                 no_mypy: bool = False, verbose: bool = False, root: bool = False, keep_container: bool = False,
                 cpu_num: int = 0, configuration: Configuration = Configuration(),
                 lock: threading.Lock = threading.Lock(), no_bandit: bool = False, requirements_3: str = '',
                 requirements_2: str = ''):

        if no_test and no_pylint and no_flake8 and no_mypy and no_bandit:
            raise ValueError("Nothing to run as all --no-* options specified.")

        self.configuration = configuration
        dev_scripts_dir = os.path.join(self.configuration.sdk_env_dir, 'common', 'dev_sh_scripts')
        self.run_dev_tasks_script_name = 'run_dev_tasks.sh'
        self.run_mypy_script_name = 'run_mypy.sh'
        self.container_setup_script_name = 'pkg_dev_container_setup.sh'
        self.run_dev_tasks_script = os.path.join(dev_scripts_dir, self.run_dev_tasks_script_name)
        self.container_setup_script = os.path.join(dev_scripts_dir, self.container_setup_script_name)
        self.run_mypy_script = os.path.join(dev_scripts_dir, self.run_mypy_script_name)
        self.docker_login_completed = False
        self.project_dir = os.path.abspath(os.path.join(self.configuration.env_dir, project_dir))
        if self.project_dir[-1] != os.sep:
            self.project_dir = os.path.join(self.project_dir, '')

        self.log_verbose = verbose
        self.root = root
        self.keep_container = keep_container
        self.cpu_num = cpu_num
        self.common_server_created = False
        self.run_args = {
            'pylint': not no_pylint,
            'flake8': not no_flake8,
            'mypy': not no_mypy,
            'bandit': not no_bandit,
            'tests': not no_test
        }
        self.lock = lock
        self.requirements_3 = requirements_3
        self.requirements_2 = requirements_2

    def get_common_server_python(self) -> bool:
        """Getting common server python in not exists changes self.common_server_created to True if needed.

        Returns:
            bool. True if exists/created, else False
        """
        # If not CommonServerPython is dir
        if not os.path.isfile(os.path.join(self.project_dir, self.common_server_target_path)):
            # Get file from git
            try:
                res = requests.get(self.common_server_remote_path, verify=False)
                with open(os.path.join(self.project_dir, self.common_server_target_path), "w+") as f:
                    f.write(res.text)
                    self.common_server_created = True
            except requests.exceptions.RequestException:
                print_error(Errors.no_common_server_python(self.common_server_remote_path))
                return False
        return True

    def remove_common_server_python(self):
        """checking if file exists and removing it."""
        if self.common_server_created:
            os.remove(os.path.join(self.project_dir, self.common_server_target_path))

    def run_dev_packages(self) -> int:
        return_code = 0
        # load yaml
        _, yml_path = get_yml_paths_in_dir(self.project_dir, Errors.no_yml_file(self.project_dir))
        if not yml_path:
            return 1
        print_v('Using yaml file: {}'.format(yml_path))
        with open(yml_path, 'r') as yml_file:
            yml_data = yaml.safe_load(yml_file)
        script_obj = yml_data
        if isinstance(script_obj.get('script'), dict):
            script_obj = script_obj.get('script')
        script_type = script_obj.get('type')
        if script_type != 'python':
            if script_type == 'powershell':
                # TODO powershell linting
                return 0

            print('Script is not of type "python". Found type: {}. Nothing to do.'.format(script_type))
            return 0

        dockers = get_all_docker_images(script_obj)
        py_num = get_python_version(dockers[0], self.log_verbose)
        self.lock.acquire()
        print_color("============ Starting process for: {} ============\n".format(self.project_dir),
                    LOG_COLORS.YELLOW)
        if self.lock.locked():
            self.lock.release()
        self._setup_dev_files(py_num)
        if self.run_args['flake8']:
            result_val = self.run_flake8(py_num)
            if result_val:
                return_code = result_val

        if self.run_args['mypy']:
            result_val = self.run_mypy(py_num)
            if result_val:
                return_code = result_val

        if self.run_args['bandit']:
            result_val = self.run_bandit(py_num)
            if result_val:
                return_code = result_val

        for docker in dockers:
            for try_num in (1, 2):
                print_v("Using docker image: {}".format(docker))
                py_num = get_python_version(docker, self.log_verbose)
                try:
                    if self.run_args['tests'] or self.run_args['pylint']:
                        if py_num == 2.7:
                            requirements = self.requirements_2
                        else:
                            requirements = self.requirements_3

                        docker_image_created = self._docker_image_create(docker, requirements)
                        output, status_code = self._docker_run(docker_image_created)

                        self.lock.acquire()
                        print_color("\n========== Running tests/pylint for: {} =========".format(self.project_dir),
                                    LOG_COLORS.YELLOW)
                        if status_code == 1:
                            raise subprocess.CalledProcessError(*output)

                        else:
                            print(output)
                            print_color("============ Finished process for: {}  "
                                        "with docker: {} ============\n".format(self.project_dir, docker),
                                        LOG_COLORS.GREEN)

                        if self.lock.locked():
                            self.lock.release()

                    break  # all is good no need to retry
                except subprocess.CalledProcessError as ex:
                    if ex.output:
                        print_color("=========================== ERROR IN {}==========================="
                                    "\n{}\n".format(self.project_dir, ex.output), LOG_COLORS.RED)
                    else:
                        print_color("========= Test Failed on {}, Look at the error/s above ========\n".format(
                            self.project_dir), LOG_COLORS.RED)
                        return_code = 1

                    if not self.log_verbose:
                        sys.stderr.write("Need a more detailed log? try running with the -v options as so: \n{} -v\n\n"
                                         .format(" ".join(sys.argv[:])))

                    if self.lock.locked():
                        self.lock.release()

                    # circle ci docker setup sometimes fails on
                    if try_num > 1 or not ex.output or 'read: connection reset by peer' not in ex.output:
                        return 2
                    else:
                        sys.stderr.write("Retrying as failure seems to be docker communication related...\n")

                finally:
                    sys.stdout.flush()
                    sys.stderr.flush()

        return return_code

    def run_flake8(self, py_num) -> int:
        """Runs flake8

        Args:
            py_num (int): The python version in use

        Returns:
            int. 0 if flake8 is successful, 1 otherwise.
        """
        lint_files = self._get_lint_files()
        python_exe = 'python2' if py_num < 3 else 'python3'
        print_v('Using: {} to run flake8'.format(python_exe))
        output = run_command(f'{python_exe} -m flake8 {self.project_dir}', cwd=self.configuration.env_dir)
        self.lock.acquire()
        print("\n========= Running flake8 on: {}===============".format(lint_files))
        if len(output) == 0:
            print_color("flake8 completed for: {}\n".format(lint_files), LOG_COLORS.GREEN)
            if self.lock.locked():
                self.lock.release()
            return 0

        else:
            print_error(output)
            if self.lock.locked():
                self.lock.release()
            return 1

    def run_mypy(self, py_num) -> int:
        """Runs mypy

        Args:
            py_num: The python version in use

        Returns:
            int. 0 on successful mypy run, 1 otherwise.
        """
        self.get_common_server_python()
        lint_files = self._get_lint_files()
        sys.stdout.flush()
        script_path = os.path.abspath(os.path.join(self.configuration.sdk_env_dir, self.run_mypy_script))
        output = run_command(' '.join(['bash', script_path, str(py_num), lint_files]), cwd=self.project_dir)
        self.lock.acquire()
        print("========= Running mypy on: {} ===============".format(lint_files))
        if 'Success: no issues found in 1 source file' in output:
            print(output)
            print_color("mypy completed for: {}\n".format(lint_files), LOG_COLORS.GREEN)
            self.remove_common_server_python()
            if self.lock.locked():
                self.lock.release()
            return 0

        else:
            print_error(output)
            self.remove_common_server_python()
            if self.lock.locked():
                self.lock.release()
            return 1

    def run_bandit(self, py_num) -> int:
        """Run bandit

        Args:
            py_num: The python version in use

        Returns:
            int. 0 on successful bandit run, 1 otherwise.
        """
        lint_files = self._get_lint_files()
        python_exe = 'python2' if py_num < 3 else 'python3'
        output = run_command(' '.join([python_exe, '-m', 'bandit', '-lll', '-iii', '-q', lint_files]),
                             cwd=self.project_dir)
        self.lock.acquire()
        print("========= Running bandit on: {} ===============".format(lint_files))
        print_v('Using: {} to run bandit'.format(python_exe))
        if len(output) == 0:
            print_color("bandit completed for: {}\n".format(lint_files), LOG_COLORS.GREEN)
            if self.lock.locked():
                self.lock.release()
            return 0

        else:
            print_error(output)
            if self.lock.locked():
                self.lock.release()
            return 1

    def _docker_login(self):
        if self.docker_login_completed:
            return True
        docker_user = os.getenv('DOCKERHUB_USER', None)
        if not docker_user:
            print_v('DOCKERHUB_USER not set. Not trying to login to dockerhub')
            return False
        docker_pass = os.getenv('DOCKERHUB_PASSWORD', None)
        # pass is optional for local testing scenario. allowing password to be passed via stdin
        cmd = ['docker', 'login', '-u', docker_user]
        if docker_pass:
            cmd.append('--password-stdin')
        res = subprocess.run(cmd, input=docker_pass, capture_output=True, text=True)
        if res.returncode != 0:
            print("Failed docker login: {}".format(res.stderr))
            return False
        print_v("Completed docker login")
        self.docker_login_completed = True
        return True

    def _docker_image_create(self, docker_base_image, requirements):
        """Create the docker image with dev dependencies. Will check if already existing.
        Uses a hash of the requirements to determine the image tag

        Arguments:
            docker_base_image (string): docker image to use as base for installing dev deps
            requirements (string): requirements doc

        Returns:
            string. image name to use
        """
        if ':' not in docker_base_image:
            docker_base_image += ':latest'
        with open(self.container_setup_script, "rb") as f:
            setup_script_data = f.read()
        md5 = hashlib.md5(requirements.encode('utf-8') + setup_script_data).hexdigest()
        target_image = 'devtest' + docker_base_image + '-' + md5
        lock_file = ".lock-" + target_image.replace("/", "-")
        try:
            if (time.time() - os.path.getctime(lock_file)) > (60 * 5):
                print("{}: Deleting old lock file: {}".format(datetime.now(), lock_file))
                os.remove(lock_file)
        except Exception as ex:
            print_v("Failed check and delete for lock file: {}. Error: {}".format(lock_file, ex))
        wait_print = True
        for x in range(60):
            images_ls = run_command(' '.join(['docker', 'image', 'ls', '--format', '{{.Repository}}:{{.Tag}}',
                                              target_image])).strip()
            if images_ls == target_image:
                print('{}: Using already existing docker image: {}'.format(datetime.now(), target_image))
                return target_image
            if wait_print:
                print("{}: Existing image: {} not found will obtain lock file or wait for image".format(datetime.now(),
                                                                                                        target_image))
                wait_print = False
            print_v("Trying to obtain lock file: " + lock_file)
            try:
                f = open(lock_file, "x")
                f.close()
                print("{}: Obtained lock file: {}".format(datetime.now(), lock_file))
                break
            except Exception as ex:
                print_v("Failed getting lock. Will wait {}".format(str(ex)))
                time.sleep(5)
        try:
            # try doing a pull
            try:
                print("{}: Trying to pull image: {}".format(datetime.now(), target_image))
                pull_res = subprocess.check_output(['docker', 'pull', target_image],
                                                   stderr=subprocess.STDOUT, universal_newlines=True)
                print("Pull succeeded with output: {}".format(pull_res))
                return target_image
            except subprocess.CalledProcessError as cpe:
                print_v("Failed docker pull (will create image) with status: {}. Output: {}".format(cpe.returncode,
                                                                                                    cpe.output))
            print("{}: Creating docker image: {} (this may take a minute or two...)".format(datetime.now(),
                                                                                            target_image))
            container_id = run_command(' '.join(['docker', 'create', '-i', docker_base_image, 'sh',
                                                 '/' + self.container_setup_script_name])).strip()
            subprocess.check_call(['docker', 'cp', self.container_setup_script,
                                   container_id + ':/' + self.container_setup_script_name])
            print_v(subprocess.check_output(['docker', 'start', '-a', '-i', container_id],
                                            input=requirements, stderr=subprocess.STDOUT,
                                            universal_newlines=True))
            print_v(subprocess.check_output(['docker', 'commit', container_id, target_image], stderr=subprocess.STDOUT,
                                            universal_newlines=True))
            print_v(subprocess.check_output(['docker', 'rm', container_id], stderr=subprocess.STDOUT,
                                            universal_newlines=True))
            if self._docker_login():
                print("{}: Pushing image: {} to docker hub".format(datetime.now(), target_image))
                print_v(subprocess.check_output(['docker', 'push', target_image], stderr=subprocess.STDOUT,
                                                universal_newlines=True))
        except subprocess.CalledProcessError as err:
            print("Failed executing command with  error: {} Output: \n{}".format(err, err.output))
            raise err
        finally:
            try:
                os.remove(lock_file)
            except Exception as ex:
                print("{}: Error removing file: {}".format(datetime.now(), ex))
        print('{}: Done creating docker image: {}'.format(datetime.now(), target_image))
        return target_image

    def _docker_run(self, docker_image):
        workdir = '/devwork'  # this is setup in CONTAINER_SETUP_SCRIPT
        pylint_files = os.path.basename(self._get_lint_files())

        run_params = ['docker', 'create', '-w', workdir,
                      '-e', 'PYLINT_FILES={}'.format(pylint_files)]
        if not self.root:
            run_params.extend(['-u', '{}:4000'.format(os.getuid())])
        if not self.run_args['tests']:
            run_params.extend(['-e', 'PYTEST_SKIP=1'])
        if not self.run_args['pylint']:
            run_params.extend(['-e', 'PYLINT_SKIP=1'])
        run_params.extend(['-e', 'CPU_NUM={}'.format(self.cpu_num)])
        run_params.extend(['-e', 'CI={}'.format(os.getenv("CI", "false"))])
        run_params.extend([docker_image, 'sh', './{}'.format(self.run_dev_tasks_script_name)])
        output = run_command(' '.join(run_params))
        container_id = output.strip()
        try:
            output = output + '\n' + run_command(' '.join(['docker', 'cp', self.project_dir + '/.', container_id +
                                                           ':' + workdir]), exit_on_error=False)
            output = output + '\n' + run_command(' '.join(['docker', 'cp', self.run_dev_tasks_script, container_id +
                                                           ':' + workdir]), exit_on_error=False)
            output = output + '\n' + subprocess.check_output(['docker', 'start', '-a', container_id],
                                                             stderr=subprocess.STDOUT,
                                                             universal_newlines=True)
            return output, 0
        finally:
            if not self.keep_container:
                run_command(f'docker rm {container_id}')
            else:
                print("Test container [{}] was left available".format(container_id))

    def _setup_dev_files(self, py_num):
        # copy demistomock and common server
        try:
            shutil.copy(self.configuration.env_dir + '/Tests/demistomock/demistomock.py', self.project_dir)
            open(self.project_dir + '/CommonServerUserPython.py', 'a').close()  # create empty file
            shutil.rmtree(self.project_dir + '/__pycache__', ignore_errors=True)
            shutil.copy(self.configuration.env_dir + '/Tests/scripts/dev_envs/pytest/conftest.py', self.project_dir)
            self.check_api_module_imports(py_num)
            if "/Scripts/CommonServerPython" not in self.project_dir:
                # Otherwise we already have the CommonServerPython.py file
                shutil.copy(self.configuration.env_dir + '/Scripts/CommonServerPython/CommonServerPython.py',
                            self.project_dir)
        except Exception as e:
            print_v('Could not copy demistomock and CommonServer files: {}'.format(str(e)), self.log_verbose)

    def check_api_module_imports(self, py_num):
        """
        Checks if the integration imports an API module and if so pastes the module in the package.
        :param py_num: The python version - api modules are in python 3
        """
        if py_num > 3:
            unifier = Unifier(self.project_dir)
            code_file_path = unifier.get_code_file('.py')

            try:
                # Look for an import to an API module in the code. If there is such import, we need to copy the correct
                # module file to the package directory.
                with io.open(code_file_path, mode='r', encoding='utf-8') as script_file:
                    _, module_name = unifier.check_api_module_imports(script_file.read())
                if module_name:
                    module_path = os.path.join(self.configuration.env_dir, 'Packs', 'ApiModules', 'Scripts',
                                               module_name, module_name + '.py')
                    print_v('Copying ' + os.path.join(self.configuration.env_dir, 'Scripts', module_path))
                    if not os.path.exists(module_path):
                        raise ValueError('API Module {} not found, you might be outside of the content repository'
                                         ' or this API module does not exist'.format(module_name))
                    shutil.copy(os.path.join(module_path), self.project_dir)
            except Exception as e:
                print_v('Unable to retrieve the module file {}: {}'.format(module_name, str(e)))

    def _get_lint_files(self):
        unifier = Unifier(self.project_dir)
        code_file = unifier.get_code_file('.py')
        return os.path.abspath(code_file)
