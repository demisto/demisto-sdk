import math
import os
import string
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import DefaultDict

import PyPDF2
from bs4 import BeautifulSoup

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_UPSTREAM,
    PACKS_DIR,
    PACKS_INTEGRATION_README_REGEX,
    PACKS_WHITELIST_FILE_NAME,
    FileType,
    re,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_file,
    get_pack_name,
    is_file_path_in_pack,
    run_command,
)

# secrets settings
# Entropy score is determined by shanon's entropy algorithm, most English words will score between 1.5 and 3.5

ENTROPY_THRESHOLD = 4.0
ACCEPTED_FILE_STATUSES = ["m", "a"]
SKIPPED_FILES = {
    "secrets_white_list",
    "id_set.json",
    "conf.json",
    "Pipfile",
    "secrets-ignore",
    "ami_builds.json",
    "secrets_test.py",
    "secrets.py",
    "constants.py",
    "core.py",
    "pack_metadata.json",
    "dev-requirements-py2.txt",
    "dev-requirements-py3.txt",
    ".vscode/extensions.json",
    ".devcontainer/devcontainer.json",
}
TEXT_FILE_TYPES = {
    ".yml",
    ".py",
    ".json",
    ".md",
    ".txt",
    ".sh",
    ".ini",
    ".eml",
    "",
    ".csv",
    ".js",
    ".pdf",
    ".html",
    ".ps1",
    ".xif",
}
SKIP_FILE_TYPE_ENTROPY_CHECKS = {".eml"}
SKIP_DEMISTO_TYPE_ENTROPY_CHECKS = {"playbook-"}
YML_FILE_EXTENSION = ".yml"

# disable-secrets-detection-start
# secrets
URLS_REGEX = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
IPV6_REGEX = (
    r"(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1"
    r"[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::"
    r"(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]"
    r"{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|"
    r"(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|"
    r"(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}"
    r"|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}"
    r"(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])"
    r"\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}"
    r"[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|"
    r"(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}"
    r"|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:"
    r"(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4]"
    r"[0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]"
    r"{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]"
    r"|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|"
    r"(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|"
    r"(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)"
)
IPV4_REGEX = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
DATES_REGEX = r"((\d{4}[/.-]\d{2}[/.-]\d{2})[T\s](\d{2}:?\d{2}:?\d{2}:?(\.\d{5,10})?([+-]\d{2}:?\d{2})?Z?)?)"
# false positives
UUID_REGEX = r"([\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{8,12})"
# find any substring
WHILEIST_REGEX = r"\S*{}\S*"


# disable-secrets-detection-end


