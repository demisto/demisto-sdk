import base64
import os
import re
import shutil
import subprocess
import tempfile
from io import open

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (TYPE_PWSH, TYPE_PYTHON,
                                                   TYPE_TO_EXTENSION)
from demisto_sdk.commands.common.tools import (LOG_COLORS,
                                               get_all_docker_images,
                                               get_pipenv_dir,
                                               get_python_version, pascal_case,
                                               print_color, print_error)

REGEX_MODULE = r"### GENERATED CODE ###((.|\s)+?)### END GENERATED CODE ###"


def get_pip_requirements(docker_image: str):
    return subprocess.check_output(["docker", "run", "--rm", docker_image,
                                    "pip", "freeze", "--disable-pip-version-check"],
                                   universal_newlines=True, stderr=subprocess.DEVNULL).strip()


class YmlSplitter:
    """YmlSplitter is a class that's designed to split a yml file to it's components.

    Attributes:
        input (str): input yml file path
        output (str): output path
        no_demisto_mock (bool): whether to add an import for demistomock
        no_common_server (bool): whether to add an import for common server
        no_auto_create_dir (bool): whether to create a dir
        base_name (str): the base name of all extracted files
        no_readme (bool): whether to extract readme
        no_pipenv (boo): whether to create pipenv
        basic_fmt (bool): whether to perform basic formatting on the code, i.e. autopep8 and isort
        file_type (str): yml file type (integration/script)
        configuration (Configuration): Configuration object
        lines_inserted_at_code_start (int): the amount of lines inserted at the beginning of the code file
    """

    def __init__(self, input: str, output: str, file_type: str, no_demisto_mock: bool = False,
                 no_common_server: bool = False, no_auto_create_dir: bool = False, configuration: Configuration = None,
                 base_name: str = '', no_readme: bool = False, no_pipenv: bool = False,
                 no_logging: bool = False, no_basic_fmt: bool = False, new_module_file: bool = False):
        self.input = input
        self.output = output
        self.demisto_mock = not no_demisto_mock
        self.common_server = not no_common_server
        self.file_type = file_type
        self.base_name = base_name
        self.readme = not no_readme
        self.pipenv = not no_pipenv
        self.logging = not no_logging
        self.basic_fmt = not no_basic_fmt
        self.lines_inserted_at_code_start = 0
        if configuration is None:
            self.config = Configuration()
        else:
            self.config = configuration
        self.autocreate_dir = not no_auto_create_dir
        with open(self.input, 'rb') as yml_file:
            self.yml_data = yaml.safe_load(yml_file)

    def get_output_path(self):
        """Get processed output path
        """
        output_path = os.path.abspath(self.output)
        if self.autocreate_dir and (output_path.endswith("Integrations") or output_path.endswith("Scripts")):
            code_name = self.yml_data.get("name")
            if not code_name:
                raise ValueError(f'Failed determining Integration/Script name when trying to auto create sub dir at: {output_path}'
                                 '\nRun with option --no-auto-create-dir to skip auto creation of target dir.')
            output_path += (os.path.sep + pascal_case(code_name))
        return output_path

    def extract_to_package_format(self) -> int:
        """Extracts the self.input yml file into several files according to the Demisto standard of the package format.

        Returns:
             int. status code for the operation.
        """
        try:
            output_path = self.get_output_path()
        except ValueError as ex:
            print_error(str(ex))
            return 1
        self.print_logs("Starting migration of: {} to dir: {}".format(self.input, output_path), log_color=LOG_COLORS.NATIVE)
        os.makedirs(output_path, exist_ok=True)
        base_name = os.path.basename(output_path) if not self.base_name else self.base_name
        code_file = "{}/{}".format(output_path, base_name)
        self.extract_code(code_file)
        script = self.yml_data['script']
        lang_type: str = script['type'] if self.file_type == 'integration' else self.yml_data['type']
        code_file = f"{code_file}{TYPE_TO_EXTENSION[lang_type]}"
        self.extract_image("{}/{}_image.png".format(output_path, base_name))
        self.extract_long_description("{}/{}_description.md".format(output_path, base_name))
        yaml_out = "{}/{}.yml".format(output_path, base_name)
        self.print_logs("Creating yml file: {} ...".format(yaml_out), log_color=LOG_COLORS.NATIVE)
        ryaml = YAML()
        ryaml.preserve_quotes = True
        with open(self.input, 'r') as yf:
            yaml_obj = ryaml.load(yf)
        script_obj = yaml_obj

        if self.file_type == 'integration':
            script_obj = yaml_obj['script']
            if 'image' in yaml_obj:
                del yaml_obj['image']
            if 'detaileddescription' in yaml_obj:
                del yaml_obj['detaileddescription']
        script_obj['script'] = SingleQuotedScalarString('')
        code_type = script_obj['type']
        if code_type == TYPE_PWSH and not yaml_obj.get('fromversion'):
            self.print_logs("Setting fromversion for PowerShell to: 5.5.0", log_color=LOG_COLORS.NATIVE)
            yaml_obj['fromversion'] = "5.5.0"
        with open(yaml_out, 'w') as yf:
            ryaml.dump(yaml_obj, yf)
        # check if there is a README and if found, set found_readme to True
        found_readme = False
        if self.readme:
            yml_readme = os.path.splitext(self.input)[0] + '_README.md'
            readme = output_path + '/README.md'
            if os.path.exists(yml_readme):
                found_readme = True
                self.print_logs(f"Copying {readme} to {readme}", log_color=LOG_COLORS.NATIVE)
                shutil.copy(yml_readme, readme)
            else:
                # open an empty file
                with open(readme, 'w'):
                    pass

        # Python code formatting and dev env setup
        if code_type == TYPE_PYTHON:
            if self.basic_fmt:
                self.print_logs("Running autopep8 on file: {} ...".format(code_file), log_color=LOG_COLORS.NATIVE)
                try:
                    subprocess.call(["autopep8", "-i", "--max-line-length", "130", code_file])
                except FileNotFoundError:
                    self.print_logs("autopep8 skipped! It doesn't seem you have autopep8 installed.\n"
                                    "Make sure to install it with: pip install autopep8.\n"
                                    "Then run: autopep8 -i {}".format(code_file), LOG_COLORS.YELLOW)
            if self.pipenv:
                try:
                    if self.basic_fmt:
                        self.print_logs("Running isort on file: {} ...".format(code_file), LOG_COLORS.NATIVE)
                        try:
                            subprocess.call(["isort", code_file])
                        except FileNotFoundError:
                            self.print_logs("isort skipped! It doesn't seem you have isort installed.\n"
                                            "Make sure to install it with: pip install isort.\n"
                                            "Then run: isort {}".format(code_file), LOG_COLORS.YELLOW)

                    self.print_logs("Detecting python version and setting up pipenv files ...", log_color=LOG_COLORS.NATIVE)
                    docker = get_all_docker_images(script_obj)[0]
                    py_ver = get_python_version(docker, self.config.log_verbose)
                    pip_env_dir = get_pipenv_dir(py_ver, self.config.envs_dirs_base)
                    self.print_logs("Copying pipenv files from: {}".format(pip_env_dir), log_color=LOG_COLORS.NATIVE)
                    shutil.copy("{}/Pipfile".format(pip_env_dir), output_path)
                    shutil.copy("{}/Pipfile.lock".format(pip_env_dir), output_path)
                    env = os.environ.copy()
                    env["PIPENV_IGNORE_VIRTUALENVS"] = "1"
                    try:
                        subprocess.call(["pipenv", "install", "--dev"], cwd=output_path, env=env)
                        self.print_logs("Installing all py requirements from docker: [{}] into pipenv".format(docker),
                                        LOG_COLORS.NATIVE)
                        requirements = get_pip_requirements(docker)
                        fp = tempfile.NamedTemporaryFile(delete=False)
                        fp.write(requirements.encode('utf-8'))
                        fp.close()

                        try:
                            subprocess.check_call(["pipenv", "install", "-r", fp.name], cwd=output_path, env=env)

                        except Exception:
                            self.print_logs("Failed installing requirements in pipenv.\n "
                                            "Please try installing manually after extract ends\n", LOG_COLORS.RED)

                        os.unlink(fp.name)
                        self.print_logs("Installing flake8 for linting", log_color=LOG_COLORS.NATIVE)
                        subprocess.call(["pipenv", "install", "--dev", "flake8"], cwd=output_path, env=env)
                    except FileNotFoundError as err:
                        self.print_logs("pipenv install skipped! It doesn't seem you have pipenv installed.\n"
                                        "Make sure to install it with: pip3 install pipenv.\n"
                                        f"Then run in the package dir: pipenv install --dev\n.Err: {err}", LOG_COLORS.YELLOW)
                    arg_path = os.path.relpath(output_path)
                    self.print_logs("\nCompleted: setting up package: {}\n".format(arg_path), LOG_COLORS.GREEN)
                    next_steps: str = "Next steps: \n" \
                                      "* Install additional py packages for unit testing (if needed): cd {};" \
                                      " pipenv install <package>\n".format(arg_path) if code_type == TYPE_PYTHON else ''
                    next_steps += "* Create unit tests\n" \
                                  "* Check linting and unit tests by running: demisto-sdk lint -i {}\n".format(arg_path)
                    next_steps += "* When ready, remove from git the old yml and/or README and add the new package:\n" \
                                  "    git rm {}\n".format(self.input)
                    if found_readme:
                        next_steps += "    git rm {}\n".format(os.path.splitext(self.input)[0] + '_README.md')
                    next_steps += "    git add {}\n".format(arg_path)
                    self.print_logs(next_steps, log_color=LOG_COLORS.NATIVE)

                except Exception:
                    self.print_logs("An unexpected error has occurred while trying to install "
                                    "the requirements in pipenv.\n"
                                    "Please try installing manually after extract ends.\n", LOG_COLORS.RED)

            else:
                self.print_logs("Skipping pipenv and requirements installation - Note: no Pipfile will be created",
                                log_color=LOG_COLORS.YELLOW)

        self.print_logs(f"Finished splitting the yml file - you can find the split results here: {output_path}",
                        log_color=LOG_COLORS.GREEN)
        return 0

    def extract_code(self, code_file_path) -> int:
        """Extracts the code from the yml_file.
        If code_file_path doesn't contain the proper extension will add it.

        Returns:
             int. status code for the operation.
        """
        common_server = self.common_server
        if common_server:
            common_server = "CommonServerPython" not in self.input and 'CommonServerPowerShell' not in self.input

        script = self.yml_data['script']
        if self.file_type == 'integration':  # in integration the script is stored at a second level
            lang_type = script['type']
            script = script['script']
        else:
            lang_type = self.yml_data['type']
        ext = TYPE_TO_EXTENSION[lang_type]
        if not code_file_path.endswith(ext):
            code_file_path += ext
        self.print_logs("Extracting code to: {} ...".format(code_file_path), log_color=LOG_COLORS.NATIVE)
        with open(code_file_path, 'wt') as code_file:
            if lang_type == TYPE_PYTHON and self.demisto_mock:
                code_file.write("import demistomock as demisto  # noqa: F401\n")
                self.lines_inserted_at_code_start += 1
            if common_server:
                if lang_type == TYPE_PYTHON:
                    code_file.write("from CommonServerPython import *  # noqa: F401\n")
                    self.lines_inserted_at_code_start += 1
                if lang_type == TYPE_PWSH:
                    code_file.write(". $PSScriptRoot\\CommonServerPowerShell.ps1\n")
                    self.lines_inserted_at_code_start += 1
            script = self.replace_imported_code(script)
            code_file.write(script)
            if script and script[-1] != '\n':
                # make sure files end with a new line (pyml seems to strip the last newline)
                code_file.write("\n")
        return 0

    def extract_image(self, output_path) -> int:
        """Extracts the image from the yml_file.

        Returns:
             int. status code for the operation.
        """
        if self.file_type == 'script':
            return 0  # no image in script type
        self.print_logs("Extracting image to: {} ...".format(output_path), log_color=LOG_COLORS.NATIVE)
        im_field = self.yml_data.get('image')
        if im_field and len(im_field.split(',')) >= 2:
            image_b64 = self.yml_data['image'].split(',')[1]
            with open(output_path, 'wb') as image_file:
                image_file.write(base64.decodebytes(image_b64.encode('utf-8')))
        return 0

    def extract_long_description(self, output_path) -> int:
        """Extracts the detailed description from the yml_file.

        Returns:
             int. status code for the operation.
        """
        if self.file_type == 'script':
            return 0  # no long description in script type
        long_description = self.yml_data.get('detaileddescription')
        if long_description:
            self.print_logs("Extracting long description to: {} ...".format(output_path), log_color=LOG_COLORS.NATIVE)
            with open(output_path, 'w', encoding='utf-8') as desc_file:
                desc_file.write(long_description)
        return 0

    def print_logs(self, log_msg: str, log_color: str) -> None:
        """
        Prints the logging message if logging is enabled
        :param log_msg: The logging message
        :param log_color: The printing color
        :return: None
        """
        if self.logging:
            print_color(log_msg, log_color)

    def replace_imported_code(self, script):
        # this is how we check that generated code exists, and the syntax of the generated code is up to date
        if '### GENERATED CODE ###:' in script and \
                '### END GENERATED CODE ###' in script:
            matches = re.finditer(REGEX_MODULE, script)
            for match in matches:
                code = match.group(1)
                lines = code.split('\n')
                imported_line = lines[0][2:]  # the first two chars are not part of the code
                self.print_logs(f'Replacing code block with `{imported_line}`', LOG_COLORS.NATIVE)
                script = script.replace(match.group(), imported_line)
        return script
