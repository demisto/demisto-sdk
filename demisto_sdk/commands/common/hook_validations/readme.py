import os
import re
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Callable, List, Optional, Set

import docker
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from demisto_sdk.commands.common.constants import (
    PACKS_DIR,
    RELATIVE_HREF_URL_REGEX,
    RELATIVE_MARKDOWN_URL_REGEX,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.docker_helper import init_global_docker_client
from demisto_sdk.commands.common.errors import (
    FOUND_FILES_AND_ERRORS,
    FOUND_FILES_AND_IGNORED_ERRORS,
    Errors,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.common.MDXServer import (
    start_docker_MDX_server,
    start_local_MDX_server,
)
from demisto_sdk.commands.common.tools import (
    compare_context_path_in_yml_and_readme,
    get_pack_name,
    get_yaml,
    get_yml_paths_in_dir,
    run_command_os,
)

NO_HTML = "<!-- NOT_HTML_DOC -->"
YES_HTML = "<!-- HTML_DOC -->"

SECTIONS = [
    "Troubleshooting",
    "Use Cases",
    "Known Limitations",
    "Additional Information",
]

USER_FILL_SECTIONS = [
    "FILL IN REQUIRED PERMISSIONS HERE",
    "version xx",
    "%%UPDATE%%",
]

REQUIRED_MDX_PACKS = [
    "@mdx-js/mdx",
    "fs-extra",
    "commander",
    "markdownlint",
    "markdownlint-rule-helpers",
]

PACKS_TO_IGNORE = ["HelloWorld", "HelloWorldPremium"]

DEFAULT_SENTENCES = ["getting started and learn how to build an integration"]

RETRIES_VERIFY_MDX = 2


@dataclass(frozen=True)
class ReadmeUrl:
    """Url links found in README files.
    can be of type markdown form - [this is a link](https://link.com)
    or be of html form - <a href="https://link.com">this is a link</a>

    link_prefix : The start of the link, for markdown will contain the description,
     for href will contain the link until the url, including the url itself.

    url : the url from our link

    is_markdown: if our link is markdown or html
    """

    link_prefix: str
    url: str
    is_markdown: bool

    def get_full_link(self) -> str:
        if self.is_markdown:
            return f"{self.link_prefix}({self.url})"
        else:
            return self.link_prefix

    def get_new_link(self, new_url: str) -> str:
        """Get a new link string where url is replaced with new_url"""
        if self.is_markdown:
            return f"{self.link_prefix}({new_url})"
        else:
            return str.replace(self.link_prefix, self.url, new_url)

    def get_url(self):
        return self.url


def get_relative_urls(content: str) -> Set[ReadmeUrl]:
    """
    Find all relative urls (md link and href links_ in README.
    Returns: a set of ReadmeUrls objects.
    """
    relative_urls = re.findall(
        RELATIVE_MARKDOWN_URL_REGEX, content, re.IGNORECASE | re.MULTILINE
    )
    relative_html_urls = re.findall(
        RELATIVE_HREF_URL_REGEX, content, re.IGNORECASE | re.MULTILINE
    )

    def get_not_empty_urls(urls, is_markdown):
        return {ReadmeUrl(url[0], url[1], is_markdown) for url in urls if url[1]}

    return get_not_empty_urls(relative_urls, True) | get_not_empty_urls(
        relative_html_urls, False
    )


def mdx_server_is_up() -> bool:
    """
    Will ping the node server to check if it is already up

    Returns: a boolean value indicating if the server is up

    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        return sock.connect_ex(("localhost", 6161)) == 0
    except Exception:
        return False


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
    _MDX_SERVER_LOCK = Lock()
    MINIMUM_README_LENGTH = 30

    def __init__(
        self,
        file_path: str,
        ignored_errors=None,
        json_file_path=None,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self.content_path = CONTENT_PATH
        self.file_path_str = file_path
        self.file_path = Path(file_path)
        self.pack_path = self.file_path.parent
        self.node_modules_path = self.content_path / Path("node_modules")  # type: ignore
        with open(self.file_path) as f:
            readme_content = f.read()
        self.readme_content = readme_content

    def is_valid_file(self) -> bool:
        """Check whether the readme file is valid or not
        Returns:
            bool: True if env configured else False.
        """
        return all(
            [
                self.is_image_path_valid(),
                self.verify_image_exist(),
                self.is_mdx_file(),
                self.verify_no_empty_sections(),
                self.verify_no_default_sections_left(),
                self.verify_readme_is_not_too_short(),
                self.is_context_different_in_yml(),
                self.verify_template_not_in_readme(),
                self.verify_copyright_section_in_readme_content(),
                # self.has_no_markdown_lint_errors(),
                self.validate_no_disallowed_terms_in_customer_facing_docs(
                    file_content=self.readme_content, file_path=self.file_path_str
                ),
            ]
        )

    def mdx_verify_server(self) -> bool:
        server_started = mdx_server_is_up()
        if not server_started:
            if self.handle_error(
                "Validation of MDX file failed due to unable to start the mdx server. You can skip this by adding RM103"
                " to the list of skipped validations under '.pack-ignore'.",
                error_code="RM103",
                file_path=self.file_path,
            ):
                return False
            logger.info(
                "<yellow>Validation of MDX file failed due to unable to start the mdx server, skipping.</yellow>"
            )
            return True
        for _ in range(RETRIES_VERIFY_MDX):
            try:
                readme_content = self.fix_mdx()
                retry = Retry(total=2)
                adapter = HTTPAdapter(max_retries=retry)
                session = requests.Session()
                session.mount("http://", adapter)
                response = session.request(
                    "POST",
                    "http://localhost:6161",
                    data=readme_content.encode("utf-8"),
                    timeout=20,
                )
                if response.status_code != 200:
                    error_message, error_code = Errors.readme_error(response.text)
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        return False
                return True
            except Exception as e:
                logger.info(f"Starting MDX local server due to exception. Error: {e}")
                start_local_MDX_server()
        return True

    @error_codes("RM103")
    def is_mdx_file(self) -> bool:
        html = self.is_html_doc()
        valid = self.should_run_mdx_validation()

        if valid and not html:
            # add to env var the directory of node modules

            os.environ["NODE_PATH"] = (
                str(self.node_modules_path) + os.pathsep + os.getenv("NODE_PATH", "")
            )
            return self.mdx_verify_server()
        return True

    def should_run_mdx_validation(self):
        return (
            os.environ.get("DEMISTO_README_VALIDATION")
            or os.environ.get("CI")
            or ReadMeValidator.are_modules_installed_for_verify(
                self.content_path  # type: ignore
            )
            or ReadMeValidator.is_docker_available()
        )

    def fix_mdx(self) -> str:
        txt = self.readme_content
        # copied from: https://github.com/demisto/content-docs/blob/2402bd1ab1a71f5bf1a23e1028df6ce3b2729cbb/content-repo/mdx_utils.py#L11
        # to use the same logic as we have in the content-docs build
        replace_tuples = [
            ("<br>(?!</br>)", "<br/>"),
            ("<hr>(?!</hr>)", "<hr/>"),
            ("<pre>", "<pre>{`"),
            ("</pre>", "`}</pre>"),
        ]
        for old, new in replace_tuples:
            txt = re.sub(old, new, txt, flags=re.IGNORECASE)
        # remove html comments
        txt = re.sub(r"<\!--.*?-->", "", txt, flags=re.DOTALL)
        return txt

    def is_html_doc(self) -> bool:
        if self.readme_content.startswith(NO_HTML):
            return False
        if self.readme_content.startswith(YES_HTML):
            return True
        # use some heuristics to try to figure out if this is html
        return (
            self.readme_content.startswith("<p>")
            or self.readme_content.startswith("<!DOCTYPE html>")
            or ("<thead>" in self.readme_content and "<tbody>" in self.readme_content)
        )

    @error_codes("RM101")
    def is_image_path_valid(self) -> bool:
        """Validate images absolute paths, and prints the suggested path if its not valid.

        Returns:
            bool: True If all links are valid else False.
        """
        invalid_paths = re.findall(
            r"(\!\[.*?\]|src\=)(\(|\")(https://github.com/demisto/content/blob/.*?)(\)|\")",
            self.readme_content,
            re.IGNORECASE,
        )
        if invalid_paths:
            handled_errors = []
            for path in invalid_paths:
                path = path[2]
                alternative_path = path.replace("blob", "raw")
                error_message, error_code = Errors.image_path_error(
                    path, alternative_path
                )
                handled_errors.append(
                    self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    )
                )
            if any(handled_errors):
                return False
        return True

    def check_readme_relative_url_paths(self, is_pack_readme: bool = False) -> list:
        """Validate readme url relative paths.
            prints an error if relative paths in README are found since they are not supported.

        Arguments:
            is_pack_readme (bool) - True if the the README file is a pack README, default: False

        Returns:
            list: List of the errors found
        """
        error_list = []
        relative_urls = get_relative_urls(self.readme_content)
        for url_link in relative_urls:
            # striping in case there are whitespaces at the beginning/ending of url.
            error_message, error_code = Errors.invalid_readme_relative_url_error(
                url_link.get_url()
            )
            if error_code and error_message:  # error was found
                formatted_error = self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                )
                # if error is None it should be ignored
                if formatted_error:
                    error_list.append(formatted_error)

        return error_list

    @error_codes("RM114")
    def verify_image_exist(self) -> bool:
        """Validate README images are actually exits.

        Returns:
            bool: True If all image path's actually exist else False.

        """
        images_path = re.findall(
            r"\.\./doc_files/[a-zA-Z0-9_-]+\.png",
            self.readme_content,
        )

        for image_path in images_path:
            image_file_path = Path(
                PACKS_DIR, get_pack_name(self.file_path), image_path.replace("../", "")
            )
            if not image_file_path.is_file():
                error_message, error_code = Errors.image_does_not_exist(image_path)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    @staticmethod
    @lru_cache(None)
    def is_docker_available():
        """Pings the docker daemon to check if it is available

        Returns:
            bool: True if the daemon is accessible
        """
        try:
            docker_client: docker.DockerClient = init_global_docker_client(
                log_prompt="DockerPing"
            )  # type: ignore
            docker_client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    @lru_cache(None)
    def are_modules_installed_for_verify(content_path: str) -> bool:
        """Check the following:
            1. npm packages installed - see packs var for specific pack details.
            2. node interperter exists.
        Returns:
            bool: True If all req ok else False
        """
        missing_module = []
        valid = True
        # Check node exist
        stdout, stderr, exit_code = run_command_os("node -v", cwd=content_path)
        if exit_code:
            logger.error(
                f"There is no node installed on the machine, error - {stderr}, {stdout}"
            )
            valid = False
        else:
            # Check npm modules exsits
            stdout, stderr, exit_code = run_command_os(
                f'npm ls --json {" ".join(REQUIRED_MDX_PACKS)}', cwd=content_path
            )
            if exit_code:  # all are missinig
                missing_module.extend(REQUIRED_MDX_PACKS)
            else:
                deps = json.loads(stdout).get("dependencies", {})
                for pack in REQUIRED_MDX_PACKS:
                    if pack not in deps:
                        missing_module.append(pack)
        if missing_module:
            valid = False
            logger.debug(
                f"The npm modules: {missing_module} are not installed. To run the mdx server locally, use "
                f"'npm install' to install all required node dependencies. Otherwise, if docker is installed, the server"
                f"will run in a docker container"
            )
        return valid

    @error_codes("RM100")
    def verify_no_empty_sections(self) -> bool:
        """Check that if the following headlines exists, they are not empty:
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
            found_section = re.findall(
                rf"(## {section}\n*)(-*\s*\n\n?)?(\s*.*)",
                self.readme_content,
                re.IGNORECASE,
            )
            if found_section:
                line_after_headline = str(found_section[0][2])
                # checks if the line after the section's headline is another headline or empty
                if not line_after_headline or line_after_headline.startswith("##"):
                    # assuming that a sub headline is part of the section
                    if not line_after_headline.startswith("###"):
                        errors += f"{section} is empty, please elaborate or delete the section.\n"
                        is_valid = False

        if not is_valid:
            error_message, error_code = Errors.readme_error(errors)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def _find_section_in_text(
        self, sections_list: List[str], ignore_packs: Optional[List[str]] = None
    ) -> str:
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
            logger.info(
                f"<yellow>Default sentences check - Pack {current_pack_name} is ignored.</yellow>"
            )
            return errors  # returns empty string

        for section in sections_list:
            required_section = re.findall(
                rf"{section}", self.readme_content, re.IGNORECASE
            )
            if required_section:
                errors += f'Replace "{section}" with a suitable info.\n'
        return errors

    @error_codes("RM100")
    def verify_no_default_sections_left(self) -> bool:
        """Check that there are no default leftovers such as:
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
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("RM100")
    def verify_readme_is_not_too_short(self):
        is_valid = True
        readme_size = len(self.readme_content)
        if 1 <= readme_size <= self.MINIMUM_README_LENGTH:
            error = (
                f"Your Pack README is too small ({readme_size} chars). Please move its content to the pack "
                "description or add more useful information to the Pack README. "
                "Pack README files are expected to include a few sentences about the pack and/or images."
                f'\nFile "{self.content_path}/{self.file_path}", line 0'
            )
            error_message, error_code = Errors.readme_error(error)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False
        return is_valid

    @error_codes("RM102,IN136")
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
        if "Scripts" in dir_path:
            return True

        # Get YML file, assuming only one yml in integration

        yml_file_paths = get_yml_paths_in_dir(dir_path)

        # Handles case of Pack's Readme, so no YML file is found in pack.
        if not yml_file_paths[0]:
            return True

        yml_file_path = yml_file_paths[
            1
        ]  # yml_file_paths[1] should contain the first yml file found in dir

        # If get_yml_paths_in_dir does not return full path, dir_path should be added to path.
        if dir_path not in yml_file_path:
            yml_file_path = os.path.join(dir_path, yml_file_path)

        # Getting the relevant error_code:
        error, missing_from_readme_error_code = Errors.readme_missing_output_context(
            "", ""
        )
        error, missing_from_yml_error_code = Errors.missing_output_context("", "")

        # Only run validation if the validation has not run with is_context_change_in_readme on integration
        # so no duplicates errors will be created:
        errors, ignored_errors = self._get_error_lists()
        if (
            f"{self.file_path} - [{missing_from_readme_error_code}]" in ignored_errors
            or f"{self.file_path} - [{missing_from_readme_error_code}]" in errors
            or f"{yml_file_path} - [{missing_from_yml_error_code}]" in ignored_errors
            or f"{yml_file_path} - [{missing_from_yml_error_code}]" in errors
        ):
            return False

        # get YML file's content:
        yml_as_dict = get_yaml(yml_file_path)

        difference_context_paths = compare_context_path_in_yml_and_readme(
            yml_as_dict, self.readme_content
        )

        # Add errors to error's list
        for command_name in difference_context_paths:
            if difference_context_paths[command_name].get("only in yml"):
                error, code = Errors.readme_missing_output_context(
                    command_name,
                    ", ".join(
                        difference_context_paths[command_name].get("only in yml")
                    ),
                )
                if self.handle_error(error, code, file_path=self.file_path):
                    valid = False

            if difference_context_paths[command_name].get("only in readme"):
                error, code = Errors.missing_output_context(
                    command_name,
                    ", ".join(
                        difference_context_paths[command_name].get("only in readme")
                    ),
                )
                if self.handle_error(error, code, file_path=yml_file_path):
                    valid = False

        return valid

    def check_readme_content_contain_text(
        self, text_list: list, is_lower: bool = False, to_split: bool = False
    ):
        """
        Args:
            text_list: list of words/sentences to search in line content.
            is_lower: True to check when line is lower cased.
            to_split: True to split the line in order to search specific word

        Returns:
            list of lines which contains the given text.

        """
        invalid_lines = []

        for line_num, line in enumerate(self.readme_content.split("\n")):
            if is_lower:
                line = line.lower()
            if to_split:
                line = line.split()  # type: ignore
            for text in text_list:
                if text in line:
                    invalid_lines.append(line_num + 1)

        return invalid_lines

    @error_codes("RM115")
    def has_no_markdown_lint_errors(self):
        """
        Will check if the readme has markdownlint.
        Returns: a boolean to fail the validations according to markdownlint

        """
        if mdx_server_is_up():
            markdown_response = run_markdownlint(self.readme_content)
            if markdown_response.has_errors:
                error_message, error_code = Errors.readme_lint_errors(
                    self.file_path_str
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        else:
            return self.should_run_mdx_validation()
        return True

    @error_codes("RM107")
    def verify_template_not_in_readme(self):
        """
        Checks if there are the generic sentence '%%FILL HERE%%' in the README content.

        Return:
            True if '%%FILL HERE%%' does not exist in the README content, and False if it does.
        """
        is_valid = True
        invalid_lines = self.check_readme_content_contain_text(
            text_list=["%%FILL HERE%%"]
        )

        if invalid_lines:
            error_message, error_code = Errors.template_sentence_in_readme(
                invalid_lines
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @error_codes("RM113")
    def verify_copyright_section_in_readme_content(self):
        """
        Checks if there are words related to copyright section in the README content.

        Returns:
            True if related words does not exist in the README content, and False if it does.
        """
        is_valid = True
        invalid_lines = self.check_readme_content_contain_text(
            text_list=["BSD", "MIT", "Copyright", "proprietary"], to_split=True
        )

        if invalid_lines:
            error_message, error_code = Errors.copyright_section_in_readme_error(
                invalid_lines
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @staticmethod
    def start_mdx_server(
        handle_error: Optional[Callable] = None, file_path: Optional[str] = None
    ):
        """
        This function will either start a local server or a server in docker depending on the dependencies installed
        If the server is already up a contextmanager yieling true will be returned without restarting the server
        Args:
            handle_error:
            file_path:

        Returns:
            A ContextManager

        """

        @contextmanager
        def empty_context_mgr(bool):
            yield bool

        with ReadMeValidator._MDX_SERVER_LOCK:
            if mdx_server_is_up():  # this allows for this context to be reentrant
                logger.debug("server is already up. Not restarting")
                return empty_context_mgr(True)
            if ReadMeValidator.are_modules_installed_for_verify(CONTENT_PATH):  # type: ignore
                ReadMeValidator.add_node_env_vars()
                return start_local_MDX_server(handle_error, file_path)
            elif ReadMeValidator.is_docker_available():
                return start_docker_MDX_server(handle_error, file_path)
        return empty_context_mgr(False)

    @staticmethod
    def add_node_env_vars():
        content_path = CONTENT_PATH
        node_modules_path = content_path / Path("node_modules")  # type: ignore
        os.environ["NODE_PATH"] = (
            str(node_modules_path) + os.pathsep + os.getenv("NODE_PATH", "")
        )

    @staticmethod
    def _get_error_lists():
        return FOUND_FILES_AND_ERRORS, FOUND_FILES_AND_IGNORED_ERRORS
