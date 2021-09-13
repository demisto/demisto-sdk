import atexit
import json
import os
import re
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Callable, List, Optional

import click
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from demisto_sdk.commands.common.errors import (FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
                                                Errors)
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (
    compare_context_path_in_yml_and_readme, get_content_path, get_yaml,
    get_yml_paths_in_dir, print_warning, run_command_os)

NO_HTML = '<!-- NOT_HTML_DOC -->'
YES_HTML = '<!-- HTML_DOC -->'

SECTIONS = [
    'Troubleshooting',
    'Use Cases',
    'Known Limitations',
    'Additional Information'
]

USER_FILL_SECTIONS = [
    'FILL IN REQUIRED PERMISSIONS HERE',
    'version xx'
]

REQUIRED_MDX_PACKS = ['@mdx-js/mdx', 'fs-extra', 'commander']

PACKS_TO_IGNORE = ['HelloWorld', 'HelloWorldPremium']

DEFAULT_SENTENCES = ['getting started and learn how to build an integration']


class ReadMeValidator(BaseValidator):
    """ReadMeValidator is a validator for readme.md files
        In order to run the validator correctly please make sure:
        - Node is installed on you machine
        - make sure that the module '@mdx-js/mdx', 'fs-extra', 'commander' are installed in node-modules folder.
            If not installed, the validator will print a warning with the relevant module that is missing.
            please install it using "npm install *missing_module_name*"
        - 'DEMISTO_README_VALIDATION' environment variable should be set to True.
            To set the environment variables, run the following shell commands:
            export DEMISTO_README_VALIDATION=True
    """

    # Static var to hold the mdx server process
    _MDX_SERVER_PROCESS: Optional[subprocess.Popen] = None
    _MDX_SERVER_LOCK = Lock()
    MINIMUM_README_LENGTH = 30

    def __init__(self, file_path: str, ignored_errors=None, print_as_warnings=False, suppress_print=False,
                 json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.content_path = get_content_path()
        self.file_path = Path(file_path)
        self.pack_path = self.file_path.parent
        self.node_modules_path = self.content_path / Path('node_modules')
        with open(self.file_path) as f:
            readme_content = f.read()
        self.readme_content = readme_content

    def is_valid_file(self) -> bool:
        """Check whether the readme file is valid or not
        Returns:
            bool: True if env configured else Fale.
        """
        return all([
            self.is_image_path_valid(),
            self.verify_readme_image_paths(),
            self.is_mdx_file(),
            self.verify_no_empty_sections(),
            self.verify_no_default_sections_left(),
            self.verify_readme_is_not_too_short(),
            self.is_context_different_in_yml(),
            self.verify_demisto_in_readme_content(),
            self.verify_template_not_in_readme()
        ])

    def mdx_verify(self) -> bool:
        mdx_parse = Path(__file__).parent.parent / 'mdx-parse.js'
        readme_content = self.fix_mdx()
        with tempfile.NamedTemporaryFile('w+t') as fp:
            fp.write(readme_content)
            fp.flush()
            # run the javascript mdx parse validator
            _, stderr, is_not_valid = run_command_os(f'node {mdx_parse} -f {fp.name}', cwd=self.content_path,
                                                     env=os.environ)
        if is_not_valid:
            error_message, error_code = Errors.readme_error(stderr)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def mdx_verify_server(self) -> bool:
        if not ReadMeValidator._MDX_SERVER_PROCESS:
            server_started = ReadMeValidator.start_mdx_server(handle_error=self.handle_error,
                                                              file_path=str(self.file_path))
            if not server_started:
                return False
        readme_content = self.fix_mdx()
        retry = Retry(total=2)
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('http://', adapter)
        response = session.request(
            'POST',
            'http://localhost:6161',
            data=readme_content.encode('utf-8'),
            timeout=20
        )
        if response.status_code != 200:
            error_message, error_code = Errors.readme_error(response.text)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_mdx_file(self) -> bool:
        html = self.is_html_doc()
        valid = os.environ.get('DEMISTO_README_VALIDATION') or os.environ.get(
            'CI') or self.are_modules_installed_for_verify(self.content_path)
        if valid and not html:
            # add to env var the directory of node modules
            os.environ['NODE_PATH'] = str(self.node_modules_path) + os.pathsep + os.getenv("NODE_PATH", "")
            if os.getenv('DEMISTO_MDX_CMD_VERIFY'):
                return self.mdx_verify()
            else:
                return self.mdx_verify_server()
        return True

    def fix_mdx(self) -> str:
        txt = self.readme_content
        # copied from: https://github.com/demisto/content-docs/blob/2402bd1ab1a71f5bf1a23e1028df6ce3b2729cbb/content-repo/mdx_utils.py#L11
        # to use the same logic as we have in the content-docs build
        replace_tuples = [
            ('<br>(?!</br>)', '<br/>'),
            ('<hr>(?!</hr>)', '<hr/>'),
            ('<pre>', '<pre>{`'),
            ('</pre>', '`}</pre>'),
        ]
        for old, new in replace_tuples:
            txt = re.sub(old, new, txt, flags=re.IGNORECASE)
        # remove html comments
        txt = re.sub(r'<\!--.*?-->', '', txt, flags=re.DOTALL)
        return txt

    @staticmethod
    @lru_cache(None)
    def are_modules_installed_for_verify(content_path: str) -> bool:
        """ Check the following:
            1. npm packages installed - see packs var for specific pack details.
            2. node interperter exists.
        Returns:
            bool: True If all req ok else False
        """
        missing_module = []
        valid = True
        # Check node exist
        stdout, stderr, exit_code = run_command_os('node -v', cwd=content_path)
        if exit_code:
            print_warning(f'There is no node installed on the machine, Test Skipped, error - {stderr}, {stdout}')
            valid = False
        else:
            # Check npm modules exsits
            stdout, stderr, exit_code = run_command_os(f'npm ls --json {" ".join(REQUIRED_MDX_PACKS)}',
                                                       cwd=content_path)
            if exit_code:  # all are missinig
                missing_module.extend(REQUIRED_MDX_PACKS)
            else:
                deps = json.loads(stdout).get('dependencies', {})
                for pack in REQUIRED_MDX_PACKS:
                    if pack not in deps:
                        missing_module.append(pack)
        if missing_module:
            valid = False
            print_warning(f"The npm modules: {missing_module} are not installed, Readme mdx validation skipped. Use "
                          f"'npm install' to install all required node dependencies")
        return valid

    def is_html_doc(self) -> bool:
        if self.readme_content.startswith(NO_HTML):
            return False
        if self.readme_content.startswith(YES_HTML):
            return True
        # use some heuristics to try to figure out if this is html
        return self.readme_content.startswith('<p>') or \
            self.readme_content.startswith('<!DOCTYPE html>') or \
            ('<thead>' in self.readme_content and '<tbody>' in self.readme_content)

    def is_image_path_valid(self) -> bool:
        """ Validate images absolute paths, and prints the suggested path if its not valid.

        Returns:
            bool: True If all links are valid else False.
        """
        invalid_paths = re.findall(
            r'(\!\[.*?\]|src\=)(\(|\")(https://github.com/demisto/content/(?!raw).*?)(\)|\")', self.readme_content,
            re.IGNORECASE)
        if invalid_paths:
            for path in invalid_paths:
                path = path[2]
                alternative_path = path.replace('blob', 'raw')
                error_message, error_code = Errors.image_path_error(path, alternative_path)
                self.handle_error(error_message, error_code, file_path=self.file_path)
            return False
        return True

    def verify_readme_image_paths(self) -> bool:
        """ Validate readme (not pack readme) images relative and absolute paths.

        Returns:
            bool: True If all links both relative and absolute are valid else False.
        """
        # If there are errors in one of the following validations return False
        if any([self.check_readme_relative_image_paths(),
                self.check_readme_absolute_image_paths()]):
            return False
        return True

    def check_readme_relative_image_paths(self, is_pack_readme: bool = False) -> list:
        """ Validate readme images relative paths.
            (1) prints an error if relative paths in the pack README are found since they are not supported.
            (2) Checks if relative paths are valid (in other readme files).

        Arguments:
            is_pack_readme (bool) - True if the the README file is a pack README, default: False

        Returns:
            list: List of the errors found
        """
        error_list = []
        error_code: str = ''
        error_message: str = ''
        # If error was found, print it only if its not a pack readme. For pack readme, the PackUniqueFilesValidator
        # class handles the errors and printing.
        should_print_error = not is_pack_readme
        relative_images = re.findall(r'(\!\[.*?\])\(((?!http).*?)\)$', self.readme_content, re.IGNORECASE | re.MULTILINE)
        relative_images += re.findall(  # HTML image tag
            r'(<img.*?src\s*=\s*\"((?!http).*?)\")', self.readme_content,
            re.IGNORECASE | re.MULTILINE)

        for img in relative_images:
            # striping in case there are whitespaces at the beginning/ending of url.
            prefix = '' if 'src' in img[0] else img[0].strip()
            relative_path = img[1].strip()

            if 'Insert the link to your image here' in relative_path:
                # the line is generated automatically in playbooks readme, the user should replace it with
                # an image or remove the line.
                error_message, error_code = Errors.invalid_readme_image_error(prefix + f'({relative_path})',
                                                                              error_type='insert_image_link_error')
            elif is_pack_readme:
                error_message, error_code = Errors.invalid_readme_image_error(prefix + f'({relative_path})',
                                                                              error_type='pack_readme_relative_error')
            else:
                # generates absolute path from relative and checks for the file existence.
                if not os.path.isfile(os.path.join(self.file_path.parent, relative_path)):
                    error_message, error_code = Errors.invalid_readme_image_error(prefix + f'({relative_path})',
                                                                                  error_type='general_readme_relative_error')
            if error_code and error_message:  # error was found
                formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path,
                                                    should_print=should_print_error)
                error_list.append(formatted_error)

        return error_list

    def check_readme_absolute_image_paths(self, is_pack_readme: bool = False) -> list:
        """ Validate readme images absolute paths - Check if absolute paths are not broken.

        Arguments:
            is_pack_readme (bool) - True if the the README file is a pack README, default: False

        Returns:
            list: List of the errors found
        """
        error_list = []
        should_print_error = not is_pack_readme  # pack readme errors are handled and printed during the pack unique
        # files validation.
        absolute_links = re.findall(
            r'(!\[.*\])\((https://.*)\)$', self.readme_content, re.IGNORECASE | re.MULTILINE)
        absolute_links += re.findall(  # image tag
            r'(src\s*=\s*"(https://.*?)")', self.readme_content, re.IGNORECASE | re.MULTILINE)
        for link in absolute_links:
            prefix = '' if 'src' in link[0] else link[0].strip()
            img_url = link[1].strip()  # striping in case there are whitespaces at the beginning/ending of url.
            try:
                response = requests.get(img_url, verify=False, timeout=10)
            except Exception as ex:
                click.secho(f"Could not validate the image link: {img_url}\n {ex}", fg='yellow')
                continue
            if response.status_code != 200:
                error_message, error_code = Errors.invalid_readme_image_error(prefix + f'({img_url})',
                                                                              error_type='general_readme_absolute_error')
                formatted_error = \
                    self.handle_error(error_message, error_code, file_path=self.file_path,
                                      should_print=should_print_error)
                error_list.append(formatted_error)

        return error_list

    def verify_no_empty_sections(self) -> bool:
        """ Check that if the following headlines exists, they are not empty:
            1. Troubleshooting
            2. Use Cases
            3. Known Limitations
            4. Additional Information
        Returns:
            bool: True If all req ok else False
        """
        is_valid = True
        errors = ""
        for section in SECTIONS:
            found_section = re.findall(rf'(## {section}\n*)(-*\s*\n\n?)?(\s*.*)', self.readme_content, re.IGNORECASE)
            if found_section:
                line_after_headline = str(found_section[0][2])
                # checks if the line after the section's headline is another headline or empty
                if not line_after_headline or line_after_headline.startswith("##"):
                    # assuming that a sub headline is part of the section
                    if not line_after_headline.startswith("###"):
                        errors += f'{section} is empty, please elaborate or delete the section.\n'
                        is_valid = False

        if not is_valid:
            error_message, error_code = Errors.readme_error(errors)
            self.handle_error(error_message, error_code, file_path=self.file_path)

        return is_valid

    def _find_section_in_text(self, sections_list: List[str], ignore_packs: Optional[List[str]] = None) -> str:
        """
        Find if sections from the sections list appear in the readme content and returns an error message.
        Arguments:
            sections_list (List[str]) - list of strings, each string is a section to find in the text
            ignore_packs (List[str]) - List of packs and integration names to be ignored
        Returns:
            An error message with the relevant sections.
        """
        errors = ""

        current_pack_name = self.pack_path.name
        if ignore_packs and current_pack_name in ignore_packs:
            click.secho(f"Default sentences check - Pack {current_pack_name} is ignored.", fg="yellow")
            return errors  # returns empty string

        for section in sections_list:
            required_section = re.findall(rf'{section}', self.readme_content, re.IGNORECASE)
            if required_section:
                errors += f'Replace "{section}" with a suitable info.\n'
        return errors

    def verify_no_default_sections_left(self) -> bool:
        """ Check that there are no default leftovers such as:
            1. 'FILL IN REQUIRED PERMISSIONS HERE'.
            2. unexplicit version number - such as "version xx of".
            3. Default description belonging to one of the examples integrations
        Returns:
            bool: True If all req ok else False
        """

        errors = ""
        errors += self._find_section_in_text(USER_FILL_SECTIONS)
        errors += self._find_section_in_text(DEFAULT_SENTENCES, PACKS_TO_IGNORE)
        is_valid = not bool(errors)
        if not is_valid:
            error_message, error_code = Errors.readme_error(errors)
            self.handle_error(error_message, error_code, file_path=self.file_path)

        return is_valid

    def verify_readme_is_not_too_short(self):
        is_valid = True
        readme_size = len(self.readme_content)
        if 1 <= readme_size <= self.MINIMUM_README_LENGTH:
            error = f'Your Pack README is too small ({readme_size} chars). Please move its content to the pack ' \
                    'description or add more useful information to the Pack README. ' \
                    'Pack README files are expected to include a few sentences about the pack and/or images.' \
                    f'\nFile "{self.content_path}/{self.file_path}", line 0'
            error_message, error_code = Errors.readme_error(error)
            self.handle_error(error_message, error_code, file_path=self.file_path)
            is_valid = False
        return is_valid

    def is_context_different_in_yml(self) -> bool:
        """
        Checks if there has been a corresponding change to the integration's README
        when changing the context paths of an integration.
        This validation might run together with is_context_change_in_readme in Integration's validation.
        Returns:
            True if there has been a corresponding change to README file when context is changed in integration
        """
        valid = True

        # disregards scripts as the structure of the files is different:
        dir_path = os.path.dirname(self.file_path)
        if 'Scripts' in dir_path:
            return True

        # Get YML file, assuming only one yml in integration

        yml_file_paths = get_yml_paths_in_dir(dir_path)

        # Handles case of Pack's Readme, so no YML file is found in pack.
        if not yml_file_paths[0]:
            return True

        yml_file_path = yml_file_paths[1]  # yml_file_paths[1] should contain the first yml file found in dir

        # If get_yml_paths_in_dir does not return full path, dir_path should be added to path.
        if dir_path not in yml_file_path:
            yml_file_path = os.path.join(dir_path, yml_file_path)

        # Getting the relevant error_code:
        error, missing_from_readme_error_code = Errors.readme_missing_output_context('', '')
        error, missing_from_yml_error_code = Errors.missing_output_context('', '')

        # Only run validation if the validation has not run with is_context_change_in_readme on integration
        # so no duplicates errors will be created:
        errors, ignored_errors = self._get_error_lists()
        if f'{self.file_path} - [{missing_from_readme_error_code}]' in ignored_errors \
                or f'{self.file_path} - [{missing_from_readme_error_code}]' in errors \
                or f'{yml_file_path} - [{missing_from_yml_error_code}]' in ignored_errors \
                or f'{yml_file_path} - [{missing_from_yml_error_code}]' in errors:
            return False

        # get YML file's content:
        yml_as_dict = get_yaml(yml_file_path)

        difference_context_paths = compare_context_path_in_yml_and_readme(yml_as_dict, self.readme_content)

        # Add errors to error's list
        for command_name in difference_context_paths:
            if difference_context_paths[command_name].get('only in yml'):
                error, code = Errors.readme_missing_output_context(
                    command_name,
                    ", ".join(difference_context_paths[command_name].get('only in yml')))
                if self.handle_error(error, code, file_path=self.file_path):
                    valid = False

            if difference_context_paths[command_name].get('only in readme'):
                error, code = Errors.missing_output_context(
                    command_name, ", ".join(difference_context_paths[command_name].get('only in readme')))
                if self.handle_error(error, code, file_path=yml_file_path):
                    valid = False

        return valid

    def verify_demisto_in_readme_content(self):
        """
        Checks if there are the word 'Demisto' in the README content.

        Return:
            True if 'Demisto' does not exist in the README content, and False if it does.
        """

        is_valid = True
        invalid_lines = []

        for line_num, line in enumerate(self.readme_content.split('\n')):
            if 'demisto ' in line.lower() or ' demisto' in line.lower():
                invalid_lines.append(line_num + 1)

        if invalid_lines:
            error_message, error_code = Errors.readme_contains_demisto_word(invalid_lines)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    def verify_template_not_in_readme(self):
        """
        Checks if there are the generic sentence '%%FILL HERE%%' in the README content.

        Return:
            True if '%%FILL HERE%%' does not exist in the README content, and False if it does.
        """
        is_valid = True
        invalid_lines = []

        for line_num, line in enumerate(self.readme_content.split('\n')):
            if '%%FILL HERE%%' in line:
                invalid_lines.append(line_num + 1)

        if invalid_lines:
            error_message, error_code = Errors.template_sentence_in_readme(invalid_lines)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @staticmethod
    def start_mdx_server(handle_error: Optional[Callable] = None, file_path: Optional[str] = None) -> bool:
        with ReadMeValidator._MDX_SERVER_LOCK:
            if not ReadMeValidator._MDX_SERVER_PROCESS:
                mdx_parse_server = Path(__file__).parent.parent / 'mdx-parse-server.js'
                ReadMeValidator._MDX_SERVER_PROCESS = subprocess.Popen(['node', str(mdx_parse_server)],
                                                                       stdout=subprocess.PIPE, text=True)
                line = ReadMeValidator._MDX_SERVER_PROCESS.stdout.readline()  # type: ignore
                if 'MDX server is listening on port' not in line:
                    ReadMeValidator.stop_mdx_server()
                    error_message, error_code = Errors.error_starting_mdx_server(line=line)
                    if handle_error and file_path:
                        if handle_error(error_message, error_code, file_path=file_path):
                            return False

                    else:
                        raise Exception(error_message)
        return True

    @staticmethod
    def stop_mdx_server():
        if ReadMeValidator._MDX_SERVER_PROCESS:
            ReadMeValidator._MDX_SERVER_PROCESS.terminate()
            ReadMeValidator._MDX_SERVER_PROCESS = None

    @staticmethod
    def _get_error_lists():
        return FOUND_FILES_AND_ERRORS, FOUND_FILES_AND_IGNORED_ERRORS


atexit.register(ReadMeValidator.stop_mdx_server)