class SecretsValidator:
    def __init__(
        self,
        configuration=Configuration(),
        is_circle=False,
        ignore_entropy=False,
        white_list_path="",
        input_path="",
        prev_ver=None,
    ):
        self.input_paths = input_path.split(",") if input_path else None
        self.configuration = configuration
        self.is_circle = is_circle
        self.white_list_path = white_list_path
        self.ignore_entropy = ignore_entropy
        self.prev_ver = prev_ver
        if self.prev_ver and not self.prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = f"{DEMISTO_GIT_UPSTREAM}/" + self.prev_ver

    def get_secrets(self, commit, is_circle):
        secret_to_location_mapping = {}
        if self.input_paths:
            secrets_file_paths = self.input_paths
        else:
            secrets_file_paths = self.get_all_diff_text_files(commit, is_circle)
        # If a input path supplied, should not run on git. If not supplied make sure not in middle of merge.
        if not run_command("git rev-parse -q --verify MERGE_HEAD") or self.input_paths:
            secret_to_location_mapping = self.search_potential_secrets(
                secrets_file_paths, self.ignore_entropy
            )
            if secret_to_location_mapping:
                secrets_found_string = "Secrets were found in the following files:"
                for file_name in secret_to_location_mapping:
                    for line in sorted(secret_to_location_mapping[file_name]):
                        secrets_found_string += (
                            "\nIn File: " + f"{file_name}:{line}" + "\n"
                        )
                        if len(secret_to_location_mapping[file_name][line]) == 1:
                            secrets_found_string += f"Secret found: {secret_to_location_mapping[file_name][line][0]}\n"
                        else:
                            secrets_found_string += f"Secrets found: {secret_to_location_mapping[file_name][line]}\n"

                if not is_circle:
                    secrets_found_string += "\n\nRemove or whitelist secrets in order to proceed, then re-commit\n"

                else:
                    secrets_found_string += (
                        "\n\nThe secrets were exposed in public repository,"
                        " remove the files asap and report it.\n"
                    )

                secrets_found_string += (
                    "For more information about whitelisting visit: "
                    "https://docs-cortex.paloaltonetworks.com/r/1/Demisto-SDK-Guide/secrets"
                )
                logger.info(f"<red>{secrets_found_string}</red>")
        return secret_to_location_mapping

    def reformat_secrets_output(self, secrets_list):
        """
        Get a list of secrets and reformat it's output
        :param secrets_list: List of secrets
        :return: str: List of secrets
        """
        return "\n".join(secrets_list) if secrets_list else ""

    def get_all_diff_text_files(self, commit, is_circle):
        """
        Get all new/modified text files that need to be searched for secrets
        :param branch_name: current branch being worked on
        :param is_circle: boolean to check if being ran from circle
        :return: list: list of text files
        """
        if is_circle:
            prev_ver = self.prev_ver
            if not prev_ver:
                self.git_util = Content.git_util()
                prev_ver = self.git_util.handle_prev_ver()[1]
            if not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
                prev_ver = f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver
            logger.info(f"Running secrets validation against {prev_ver}")

            changed_files_string = run_command(
                f"git diff --name-status {prev_ver}...{commit}"
            )
        else:
            logger.info("Running secrets validation on all changes")
            changed_files_string = run_command(
                "git diff --name-status --no-merges HEAD"
            )
        return list(self.get_diff_text_files(changed_files_string))

    def get_diff_text_files(self, files_string):
        """Filter out only added/modified text files from git diff
        :param files_string: string representing the git diff files
        :return: text_files_list: string of full path to text files
        """
        # file statuses to filter from the diff, no need to test deleted files.
        all_files = files_string.split("\n")
        text_files_list = set()
        for file_name in all_files:
            file_data: list = list(filter(None, file_name.split("\t")))
            if not file_data:
                continue
            file_status = file_data[0]
            if "r" in file_status.lower():
                file_path = file_data[2]
            else:
                file_path = file_data[1]
            # only modified/added file, text readable, exclude white_list file
            if (
                file_status.lower() in ACCEPTED_FILE_STATUSES
                or "r" in file_status.lower()
            ) and self.is_text_file(file_path):
                if not any(skipped_file in file_path for skipped_file in SKIPPED_FILES):
                    text_files_list.add(file_path)
        return text_files_list

    @staticmethod
    def is_text_file(file_path):
        file_extension = os.path.splitext(file_path)[1]
        if file_extension in TEXT_FILE_TYPES:
            return True
        return False

    def search_potential_secrets(
        self, secrets_file_paths: list, ignore_entropy: bool = False
    ):
        """Returns potential secrets(sensitive data) found in committed and added files
        :param secrets_file_paths: paths of files that are being commited to git repo
        :param ignore_entropy: If True then will ignore running entropy algorithm for finding potential secrets

        :return: dictionary(filename: (list)secrets) of strings sorted by file name for secrets found in files
        """
        secret_to_location_mapping: DefaultDict[str, defaultdict] = defaultdict(
            lambda: defaultdict(list)
        )
        for file_path in secrets_file_paths:
            # Get if file path in pack and pack name
            is_pack = is_file_path_in_pack(file_path)
            pack_name = get_pack_name(file_path)
            # Get generic/ioc/files white list sets based on if pack or not
            (
                secrets_white_list,
                ioc_white_list,
                files_white_list,
            ) = self.get_white_listed_items(is_pack, pack_name)
            # Skip white listed files

            if file_path in files_white_list:
                logger.info(
                    f"Skipping secrets detection for file: {file_path} as it is white listed"
                )
                continue
            # Init vars for current loop
            file_name = Path(file_path).name
            _, file_extension = os.path.splitext(file_path)
            # get file contents
            file_contents = self.get_file_contents(file_path, file_extension)
            # if detected disable-secrets comments, removes the line/s
            file_contents = self.remove_secrets_disabled_line(file_contents)
            # in packs regard all items as regex as well, reset pack's whitelist in order to avoid repetition later
            if is_pack:
                file_contents = self.remove_whitelisted_items_from_file(
                    file_contents, secrets_white_list
                )

            yml_file_contents = self.get_related_yml_contents(file_path)
            # Add all context output paths keywords to whitelist temporary
            if file_extension == YML_FILE_EXTENSION or yml_file_contents:
                temp_white_list = self.create_temp_white_list(
                    yml_file_contents if yml_file_contents else file_contents
                )
                secrets_white_list = secrets_white_list.union(temp_white_list)
            # Search by lines after strings with high entropy / IoCs regex as possibly suspicious
            for line_num, line in enumerate(file_contents.split("\n")):
                # REGEX scanning for IOCs and false positive groups
                regex_secrets, false_positives = self.regex_for_secrets(line)
                for regex_secret in regex_secrets:
                    if not any(
                        ioc.lower() in regex_secret.lower() for ioc in ioc_white_list
                    ):
                        secret_to_location_mapping[file_path][line_num + 1].append(
                            regex_secret
                        )
                # added false positives into white list array before testing the strings in line

                secrets_white_list = secrets_white_list.union(false_positives)

                if not ignore_entropy:
                    # due to nature of eml files, skip string by string secret detection - only regex
                    if file_extension in SKIP_FILE_TYPE_ENTROPY_CHECKS or any(
                        demisto_type in file_name
                        for demisto_type in SKIP_DEMISTO_TYPE_ENTROPY_CHECKS
                    ):
                        continue
                    line = self.remove_false_positives(line)
                    # calculate entropy for each string in the file
                    for string_ in line.split():
                        # compare the lower case of the string against both generic whitelist & temp white list
                        if not any(
                            white_list_string.lower() in string_.lower()
                            for white_list_string in secrets_white_list
                        ):
                            entropy = self.calculate_shannon_entropy(string_)
                            if entropy >= ENTROPY_THRESHOLD:
                                secret_to_location_mapping[file_path][
                                    line_num + 1
                                ].append(string_)

        return secret_to_location_mapping

    @staticmethod
    def remove_whitelisted_items_from_file(
        file_content: str, secrets_white_list: set
    ) -> str:
        """Removes whitelisted items from file content

        Arguments:
            file_content (str): The content of the file to remove the whitelisted item from
            secrets_white_list (set): List of whitelist items to remove from the file content.

        Returns:
            str: The file content with the whitelisted items removed.
        """
        for item in secrets_white_list:
            try:
                file_content = re.sub(
                    WHILEIST_REGEX.format(re.escape(item)), "", file_content
                )
            except re.error as err:
                error_string = f"Could not use secrets with item: {item}"
                logger.info(f"<red>{error_string}</red>")
                raise re.error(error_string, str(err))
        return file_content

    @staticmethod
    def create_temp_white_list(file_contents) -> set:
        temp_white_list: set = set()
        context_paths = re.findall(r"contextPath: (\S+\.+\S+)", file_contents)
        for context_path in context_paths:
            context_path = context_path.split(".")
            context_path = [
                white_item.lower() for white_item in context_path if len(white_item) > 4
            ]
            temp_white_list = temp_white_list.union(context_path)

        return temp_white_list

    def get_related_yml_contents(self, file_path):
        # if script or readme file, search for yml in order to retrieve temp white list
        yml_file_contents = ""
        # Validate if it is integration documentation file or supported file extension
        if find_type(file_path) in [
            FileType.PYTHON_FILE,
            FileType.README,
            FileType.POWERSHELL_FILE,
        ]:
            yml_file_contents = self.retrieve_related_yml(os.path.dirname(file_path))
        return yml_file_contents

    @staticmethod
    def retrieve_related_yml(integration_path):
        matching_yml_file_contents = None
        yml_file = str(Path(integration_path, Path(integration_path).name + ".yml"))
        if Path(yml_file).exists():
            with open(yml_file, encoding="utf-8") as matching_yml_file:
                matching_yml_file_contents = matching_yml_file.read()
        return matching_yml_file_contents

    @staticmethod
    def regex_for_secrets(line):
        """Scans for IOCs with potentially low entropy score
        :param line: line to test as string representation (string)
        :return  potential_secrets (list) IOCs found via regex, false_positives (list) Non secrets with high entropy
        """
        potential_secrets = []
        false_positives = []

        # Dates REGEX for false positive preventing since they have high entropy
        dates = re.findall(DATES_REGEX, line)
        if dates:
            false_positives += [date[0].lower() for date in dates]
        # UUID REGEX - for false positives
        uuids = re.findall(UUID_REGEX, line)
        if uuids:
            false_positives += uuids
        # docker images version are detected as ips. so we ignore and whitelist them
        # example: dockerimage: demisto/duoadmin:1.0.0.147
        re_res = re.search(r"dockerimage:\s*\w*demisto/\w+:(\d+.\d+.\d+.\d+)", line)
        if re_res:
            docker_version = re_res.group(1)
            false_positives.append(docker_version)
            line = line.replace(docker_version, "")
        # URL REGEX
        urls = re.findall(URLS_REGEX, line)
        if urls:
            potential_secrets += urls
        # EMAIL REGEX
        emails = re.findall(EMAIL_REGEX, line)
        if emails:
            potential_secrets += emails
        # IPV6 REGEX
        ipv6_list = re.findall(IPV6_REGEX, line)
        if ipv6_list:
            for ipv6 in ipv6_list:
                if ipv6 != "::" and len(ipv6) > 4:
                    potential_secrets.append(ipv6)
        # IPV4 REGEX
        ipv4_list = re.findall(IPV4_REGEX, line)
        if ipv4_list:
            potential_secrets += ipv4_list

        return potential_secrets, false_positives

    @staticmethod
    def calculate_shannon_entropy(data) -> float:
        """Algorithm to determine the randomness of a given data.
        Higher is more random/complex, most English words will yield in average result of 3
        :param data: could be either a list/dict or a string.
        :return: entropy: entropy score.
        """
        if not data:
            return 0
        entropy = 0.0
        # each unicode code representation of all characters which are considered printable
        for char in (ord(c) for c in string.printable):
            # probability of event X
            p_x = float(data.count(chr(char))) / len(data)
            if p_x > 0:
                # the information in every possible news, in bits
                entropy += -p_x * math.log(p_x, 2)
        return entropy

    def get_white_listed_items(self, is_pack, pack_name):
        (
            final_white_list,
            ioc_white_list,
            files_white_list,
        ) = self.get_generic_white_list(self.white_list_path)
        if is_pack:
            pack_whitelist_path = os.path.join(
                PACKS_DIR, pack_name, PACKS_WHITELIST_FILE_NAME
            )
            pack_white_list, _, pack_files_white_list = self.get_packs_white_list(
                pack_whitelist_path, pack_name
            )
            final_white_list.extend(pack_white_list)
            files_white_list.extend(pack_files_white_list)

        final_white_list = set(final_white_list)
        if "" in final_white_list:
            # remove('') is ignoring empty lines in whitelists - users can accidentally add empty lines and those will
            # cause whitelisting of every string
            final_white_list.remove("")

        return final_white_list, set(ioc_white_list), set(files_white_list)

    @staticmethod
    def get_generic_white_list(whitelist_path):
        final_white_list = []
        ioc_white_list = []
        files_while_list = []
        if Path(whitelist_path).is_file():
            secrets_white_list_file = get_file(whitelist_path, raise_on_error=True)
            for name, white_list in secrets_white_list_file.items():  # type: ignore
                if name == "iocs":
                    for sublist in white_list:
                        ioc_white_list += [
                            white_item
                            for white_item in white_list[sublist]
                            if len(white_item) > 4
                        ]
                    final_white_list += ioc_white_list
                elif name == "files":
                    files_while_list = white_list
                else:
                    final_white_list += [
                        white_item for white_item in white_list if len(white_item) > 4
                    ]

        return final_white_list, ioc_white_list, files_while_list

    @staticmethod
    def get_packs_white_list(whitelist_path, pack_name=None):
        final_white_list = []
        files_white_list = []

        if Path(whitelist_path).is_file():
            with open(whitelist_path, encoding="utf-8") as secrets_white_list_file:
                temp_white_list = secrets_white_list_file.read().split("\n")
            for white_list_line in temp_white_list:
                if white_list_line.startswith("file:"):
                    white_list_line = os.path.join(
                        PACKS_DIR, pack_name, white_list_line[5:]
                    )
                    if not Path(white_list_line).is_file():
                        logger.info(
                            f"<yellow>{white_list_line} not found.\n"
                            "please add the file name in the following format\n"
                            "file:[Scripts|Integrations|Playbooks]/name/file.example\n"
                            "e.g. file:Scripts/HelloWorldScript/HelloWorldScript.py</yellow>"
                        )
                    files_white_list.append(white_list_line)
                else:
                    final_white_list.append(white_list_line)
        return final_white_list, [], files_white_list

    def get_file_contents(self, file_path, file_extension):
        try:
            # if pdf or README.md file, parse text
            integration_readme = re.match(
                pattern=PACKS_INTEGRATION_README_REGEX,
                string=file_path,
                flags=re.IGNORECASE,
            )
            if file_extension == ".pdf":
                file_contents = self.extract_text_from_pdf(file_path)
            elif file_extension == ".md" and integration_readme:
                file_contents = self.extract_text_from_md_html(file_path)
            else:
                # Open each file, read its contents in UTF-8 encoding to avoid unicode characters
                with open(
                    file_path, encoding="utf-8", errors="ignore"
                ) as commited_file:
                    file_contents = commited_file.read()
            file_contents = self.ignore_base64(file_contents)
            return file_contents
        except Exception as ex:
            logger.info(f"Failed opening file: {file_path}. Exception: {ex}")
            raise

    @staticmethod
    def extract_text_from_pdf(file_path):
        page_num = 0
        file_contents = ""
        try:
            pdf_file_obj = open("./" + file_path, "rb")
            pdf_reader = PyPDF2.PdfFileReader(pdf_file_obj)
            num_pages = pdf_reader.numPages
        except PyPDF2.errors.PdfReadError:
            logger.error(
                f"ERROR: Could not parse PDF file in path: {file_path} - ***Review Manually***"
            )
            return file_contents
        while page_num < num_pages:
            pdf_page = pdf_reader.getPage(page_num)
            page_num += 1
            file_contents += pdf_page.extractText()

        return file_contents

    @staticmethod
    def extract_text_from_md_html(file_path):
        try:
            with open(file_path) as html_page:
                soup = BeautifulSoup(html_page, features="html.parser")
                file_contents = soup.text
                return file_contents
        except Exception as ex:
            logger.info(
                f"<red>Unable to parse the following file {file_path} due to error {ex}</red>"
            )
            raise

    @staticmethod
    def remove_false_positives(line):
        false_positive = re.search(r"([^\s]*[(\[{].*[)\]}][^\s]*)", line)
        if false_positive:
            false_positive_result = false_positive.group(1)
            line = line.replace(false_positive_result, "")
        return line

    @staticmethod
    def is_secrets_disabled(line, skip_secrets):
        if bool(re.findall(r"(disable-secrets-detection-start)", line)):
            skip_secrets["skip_multi"] = True
        elif bool(re.findall(r"(disable-secrets-detection-end)", line)):
            skip_secrets["skip_multi"] = False
        elif bool(re.findall(r"(disable-secrets-detection)", line)):
            skip_secrets["skip_once"] = True
        return skip_secrets

    @staticmethod
    def ignore_base64(file_contents):
        base64_strings = re.findall(
            r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|"
            r"[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{4})",
            file_contents,
        )
        for base64_string in base64_strings:
            if len(base64_string) > 500:
                file_contents = file_contents.replace(base64_string, "")
        return file_contents

    @staticmethod
    @lru_cache()
    def get_current_commit() -> str:
        commit = run_command("git rev-parse HEAD")
        if not commit:
            return ""
        return commit.strip()

    def find_secrets(self):
        logger.info("<green>Starting secrets detection</green>")
        is_circle = self.is_circle
        commit = self.get_current_commit()
        secrets_found = self.get_secrets(commit, is_circle)
        if secrets_found:
            return True
        else:
            logger.info(
                "<green>Finished validating secrets, no secrets were found.</green>"
            )
            return False

    def remove_secrets_disabled_line(self, file_content: str) -> str:
        """Removes lines that have "disable-secrets-detection" from file content

        Arguments:
            file_content (str): The content of the file to remove the "disable-secrets-detection" lines from

        Returns:
            str: The new file content with the "disable-secrets-detection" lines removed.
        """
        skip_secrets = {"skip_once": False, "skip_multi": False}
        new_file_content = ""
        for line in file_content.split("\n"):
            skip_secrets = self.is_secrets_disabled(line, skip_secrets)
            if skip_secrets["skip_once"] or skip_secrets["skip_multi"]:
                skip_secrets["skip_once"] = False
            else:
                new_file_content += f"{line}\n"
        return new_file_content

    def run(self):
        if self.find_secrets():
            return 1

        else:
            return 0
