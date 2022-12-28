import base64
import copy
import glob
import os
import re
from pathlib import Path
from typing import Dict, List, Union

import click
from inflection import dasherize, underscore
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.constants import (
    DEFAULT_IMAGE_PREFIX,
    TYPE_TO_EXTENSION,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (
    LOG_COLORS,
    arg_to_list,
    find_type,
    get_mp_tag_parser,
    get_pack_name,
    get_yaml,
    get_yml_paths_in_dir,
    print_color,
    print_warning,
)
from demisto_sdk.commands.prepare_content.unifier import Unifier

json = JSON_Handler()

PACK_METADATA_PATH = "pack_metadata.json"
CONTRIBUTOR_DISPLAY_NAME = " ({} Contribution)"
CONTRIBUTOR_DETAILED_DESC = (
    "### {} Contributed Integration\n"
    "#### Integration Author: {}\n"
    "Support and maintenance for this integration are provided by the author. "
    "Please use the following contact details:"
)

CONTRIBUTOR_COMMUNITY_DETAILED_DESC = (
    "### Community Contributed Integration\n "
    "#### Integration Author: {}\n "
    "No support or maintenance is provided by the author. Customers are encouraged "
    "to engage with the user community for questions and guidance at the "
    "[Cortex XSOAR Live Discussions](https://live.paloaltonetworks.com/"
    "t5/cortex-xsoar-discussions/bd-p/Cortex_XSOAR_Discussions)."
)

CONTRIBUTORS_LIST = ["partner", "developer", "community"]
COMMUNITY_CONTRIBUTOR = "community"
INTEGRATIONS_DOCS_REFERENCE = "https://xsoar.pan.dev/docs/reference/integrations/"


class IntegrationScriptUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path,
        data: dict,
        marketplace: MarketplaceVersions = None,
        custom: str = "",
        image_prefix: str = DEFAULT_IMAGE_PREFIX,
        **kwargs,
    ):
        print(f"Unifying package: {path}")
        if path.parent.name in {"Integrations", "Scripts"}:
            return data
        package_path = path.parent
        is_script_package = isinstance(data.get("script"), str)
        script_obj = data

        if not is_script_package:  # integration
            IntegrationScriptUnifier.update_hidden_parameters_value(
                data, marketplace
            )  # changes data
            script_obj = data["script"]
        script_type = TYPE_TO_EXTENSION[script_obj["type"]]
        try:
            IntegrationScriptUnifier.get_code_file(package_path, script_type)
        except ValueError:
            print_warning(
                f"No code file found for {path}, assuming it is already unified"
            )
            return data
        yml_unified = copy.deepcopy(data)

        yml_unified, _ = IntegrationScriptUnifier.insert_script_to_yml(
            package_path, script_type, yml_unified, data, is_script_package
        )
        if not is_script_package:
            yml_unified, _ = IntegrationScriptUnifier.insert_image_to_yml(
                package_path, yml_unified, is_script_package, image_prefix
            )
            yml_unified, _ = IntegrationScriptUnifier.insert_description_to_yml(
                package_path, yml_unified, is_script_package
            )
            (
                contributor_type,
                metadata_data,
            ) = IntegrationScriptUnifier.get_contributor_data(
                package_path, is_script_package
            )

            if IntegrationScriptUnifier.is_contributor_pack(contributor_type):
                contributor_email = metadata_data.get("email", "")
                contributor_url = metadata_data.get("url", "")
                author = metadata_data.get("author")
                yml_unified = IntegrationScriptUnifier.add_contributors_support(
                    yml_unified,
                    contributor_type,
                    contributor_email,
                    contributor_url,
                    author,
                )

        if custom:
            yml_unified = IntegrationScriptUnifier.add_custom_section(
                yml_unified, custom, is_script_package
            )

        print_color(f"Created unified yml: {path.name}", LOG_COLORS.GREEN)
        return yml_unified

    @staticmethod
    def update_hidden_parameters_value(
        data: dict, marketplace: MarketplaceVersions = None
    ) -> None:
        """
        The `hidden` attribute of each param may be a bool (affecting both marketplaces),
        or a list of marketplaces where this param is hidden.

        This method replaces a list with a boolean, according to the self.marketplace value.
        Boolean values are left untouched.
        """
        if not marketplace:
            return

        for i, param in enumerate(data.get("configuration", ())):
            if isinstance(hidden := (param.get("hidden")), list):
                # converts list to bool
                data["configuration"][i]["hidden"] = marketplace in hidden

    @staticmethod
    def add_custom_section(
        unified_yml: Dict, custom: str = "", is_script_package: bool = False
    ) -> Dict:
        """
        Args:
            unified_yml - The unified_yml
        Returns:
             the unified yml with the id/name/display appended with the custom label
             if the fields exsits.
        """
        to_append = custom if is_script_package else f" - {custom}"
        if unified_yml.get("name"):
            unified_yml["name"] += to_append
        if unified_yml.get("commonfields", {}).get("id"):
            unified_yml["commonfields"]["id"] += to_append
        if not is_script_package:
            if unified_yml.get("display"):
                unified_yml["display"] += to_append

        return unified_yml

    @staticmethod
    def insert_image_to_yml(
        package_path: Path,
        yml_unified: dict,
        is_script_package: bool = False,
        image_prefix: str = DEFAULT_IMAGE_PREFIX,
    ):
        image_data, found_img_path = IntegrationScriptUnifier.get_data(
            package_path, "*png", is_script_package
        )
        if image_data:
            image_data = image_prefix + base64.b64encode(image_data).decode("utf-8")
            yml_unified["image"] = image_data
        else:
            click.secho(f"Failed getting image data for {package_path}", fg="yellow")

        return yml_unified, found_img_path

    @staticmethod
    def insert_description_to_yml(
        package_path: Path, yml_unified: dict, is_script_package: bool
    ):
        desc_data, found_desc_path = IntegrationScriptUnifier.get_data(
            package_path, "*_description.md", is_script_package
        )

        detailed_description = ""
        if desc_data:
            detailed_description = get_mp_tag_parser().parse_text(
                FoldedScalarString(desc_data.decode("utf-8"))
            )

        integration_doc_link = ""
        if "[View Integration Documentation]" not in detailed_description:
            integration_doc_link = IntegrationScriptUnifier.get_integration_doc_link(
                package_path, yml_unified
            )
        if integration_doc_link:
            if detailed_description:
                detailed_description += "\n\n---\n" + integration_doc_link
            else:
                detailed_description += integration_doc_link
        if detailed_description:
            yml_unified["detaileddescription"] = detailed_description
        return yml_unified, found_desc_path

    @staticmethod
    def get_data(path: Path, extension: str, is_script_package: bool):
        data_path = glob.glob(os.path.join(path, extension))
        data = None
        found_data_path = None
        if not is_script_package and data_path:
            found_data_path = data_path[0]
            with open(found_data_path, "rb") as data_file:
                data = data_file.read()

        return data, found_data_path

    @staticmethod
    def get_code_file(package_path: Path, script_type):
        """Return the first code file in the specified directory path
        :param script_type: script type: .py, .js, .ps1
        :type script_type: str
        :return: path to found code file
        :rtype: str
        """
        package_path = str(package_path)
        ignore_regex = (
            r"CommonServerPython\.py|CommonServerUserPython\.py|demistomock\.py|_test\.py"
            r"|conftest\.py|__init__\.py|ApiModule\.py|vulture_whitelist\.py"
            r"|CommonServerPowerShell\.ps1|CommonServerUserPowerShell\.ps1|demistomock\.ps1|\.Tests\.ps1"
        )
        if package_path.endswith("/"):
            package_path = package_path[:-1]  # remove the last / as we use os.path.join
        if package_path.endswith(os.path.join("Scripts", "CommonServerPython")):
            return os.path.join(package_path, "CommonServerPython.py")
        if package_path.endswith(os.path.join("Scripts", "CommonServerUserPython")):
            return os.path.join(package_path, "CommonServerUserPython.py")
        if package_path.endswith(os.path.join("Scripts", "CommonServerPowerShell")):
            return os.path.join(package_path, "CommonServerPowerShell.ps1")
        if package_path.endswith(os.path.join("Scripts", "CommonServerUserPowerShell")):
            return os.path.join(package_path, "CommonServerUserPowerShell.ps1")
        if package_path.endswith("ApiModule"):
            return os.path.join(
                package_path, os.path.basename(os.path.normpath(package_path)) + ".py"
            )

        script_path_list = list(
            filter(
                lambda x: not re.search(ignore_regex, x, flags=re.IGNORECASE),
                sorted(glob.glob(os.path.join(package_path, "*" + script_type))),
            )
        )
        if script_path_list:
            return script_path_list[0]
        else:
            raise ValueError(
                f"Could not find a code file {script_type} in {package_path}"
            )

    @staticmethod
    def insert_script_to_yml(
        package_path: Path,
        script_type: str,
        yml_unified: dict,
        yml_data: dict,
        is_script_package: bool,
    ):
        script_path = IntegrationScriptUnifier.get_code_file(package_path, script_type)
        with open(script_path, encoding="utf-8") as script_file:
            script_code = script_file.read()

        # Check if the script imports an API module. If it does,
        # the API module code will be pasted in place of the import.
        imports_to_names = IntegrationScriptUnifier.check_api_module_imports(
            script_code
        )
        script_code = IntegrationScriptUnifier.insert_module_code(
            script_code, imports_to_names
        )

        if script_type == ".py":
            clean_code = IntegrationScriptUnifier.clean_python_code(script_code)
            if "CommonServer" not in yml_data["name"]:
                # CommonServerPython has those line hard-coded so there is no need to add them here.
                clean_code = (
                    f"register_module_line('{yml_data['name']}', 'start', __line__())\n"
                    f"{clean_code}\n"
                    f"register_module_line('{yml_data['name']}', 'end', __line__())\n"
                )
        elif script_type == ".ps1":
            clean_code = IntegrationScriptUnifier.clean_pwsh_code(script_code)
        else:
            # for JS scripts
            clean_code = script_code

        if is_script_package:
            if yml_data.get("script", "") not in ("", "-"):
                print_warning(
                    f"Script section is not empty in package {package_path}."
                    f"It should be blank or a dash(-)."
                )

            yml_unified["script"] = FoldedScalarString(clean_code)

        else:
            if yml_data["script"].get("script", "") not in ("", "-"):
                print_warning(
                    f"Script section is not empty in package {package_path}."
                    f"It should be blank or a dash(-)."
                )

            yml_unified["script"]["script"] = FoldedScalarString(clean_code)

        return yml_unified, script_path

    @staticmethod
    def get_script_or_integration_package_data(package_path: Path):
        # should be static method
        _, yml_path = get_yml_paths_in_dir(str(package_path), error_msg="")

        if not yml_path:
            raise Exception(
                f"No yml files found in package path: {package_path}. "
                "Is this really a package dir?"
            )

        if find_type(yml_path) in (FileType.SCRIPT, FileType.TEST_SCRIPT):
            code_type = get_yaml(yml_path).get("type")
        else:
            code_type = get_yaml(yml_path).get("script", {}).get("type")
        code_path = IntegrationScriptUnifier.get_code_file(
            package_path, TYPE_TO_EXTENSION[code_type]
        )
        with open(code_path, encoding="utf-8") as code_file:
            code = code_file.read()

        return yml_path, code

    @staticmethod
    def check_api_module_imports(script_code: str) -> Dict[str, str]:
        """
        Checks integration code for API module imports
        :param script_code: The integration code
        :return: The import string and the imported module name
        """

        # General regex to find API module imports, for example: "from MicrosoftApiModule import *  # noqa: E402"
        module_regex = r"from ([\w\d]+ApiModule) import \*(?:  # noqa: E402)?"

        module_matches = re.finditer(module_regex, script_code)

        return {
            module_match.group(): module_match.group(1)
            for module_match in module_matches
        }

    @staticmethod
    def insert_module_code(script_code: str, import_to_name: Dict[str, str]) -> str:
        """
        Inserts API module in place of an import to the module according to the module name
        :param script_code: The integration code
        :param import_to_name: A dictionary where the keys are The module import string to replace
        and the values are The module name
        :return: The integration script with the module code appended in place of the import
        """
        for module_import, module_name in import_to_name.items():

            module_path = os.path.join(
                "./Packs", "ApiModules", "Scripts", module_name, module_name + ".py"
            )
            module_code = IntegrationScriptUnifier._get_api_module_code(
                module_name, module_path
            )

            # the wrapper numbers represents the number of generated lines added
            # before (negative) or after (positive) the registration line
            module_code = (
                f"\n### GENERATED CODE ###: {module_import}\n"
                f"# This code was inserted in place of an API module.\n"
                f"register_module_line('{module_name}', 'start', __line__(), wrapper=-3)\n"
                f"{module_code}\n"
                f"register_module_line('{module_name}', 'end', __line__(), wrapper=1)\n"
                f"### END GENERATED CODE ###"
            )

            script_code = script_code.replace(module_import, module_code)
        return script_code

    @staticmethod
    def _get_api_module_code(module_name, module_path):
        """
        Attempts to get the API module code from the ApiModules pack.
        :param module_name: The API module name
        :param module_path: The API module code file path
        :return: The API module code
        """
        try:
            with open(module_path, encoding="utf-8") as script_file:
                module_code = script_file.read()
        except Exception as exc:
            raise ValueError(
                f"Could not retrieve the module [{module_name}] code: {str(exc)}"
            )

        return module_code

    @staticmethod
    def clean_python_code(script_code, remove_print_future=True):
        # we use '[ \t]' and not \s as we don't want to match newline
        script_code = re.sub(
            r"import demistomock as demisto[ \t]*(#.*)?", "", script_code
        )
        script_code = re.sub(
            r"from CommonServerPython import \*[ \t]*(#.*)?", "", script_code
        )
        script_code = re.sub(
            r"from CommonServerUserPython import \*[ \t]*(#.*)?", "", script_code
        )
        # print function is imported in python loop
        if remove_print_future:  # docs generation requires to leave this
            script_code = re.sub(
                r"from __future__ import print_function[ \t]*(#.*)?", "", script_code
            )
        return script_code

    @staticmethod
    def clean_pwsh_code(script_code):
        script_code = script_code.replace(". $PSScriptRoot\\demistomock.ps1", "")
        script_code = script_code.replace(
            ". $PSScriptRoot\\CommonServerPowerShell.ps1", ""
        )
        return script_code

    @staticmethod
    def get_pack_path(package_path: Path):
        return str(package_path).split("Integrations")[0]

    @staticmethod
    def is_contributor_pack(contributor_type):
        """Checks if the pack is a contribution.
        Args:
            contributor_type (str): The contributor type.
        Returns:
            (bool). True if it is a contributed pack, False otherwise.
        """
        if contributor_type in CONTRIBUTORS_LIST:
            return True
        return False

    @staticmethod
    def get_contributor_data(package_path: Path, is_script_package: bool = False):
        """Gets contributor data.

        Returns:
            (str, dict). Contributor type and file data.
        """
        pack_path = IntegrationScriptUnifier.get_pack_path(package_path)
        pack_metadata_data, pack_metadata_path = IntegrationScriptUnifier.get_data(
            pack_path, PACK_METADATA_PATH, is_script_package
        )

        if pack_metadata_data:
            try:
                json_pack_metadata = json.loads(pack_metadata_data)
            except json.JSONDecodeError as e:
                pack_name: str = get_pack_name(pack_path)
                raise Exception(
                    f"Failed to load pack metadata of pack {pack_name}: {str(e)}"
                ) from e
            support_field = json_pack_metadata.get("support")
            return support_field, json_pack_metadata
        return None, None

    @staticmethod
    def add_contributors_support(
        unified_yml: Dict,
        contributor_type: str,
        contributor_email: Union[str, List[str]],
        contributor_url: str,
        author: str = "",
    ) -> Dict:
        """Add contributor support to the unified file - text in the display name and detailed description.

        Args:
            unified_yml (dict): The unified yaml file.
            contributor_type (str): The contributor type - partner / developer / community
            contributor_email (str): The contributor email.
            contributor_url (str): The contributor url.
            author (str): The packs author.

        Returns:
            The unified yaml file (dict).
        """
        if " Contribution)" not in unified_yml["display"]:
            unified_yml["display"] += CONTRIBUTOR_DISPLAY_NAME.format(
                contributor_type.capitalize()
            )
        existing_detailed_description = unified_yml.get("detaileddescription", "")
        if contributor_type == COMMUNITY_CONTRIBUTOR:
            contributor_description = CONTRIBUTOR_COMMUNITY_DETAILED_DESC.format(author)
        else:
            contributor_description = CONTRIBUTOR_DETAILED_DESC.format(
                contributor_type.capitalize(), author
            )
            if contributor_email:
                email_list: List[str] = arg_to_list(contributor_email, ",")
                for email in email_list:
                    contributor_description += (
                        f"\n- **Email**: [{email}](mailto:{email})"
                    )
            if contributor_url:
                contributor_description += (
                    f"\n- **URL**: [{contributor_url}]({contributor_url})"
                )

        contrib_details = re.findall(
            r"### .* Contributed Integration", existing_detailed_description
        )

        if not contrib_details:
            unified_yml["detaileddescription"] = (
                contributor_description + "\n***\n" + existing_detailed_description
            )

        return unified_yml

    @staticmethod
    def get_integration_doc_link(package_path: Path, unified_yml: Dict) -> str:
        """Generates the integration link to the integration documentation

        Args:
            unified_yml (Dict): The integration YAML dictionary object

        Returns:
            str: The integration doc markdown link to add to the detailed description (if reachable)
        """
        normalized_integration_id = IntegrationScriptUnifier.normalize_integration_id(
            unified_yml["commonfields"]["id"]
        )
        integration_doc_link = INTEGRATIONS_DOCS_REFERENCE + normalized_integration_id

        readme_path = os.path.join(package_path, "README.md")
        if os.path.isfile(readme_path) and os.stat(readme_path).st_size != 0:
            # verify README file exists and is not empty
            return f"[View Integration Documentation]({integration_doc_link})"
        else:
            click.secho(
                f"Did not find README in {package_path}, not adding integration doc link",
                fg="bright_cyan",
            )
            return ""

    @staticmethod
    def normalize_integration_id(integration_id: str) -> str:
        """Normalizes integration ID to an identifier to be used as the integration documentation ID

        Examples
            >>> normalize_integration_id('Cortex XDR - IOC')
            cortex-xdr---ioc
            >>> normalize_integration_id('Whois')
            whois
            >>> normalize_integration_id('SomeIntegration')
            some-integration

        Args:
            integration_id (str): The integration ID to normalize

        Returns:
            str: The normalized identifier
        """
        dasherized_integration_id = dasherize(underscore(integration_id)).replace(
            " ", "-"
        )
        # remove all non-word characters (dash is ok)
        return re.sub(r"[^\w-]", "", dasherized_integration_id)
