import base64
import os
import shutil
import subprocess
import tempfile
from io import open

import yaml
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (TYPE_PWSH, TYPE_PYTHON,
                                                   TYPE_TO_EXTENSION)
from demisto_sdk.commands.common.tools import (LOG_COLORS,
                                               get_all_docker_images,
                                               get_pipenv_dir,
                                               get_python_version, pascal_case,
                                               print_color, print_error)
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString


class Extractor:
    """Extractor is a class that's designed to split a yml file to it's components.

    Attributes:
        input (str): input yml file path
        dest_path (str): output path
        demisto_mock (bool): whether to add an import for demistomock
        common_server (bool): whether to add an import for common server
        file_type (str): yml file type
        configuration (Configuration): Configuration object
    """

    def __init__(self, input: str, output: str, file_type: str, no_demisto_mock: bool = False, no_common_server: bool = False,
                 no_auto_create_dir: bool = False, configuration: Configuration = None):
        self.input = input
        self.output = output
        self.demisto_mock = not no_demisto_mock
        self.common_server = not no_common_server
        self.file_type = file_type
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
        print("Starting migration of: {} to dir: {}".format(self.input, output_path))
        os.makedirs(output_path, exist_ok=True)
        base_name = os.path.basename(output_path)
        code_file = "{}/{}".format(output_path, base_name)  # extract_code will add the file extension
        self.extract_code(code_file)
        self.extract_image("{}/{}_image.png".format(output_path, base_name))
        self.extract_long_description("{}/{}_description.md".format(output_path, base_name))
        yaml_out = "{}/{}.yml".format(output_path, base_name)
        print("Creating yml file: {} ...".format(yaml_out))
        ryaml = YAML()
        ryaml.preserve_quotes = True
        with open(self.input, 'r') as yf:
            yaml_obj = ryaml.load(yf)
        script_obj = yaml_obj

        if self.file_type == 'integration':
            script_obj = yaml_obj['script']
            del yaml_obj['image']
            if 'detaileddescription' in yaml_obj:
                del yaml_obj['detaileddescription']
        script_obj['script'] = SingleQuotedScalarString('')
        code_type = script_obj['type']
        if code_type == TYPE_PWSH and not yaml_obj.get('fromversion'):
            print("Setting fromversion for PowerShell to: 5.5.0")
            yaml_obj['fromversion'] = "5.5.0"
        with open(yaml_out, 'w') as yf:
            ryaml.dump(yaml_obj, yf)
        # check if there is a README
        yml_readme = os.path.splitext(self.input)[0] + '_README.md'
        readme = output_path + '/README.md'
        if os.path.exists(yml_readme):
            shutil.copy(yml_readme, readme)
        # check if there is a changelog
        yml_changelog = os.path.splitext(self.input)[0] + '_CHANGELOG.md'
        changelog = output_path + '/CHANGELOG.md'
        if os.path.exists(yml_changelog):
            shutil.copy(yml_changelog, changelog)
        else:
            with open(changelog, 'wt', encoding='utf-8') as changelog_file:
                changelog_file.write("## [Unreleased]\n-\n")
        # Python code formatting and dev env setup
        if code_type == TYPE_PYTHON:
            code_file += '.py'
            print("Running autopep8 on file: {} ...".format(code_file))
            try:
                subprocess.call(["autopep8", "-i", "--max-line-length", "130", code_file])
            except FileNotFoundError:
                print_color("autopep8 skipped! It doesn't seem you have autopep8 installed.\n"
                            "Make sure to install it with: pip install autopep8.\n"
                            "Then run: autopep8 -i {}".format(code_file), LOG_COLORS.YELLOW)

            print("Running isort on file: {} ...".format(code_file))
            try:
                subprocess.call(["isort", code_file])
            except FileNotFoundError:
                print_color("isort skipped! It doesn't seem you have isort installed.\n"
                            "Make sure to install it with: pip install isort.\n"
                            "Then run: isort {}".format(code_file), LOG_COLORS.YELLOW)

            print("Detecting python version and setting up pipenv files ...")
            docker = get_all_docker_images(script_obj)[0]
            py_ver = get_python_version(docker, self.config.log_verbose)
            pip_env_dir = get_pipenv_dir(py_ver, self.config.envs_dirs_base)
            print("Copying pipenv files from: {}".format(pip_env_dir))
            shutil.copy("{}/Pipfile".format(pip_env_dir), output_path)
            shutil.copy("{}/Pipfile.lock".format(pip_env_dir), output_path)
            try:
                subprocess.call(["pipenv", "install", "--dev"], cwd=output_path)
                print("Installing all py requirements from docker: [{}] into pipenv".format(docker))
                requirements = subprocess.check_output(["docker", "run", "--rm", docker,
                                                        "pip", "freeze", "--disable-pip-version-check"],
                                                       universal_newlines=True, stderr=subprocess.DEVNULL).strip()
                fp = tempfile.NamedTemporaryFile(delete=False)
                fp.write(requirements.encode('utf-8'))
                fp.close()

                try:
                    subprocess.check_call(["pipenv", "install", "-r", fp.name], cwd=output_path)

                except Exception:
                    print_color("Failed installing requirements in pipenv.\n "
                                "Please try installing manually after extract ends\n", LOG_COLORS.RED)

                os.unlink(fp.name)
                print("Installing flake8 for linting")
                subprocess.call(["pipenv", "install", "--dev", "flake8"], cwd=output_path)
            except FileNotFoundError:
                print_color("pipenv install skipped! It doesn't seem you have pipenv installed.\n"
                            "Make sure to install it with: pip3 install pipenv.\n"
                            "Then run in the package dir: pipenv install --dev", LOG_COLORS.YELLOW)
        arg_path = os.path.relpath(output_path)
        print_color("\nCompleted: setting up package: {}\n".format(arg_path), LOG_COLORS.GREEN)
        print("Next steps: \n",
              "* Install additional py packages for unit testing (if needed): cd {}; pipenv install <package>\n".format(
                  arg_path) if code_type == TYPE_PYTHON else '',
              "* Create unit tests\n",
              "* Check linting and unit tests by running: demisto-sdk lint -d {}\n".format(
                  arg_path),
              "* When ready rm from git the source yml and add the new package:\n",
              "    git rm {}\n".format(self.input),
              "    git add {}\n".format(arg_path),
              sep=''
              )
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
        print("Extracting code to: {} ...".format(code_file_path))
        with open(code_file_path, 'wt') as code_file:
            if lang_type == TYPE_PYTHON and self.demisto_mock:
                code_file.write("import demistomock as demisto\n")
            if common_server:
                if lang_type == TYPE_PYTHON:
                    code_file.write("from CommonServerPython import *\n")
                if lang_type == TYPE_PWSH:
                    code_file.write(". $PSScriptRoot\\CommonServerPowerShell.ps1\n")
            code_file.write(script)
            if script[-1] != '\n':  # make sure files end with a new line (pyml seems to strip the last newline)
                code_file.write("\n")
        return 0

    def extract_image(self, output_path) -> int:
        """Extracts the image from the yml_file.

        Returns:
             int. status code for the operation.
        """
        if self.file_type == 'script':
            return 0  # no image in script type
        print("Extracting image to: {} ...".format(output_path))
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
            print("Extracting long description to: {} ...".format(output_path))
            with open(output_path, 'w', encoding='utf-8') as desc_file:
                desc_file.write(long_description)
        return 0
