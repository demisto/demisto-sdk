import glob
import os
import re
import shutil
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from packaging.version import Version

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    CONNECTIONS_DIR,
    CORRELATION_RULES_DIR,
    DASHBOARDS_DIR,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DOC_FILES_DIR,
    EVENT_COLLECTOR,
    GENERIC_DEFINITIONS_DIR,
    GENERIC_FIELDS_DIR,
    GENERIC_MODULES_DIR,
    GENERIC_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATION_CATEGORIES,
    INTEGRATIONS_DIR,
    INTEGRATIONS_DIR_REGEX,
    JOBS_DIR,
    LAYOUTS_DIR,
    MARKETPLACE_LIVE_DISCUSSIONS,
    MARKETPLACES,
    MODELING_RULE_ID_SUFFIX,
    MODELING_RULES_DIR,
    PACK_INITIAL_VERSION,
    PACK_SUPPORT_OPTIONS,
    PACKS_DIR_REGEX,
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    REPORTS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    WIDGETS_DIR,
    WIZARDS_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
    XSOAR_AUTHOR,
    XSOAR_SUPPORT,
    XSOAR_SUPPORT_URL,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_pack_folder,
    get_common_server_path,
    get_file,
    get_pack_name,
    get_yaml,
    string_to_bool,
)
from demisto_sdk.commands.secrets.secrets import SecretsValidator

ANALYTICS_AND_SIEM_CATEGORY = "Analytics & SIEM"


def extract_values_from_nested_dict_to_a_set(given_dictionary: dict, return_set: set):
    """Recursively extracts values from a nested dictionary to a set.

    Args:
        given_dictionary: The nested dictionary to extract the values from.
        return_set: the set with the extracted values.

    """

    for value in given_dictionary.values():
        if isinstance(value, dict):  # value can be a dictionary
            extract_values_from_nested_dict_to_a_set(value, return_set)
        else:
            for secret in value:  # value is a list
                return_set.add(secret)


class Initiator:
    """Initiator creates a new pack/integration/script.

    Attributes:
        output (str): The directory in which init will create the new pack/integration/script
        name (str): The name for the new pack/integration/script directory.
        id (str): The id for the created script/integration.
        integration (bool): Indicates whether to create an integration.
        template (str): If an integration is initialized, specifies the integration template.
        script (bool): Indicates whether to create a script.
        full_output_path (str): The full path to the newly created pack/integration/script
    """

    TEST_DATA_DIR = "test_data"

    """ INTEGRATION TEMPLATES CONSTANTS """
    DEFAULT_INTEGRATION_TEMPLATE = "BaseIntegration"
    HELLO_WORLD_INTEGRATION = "HelloWorld"
    HELLO_IAM_WORLD_INTEGRATION = "HelloIAMWorld"
    HELLO_WORLD_FEED_INTEGRATION = "FeedHelloWorld"
    HELLO_WORLD_SLIM_INTEGRATION = "HelloWorldSlim"
    HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION = "HelloWorldEventCollector"
    HELLO_WORLD_PARSING_RULES = "HelloWorldParsingRules"
    HELLO_WORLD_MODELING_RULES = "HelloWorldModelingRules"

    INTEGRATION_TEMPLATE_OPTIONS = [
        HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION,
        HELLO_WORLD_INTEGRATION,
        HELLO_IAM_WORLD_INTEGRATION,
        HELLO_WORLD_FEED_INTEGRATION,
        DEFAULT_INTEGRATION_TEMPLATE,
        HELLO_WORLD_SLIM_INTEGRATION,
    ]

    TEMPLATE_INTEGRATION_NAME = "%%TEMPLATE_NAME%%"
    TEMPLATE_INTEGRATION_FILES = {
        f"{TEMPLATE_INTEGRATION_NAME}.py",
        f"{TEMPLATE_INTEGRATION_NAME}.yml",
        f"{TEMPLATE_INTEGRATION_NAME}_description.md",
        f"{TEMPLATE_INTEGRATION_NAME}_image.png",
        f"{TEMPLATE_INTEGRATION_NAME}_test.py",
        "README.md",
        "command_examples",
    }

    DEFAULT_INTEGRATION_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "baseintegration-dummy.json")
    }

    DEFAULT_EVENT_COLLECTOR_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "baseintegrationEventCollector-dummy.json")
    }

    TEMPLATE_MODELING_RULES_FILES = {
        "HelloWorldModelingRules_schema.json",
        "HelloWorldModelingRules.xif",
        "HelloWorldModelingRules.yml",
    }

    TEMPLATE_PARSING_RULES_FILES = {
        "HelloWorldParsingRules.xif",
        "HelloWorldParsingRules.yml",
    }

    HELLO_WORLD_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "domain_reputation.json"),
        os.path.join(TEST_DATA_DIR, "get_alert.json"),
        os.path.join(TEST_DATA_DIR, "ip_reputation.json"),
        os.path.join(TEST_DATA_DIR, "scan_results.json"),
        os.path.join(TEST_DATA_DIR, "search_alerts.json"),
        os.path.join(TEST_DATA_DIR, "update_alert_status.json"),
        os.path.join(TEST_DATA_DIR, "domain_reputation.json"),
    }

    HELLO_WORLD_FEED_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "build_iterator_results.json"),
        os.path.join(TEST_DATA_DIR, "get_indicators_command_results.json"),
        os.path.join(TEST_DATA_DIR, "FeedHelloWorld_mock.txt"),
    }

    HELLO_WORLD_SLIM_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "get_alert.json"),
        os.path.join(TEST_DATA_DIR, "update_alert_status.json"),
    }

    """ SCRIPT TEMPLATES CONSTANTS """
    DEFAULT_SCRIPT_TEMPLATE = "BaseScript"
    HELLO_WORLD_SCRIPT = "HelloWorldScript"

    SCRIPT_TEMPLATE_OPTIONS = [HELLO_WORLD_SCRIPT, DEFAULT_SCRIPT_TEMPLATE]

    TEMPLATE_SCRIPT_NAME = "%%TEMPLATE_NAME%%"
    TEMPLATE_SCRIPT_FILES = {
        f"{TEMPLATE_SCRIPT_NAME}.py",
        f"{TEMPLATE_SCRIPT_NAME}.yml",
        f"{TEMPLATE_SCRIPT_NAME}_test.py",
        "README.md",
    }

    DEFAULT_SCRIPT_TEST_DATA_FILES = {
        os.path.join(TEST_DATA_DIR, "basescript-dummy.json")
    }

    """ TEMPLATES PACKS CONSTANTS """
    DEFAULT_TEMPLATE_PACK_NAME = "StarterPack"
    HELLO_WORLD_PACK_NAME = "HelloWorld"
    DEFAULT_TEMPLATES = [DEFAULT_INTEGRATION_TEMPLATE, DEFAULT_SCRIPT_TEMPLATE]
    HELLO_WORLD_BASE_TEMPLATES = [HELLO_WORLD_SCRIPT, HELLO_WORLD_INTEGRATION]

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    PACK_INITIAL_VERSION = "1.0.0"
    SUPPORTED_FROM_VERSION = "5.5.0"
    SUPPORTED_FROM_VERSION_XSIAM = "8.3.0"

    DIR_LIST = [
        INTEGRATIONS_DIR,
        SCRIPTS_DIR,
        INCIDENT_FIELDS_DIR,
        INCIDENT_TYPES_DIR,
        INDICATOR_FIELDS_DIR,
        PLAYBOOKS_DIR,
        LAYOUTS_DIR,
        TEST_PLAYBOOKS_DIR,
        CLASSIFIERS_DIR,
        CONNECTIONS_DIR,
        DASHBOARDS_DIR,
        INDICATOR_TYPES_DIR,
        REPORTS_DIR,
        WIDGETS_DIR,
        DOC_FILES_DIR,
        GENERIC_MODULES_DIR,
        GENERIC_DEFINITIONS_DIR,
        GENERIC_FIELDS_DIR,
        GENERIC_TYPES_DIR,
        JOBS_DIR,
        WIZARDS_DIR,
    ]

    XSIAM_DIR = [
        CORRELATION_RULES_DIR,
        XSIAM_DASHBOARDS_DIR,
        XSIAM_REPORTS_DIR,
        MODELING_RULES_DIR,
        PARSING_RULES_DIR,
    ]

    def __init__(
        self,
        output: str,
        name: str = "",
        id: str = "",
        integration: bool = False,
        template: str = "",
        category: str = "",
        script: bool = False,
        pack: bool = False,
        author_image: str = "",
        demisto_mock: bool = False,
        common_server: bool = False,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ):
        self.output = output if output else ""
        self.id = id
        self.marketplace = marketplace
        self.is_integration = integration
        self.is_script = script
        self.is_pack = pack
        self.author_image = author_image
        self.demisto_mock = demisto_mock
        self.common_server = common_server
        self.category = category
        self.configuration = Configuration()

        # if no flag given automatically create a pack.
        if not integration and not script and not pack:
            self.is_pack = True

        self.template = self.get_selected_template(template)

        self.full_output_path = ""
        if name:
            while " " in name:
                name = str(
                    input(
                        "The directory and file name cannot have spaces in it, Enter a different name: "
                    )
                )

        self.dir_name = name

        self.is_pack_creation = not all([self.is_script, self.is_integration])

    def init(self):
        """Starts the init command process."""
        if self.is_integration:
            self.get_created_dir_name(created_object="integration")
            self.get_object_id(created_object="integration")
            return self.integration_init()

        elif self.is_script:
            self.get_created_dir_name(created_object="script")
            self.get_object_id(created_object="script")
            return self.script_init()

        elif self.is_pack:
            self.get_created_dir_name(created_object="pack")
            return self.pack_init()

    def get_selected_template(self, template: str = "") -> str:
        """Makes sure a valid template is selected

        Args:
            template (str): the given template name (empty string if not given)

        Returns:
            str. A valid template name. If no template was specified, returns the default template name.
        """
        if self.is_integration:
            while template and template not in self.INTEGRATION_TEMPLATE_OPTIONS:
                options_str = ", ".join(self.INTEGRATION_TEMPLATE_OPTIONS)
                template = str(
                    input(
                        f"Enter a valid template name, or press enter to choose the default template"
                        f" ({self.DEFAULT_INTEGRATION_TEMPLATE}).\nValid options: {options_str}\n"
                    )
                )
            return template or (
                self.HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION
                if self.marketplace == MarketplaceVersions.MarketplaceV2
                else self.DEFAULT_INTEGRATION_TEMPLATE
            )

        elif self.is_script:
            while template and template not in self.SCRIPT_TEMPLATE_OPTIONS:
                options_str = ", ".join(self.SCRIPT_TEMPLATE_OPTIONS)
                template = str(
                    input(
                        f"Enter a valid template name, or press enter to choose the default template"
                        f" ({self.DEFAULT_SCRIPT_TEMPLATE}).\nValid options: {options_str}\n"
                    )
                )
            return template if template else self.DEFAULT_SCRIPT_TEMPLATE

        # if reached here it is a pack init - will be used again if user decides to create an integration
        return template

    def process_files(self, file_list: Set[str], path_of_template) -> None:
        """Creates empty files according to a given list or from a template if exist.

        Args:
            file_list (List(str)): A list with path and names of the files.
        """
        for file in file_list:
            file_path = Path(self.full_output_path).joinpath(file)
            template_path = Path(path_of_template).joinpath(file)
            dir_path = file_path.parent

            # if the file path is not exist we create it from template.
            if not file_path.exists() or os.stat(file_path).st_size == 0:
                if template_path.exists():
                    self.write_to_file_from_template(template_path, file_path)
                else:
                    if not dir_path.exists():
                        dir_path.mkdir(exist_ok=True)
                    _, file_extension = os.path.splitext(file_path)
                    with open(file_path, "w") as f:
                        if file_extension == ".json":
                            f.write(json.dumps({}, indent=4))

    def get_created_dir_name(self, created_object: str):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        while not self.dir_name or len(self.dir_name) == 0:
            self.dir_name = str(
                input(f"Please input the name of the initialized {created_object}: ")
            )
            while " " in self.dir_name:
                self.dir_name = str(
                    input(
                        "The directory name cannot have spaces in it, Enter a different name: "
                    )
                )

    def get_object_id(self, created_object: str):
        if not self.id:
            if (
                self.is_pack_creation
            ):  # There was no option to enter the ID in this process.
                use_dir_name = str(
                    input(
                        f"Do you want to use the directory name as an "
                        f"ID for the {created_object}? Y/N "
                    )
                )
            else:
                use_dir_name = str(
                    input(
                        f"No ID given for the {created_object}'s yml file. "
                        f"Do you want to use the directory name? Y/N "
                    )
                )

            if use_dir_name and use_dir_name.lower() in ["y", "yes"]:
                self.id = self.dir_name
            else:
                while not self.id:
                    self.id = str(
                        input(f"Please enter the id name for the {created_object}: ")
                    )

    def create_initiator(
        self,
        output: str,
        template: str,
        is_script: bool,
        is_integration: bool,
        is_pack: bool,
    ):
        """Creates initiator object and initialize it.

        Args:
            output (str): The output path.
            template (str): The template.
            is_script (bool): Indicates whether the content is a script.
            is_integration (bool): Indicates whether the content is a integration.
            is_pack (bool): Indicates whether the content is a pack.
        """
        return Initiator(
            output=output,
            common_server=self.common_server,
            dir_name=self.dir_name,
            template=template,
            script=is_script,
            integration=is_integration,
            pack=is_pack,
            demisto_mock=self.demisto_mock,
            marketplace=self.marketplace,
            name=self.dir_name,
        )

    def create_initiators_and_init_modeling_parsing_rules(
        self, product: Optional[str], vendor: Optional[str]
    ) -> bool:
        """Creates initiators object for modeling and parsing rules init and initialize them.

        Args:
            product (str): The product from the user.
            vendor (str): The vendor from the user.
        """
        if not self.full_output_path and self.output:
            self.full_output_path = str(find_pack_folder(Path(self.output)))
        modeling_rules_initiator = self.create_initiator(
            os.path.join(self.full_output_path, MODELING_RULES_DIR),
            self.HELLO_WORLD_MODELING_RULES,
            False,
            False,
            False,
        )
        parsing_rules_initiator = self.create_initiator(
            os.path.join(self.full_output_path, PARSING_RULES_DIR),
            self.HELLO_WORLD_PARSING_RULES,
            False,
            False,
            False,
        )
        if not parsing_rules_initiator.modeling_parsing_rules_init(
            is_parsing_rules=True,
        ) or not modeling_rules_initiator.modeling_parsing_rules_init(
            is_modeling_rules=True, product=product, vendor=vendor
        ):
            return False
        return True

    def pack_init(self) -> bool:
        """Creates a pack directory tree.

        Returns:
            bool. Returns True if pack was created successfully and False otherwise
        """
        # if an output directory given create the pack there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # content-descriptor file indicates we are in "content" repository
        # thus we will create the pack under Packs directory
        elif Path("content-descriptor.json").is_file():
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if in an external repo check for the existence of Packs directory
        # if it does not exist create it
        elif tools.is_external_repository():
            if not os.path.isdir("Packs"):
                logger.info("Creating 'Packs' directory")
                os.mkdir("Packs")
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if non of the above conditions apply - create the pack in current directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False
        for directory in self.DIR_LIST:
            path = os.path.join(self.full_output_path, directory)
            os.mkdir(path=path)
        # create the relevant folders for XSIAM content pack.
        if self.marketplace == MarketplaceVersions.MarketplaceV2:
            for directory in self.XSIAM_DIR:
                path = os.path.join(self.full_output_path, directory)
                os.mkdir(path=path)

        self.create_pack_base_files()
        logger.info(
            f"[green]Successfully created the pack {self.dir_name} in: {self.full_output_path}[/green]"
        )

        metadata_path = os.path.join(self.full_output_path, "pack_metadata.json")
        with open(metadata_path, "a") as fp:
            user_response = str(
                input("\nWould you like to fill pack's metadata file? Y/N ")
            ).lower()
            fill_manually = user_response in ["y", "yes"]

            pack_metadata = Initiator.create_metadata(fill_manually)
            self.category = (
                pack_metadata["categories"][0]
                if pack_metadata["categories"]
                else "Utilities"
            )
            json.dump(pack_metadata, fp, indent=4)

            logger.info(
                f"[green]Created pack metadata at path : {metadata_path}[/green]"
            )

        create_integration = str(
            input("\nDo you want to create an integration in the pack? Y/N ")
        ).lower()
        if string_to_bool(create_integration):
            if not self.marketplace == MarketplaceVersions.MarketplaceV2:
                is_same_category = str(
                    input(
                        "\nDo you want to set the integration category as you defined in the pack "
                        "metadata? Y/N "
                    )
                ).lower()

                integration_category = (
                    self.category if string_to_bool(is_same_category) else ""
                )
            else:
                integration_category = ANALYTICS_AND_SIEM_CATEGORY
            integration_init = Initiator(
                output=os.path.join(self.full_output_path, "Integrations"),
                integration=True,
                common_server=self.common_server,
                demisto_mock=self.demisto_mock,
                template=self.template,
                category=integration_category,
                marketplace=self.marketplace,
            )
            return integration_init.init()

        return True

    def modeling_parsing_rules_init(
        self,
        product: Optional[str] = None,
        vendor: Optional[str] = None,
        is_parsing_rules: bool = False,
        is_modeling_rules: bool = False,
    ) -> bool:
        """Creates a parsing or modeling rules directory tree.

        Returns:
            bool. Returns True if the parsing rules was created successfully and False otherwise
        """
        dirname = get_dir_name_for_xsiam_item(
            is_modeling_rules=is_modeling_rules,
            is_parsing_rules=is_parsing_rules,
            name="",
        )

        xsiam_content_dir_name = get_dir_name_for_xsiam_item(
            is_parsing_rules, is_modeling_rules, name=self.dir_name
        )
        self.full_output_path = str(Path(self.output).joinpath(xsiam_content_dir_name))
        rules_template_files = self.get_template_files()
        if not self.get_remote_templates(
            rules_template_files,
            dir=dirname,
        ):
            local_template_dir = dirname
            local_template_path = Path(
                Path(__file__).parent,
                "templates",
                self.HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION,
                local_template_dir,
                self.template,
            )
            copy_tree(str(local_template_path), self.full_output_path)
            self.process_files(rules_template_files, local_template_path)
        if self.id != self.template:
            self.rename(
                current_suffix=self.template,
                is_parsing_rules=is_parsing_rules,
                is_modeling_rules=is_modeling_rules,
            )
            self.modeling_or_parsing_rules_yml_reformatting(
                current_suffix=self.dir_name,
                is_modeling_rules=is_modeling_rules,
                is_parsing_rules=is_parsing_rules,
                product=product,
                vendor=vendor,
            )

        return True

    def create_pack_base_files(self):
        """
        Create empty 'README.md', '.secrets-ignore', '.pack-ignore' and 'Author_image.png' files that are expected
        to be in the base directory of a pack
        """
        logger.info("Creating pack base files")
        fp = open(os.path.join(self.full_output_path, "README.md"), "a")
        fp.close()

        fp = open(os.path.join(self.full_output_path, ".secrets-ignore"), "a")
        fp.close()

        fp = open(os.path.join(self.full_output_path, ".pack-ignore"), "a")
        fp.close()

        # if an `Author_image.png` file was given - replace the default file with it
        author_image_path = os.path.join(self.full_output_path, "Author_image.png")
        if self.author_image:
            shutil.copyfile(self.author_image, author_image_path)
        else:
            fp = open(author_image_path, "a")
            fp.close()

    @staticmethod
    def create_metadata(fill_manually: bool, data: Dict = None) -> Dict:
        """Builds pack metadata JSON content.

        Args:
            fill_manually (bool): Whether to interact with the user to fill in metadata details or not.
            data (dict): Dictionary keys and value to insert into the pack metadata.

        Returns:
            Dict. Pack metadata JSON content.
        """
        pack_metadata = {
            "name": "## FILL MANDATORY FIELD ##",
            "description": "## FILL MANDATORY FIELD ##",
            "support": XSOAR_SUPPORT,
            "currentVersion": PACK_INITIAL_VERSION,
            "author": XSOAR_AUTHOR,
            "url": XSOAR_SUPPORT_URL,
            "email": "",
            "categories": [],
            "tags": [],
            "useCases": [],
            "keywords": [],
            "marketplaces": MARKETPLACES,
        }

        if data:
            pack_metadata.update(data)

        if not fill_manually:
            return pack_metadata  # return xsoar template

        pack_metadata["name"] = input("\nDisplay name of the pack: ")
        if not pack_metadata.get("name"):
            pack_metadata["name"] = "## FILL MANDATORY FIELD ##"

        pack_metadata["description"] = input("\nDescription of the pack: ")
        if not pack_metadata.get("description"):
            pack_metadata["description"] = "## FILL MANDATORY FIELD ##"

        pack_metadata["support"] = Initiator.get_valid_user_input(
            options_list=PACK_SUPPORT_OPTIONS,
            option_message="\nSupport type of the pack: \n",
        )
        pack_metadata["categories"] = [
            Initiator.get_valid_user_input(
                options_list=INTEGRATION_CATEGORIES,
                option_message="\nPack category options: \n",
            )
        ]

        marketplaces = input(
            "\nSupported marketplaces for this pack, comma separated values.\n"
            "Possible options are: xsoar, marketplacev2. default value is 'xsoar,marketplacev2'.\n"
        )
        mp_list = [m.strip() for m in marketplaces.split(",") if m]
        if mp_list:
            pack_metadata["marketplaces"] = mp_list

        if pack_metadata.get("support") == XSOAR_SUPPORT:
            pack_metadata["author"] = XSOAR_AUTHOR
            pack_metadata["url"] = XSOAR_SUPPORT_URL

            return pack_metadata

        pack_metadata["author"] = input("\nAuthor of the pack: ")

        if (
            pack_metadata.get("support") != "community"
        ):  # get support details from the user for non community packs
            support_url = input(
                "\nThe url of support, should be a valid support/info URL (optional): "
            )
            while support_url and "http" not in support_url:
                support_url = input("\nIncorrect input. Please enter full valid url: ")
            pack_metadata["url"] = support_url
            pack_metadata["email"] = input(
                "\nThe email in which users can reach out for support (optional): "
            )
        else:  # community pack url should refer to the marketplace live discussions
            pack_metadata["url"] = MARKETPLACE_LIVE_DISCUSSIONS

        dev_email = input(
            "\nThe email will be used to inform you for any changes made to your pack (optional): "
        )
        if dev_email:
            pack_metadata["devEmail"] = [e.strip() for e in dev_email.split(",") if e]

        tags = input("\nTags of the pack, comma separated values: ")
        tags_list = [t.strip() for t in tags.split(",") if t]
        pack_metadata["tags"] = tags_list

        github_users = input(
            "\nPack default reviewers, comma separated github username: "
        )
        github_users_list = [u.strip() for u in github_users.split(",") if u]
        pack_metadata["githubUser"] = github_users_list

        return pack_metadata

    @staticmethod
    def get_valid_user_input(options_list: List[str], option_message: str) -> str:
        """Gets user input from a list of options, by integer represents the choice.

        Args:
            options_list (List[str]): List of options for the user to choose from.
            option_message (str): The message to show the user along with the list of options.

        Returns:
            str. The chosen option.
        """
        for index, option in enumerate(options_list, start=1):
            option_message += f"[{index}] {option}\n"
        option_message += "\nEnter option: "

        user_input = input(option_message)

        while True:
            try:
                user_choice = int(user_input)
                if user_choice not in range(1, len(options_list) + 1):
                    user_input = input(
                        f"\nInvalid option {user_input}, please enter valid choice: "
                    )
                else:
                    return options_list[user_choice - 1]
            except ValueError:
                user_input = input(
                    "\nThe option must be number, please enter valid choice: "
                )

    def add_event_collector_suffix(self) -> None:
        """Adds the "EventCollector" suffix if it does not exist.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        if self.marketplace == MarketplaceVersions.MarketplaceV2:
            if not self.dir_name.lower().endswith(EVENT_COLLECTOR.lower()):
                self.dir_name = f"{self.dir_name}{EVENT_COLLECTOR}"
            if not self.id.lower().endswith(EVENT_COLLECTOR.lower()):
                self.id = f"{self.id}{EVENT_COLLECTOR}"

    def find_secrets(self):
        files_and_directories = glob.glob(
            f"{self.full_output_path}/**/*", recursive=True
        )

        sv = SecretsValidator(
            white_list_path="./Tests/secrets_white_list.json", ignore_entropy=True
        )
        # remove directories and irrelevant files
        files = [
            file
            for file in files_and_directories
            if Path(file).is_file() and sv.is_text_file(file)
        ]
        # The search_potential_secrets method returns a nested dict with values of type list. The values are the secrets
        # {'a': {'b': ['secret1', 'secret2'], 'e': ['secret1']}, 'g': ['secret3']}
        nested_dict_of_secrets = sv.search_potential_secrets(files)
        set_of_secrets: set = set()

        extract_values_from_nested_dict_to_a_set(nested_dict_of_secrets, set_of_secrets)

        return set_of_secrets

    def ignore_secrets(self, secrets):
        pack_dir = get_pack_name(self.full_output_path)
        try:
            with open(f"Packs/{pack_dir}/.secrets-ignore", "a") as f:
                for secret in secrets:
                    f.write(secret)
                    f.write("\n")
        except FileNotFoundError:
            logger.info(
                "[yellow]Could not find the .secrets-ignore file - make sure your path is correct[/yellow]"
            )

    def verify_output_path_for_xsiam_content(self) -> bool:
        """Verify that there is an output path from the user.
        Returns:
            bool. True if all the required inputs from the user are valid.
        """
        if self.marketplace != MarketplaceVersions.MarketplaceV2:
            return True
        if not self.output:
            logger.error(
                "[red]An output directory is required to utilize the --xsiam flag. Please attempt the operation again using the -o flag to specify the output directory.[/red]"
            )
            return False
        # Check if the output path matches either the Integrations directory or a subdirectory under Packs
        valid_output_path = re.search(INTEGRATIONS_DIR_REGEX, self.output) or re.search(
            PACKS_DIR_REGEX, self.output
        )
        if not valid_output_path:
            logger.error(
                "[red]The output directory is invalid - make sure the name looks like one of the following: Packs/**/Integrations [/red]"
            )
            return False
        return True

    def integration_init(self) -> bool:
        """Creates a new integration according to a template.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        # if we want to create xsiam content we will create an eventcollector integration

        if not self.verify_output_path_for_xsiam_content():
            return False
        product, vendor = self.get_product_and_vendor()
        if (
            self.marketplace == MarketplaceVersions.MarketplaceV2
            and not self.create_initiators_and_init_modeling_parsing_rules(
                product, vendor
            )
        ):
            return False
        self.add_event_collector_suffix()

        # if output directory given create the integration there
        if self.output:
            if (
                self.output
                and re.search(PACKS_DIR_REGEX, self.output)
                and self.marketplace == MarketplaceVersions.MarketplaceV2
            ):
                self.full_output_path = str(
                    find_pack_folder(Path(self.output))
                    / INTEGRATIONS_DIR
                    / self.dir_name
                )
            else:
                self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the integration under the Integrations directory of the pack
        elif os.path.isdir(INTEGRATIONS_DIR):
            self.full_output_path = os.path.join(INTEGRATIONS_DIR, self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False
        integration_template_files = self.get_template_files()
        if not self.get_remote_templates(
            integration_template_files, dir=INTEGRATIONS_DIR
        ):
            local_template_path = os.path.normpath(
                os.path.join(__file__, "..", "templates", self.template)
            )
            if self.marketplace == MarketplaceVersions.MarketplaceV2:
                self.process_files(integration_template_files, local_template_path)
            else:
                copy_tree(str(local_template_path), self.full_output_path)

        if self.id != self.template:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.template)
            self.yml_reformatting(current_suffix=self.template, integration=True)
            self.fix_test_file_import(name_to_change=self.template)
            self.replace_vendor_and_product_py_file(vendor=vendor, product=product)

        self.copy_common_server_python()
        self.copy_demistotmock()

        if (
            self.template != self.DEFAULT_INTEGRATION_TEMPLATE
        ):  # DEFAULT_INTEGRATION_TEMPLATE there are no secrets
            secrets = self.find_secrets()
            if secrets:
                new_line = "\n"
                logger.info(
                    f"\n[green]The following secrets were detected:\n"
                    f"{new_line.join(secret for secret in secrets)}[/green]"
                )

                ignore_secrets = input(
                    "\nWould you like ignore them automatically? Y/N "
                ).lower()
                if ignore_secrets in ["y", "yes"]:
                    self.ignore_secrets(secrets)

        logger.info(
            f"[green]Finished creating integration: {self.full_output_path}.[/green]"
        )

        return True

    def script_init(self) -> bool:
        """Creates a new script according to a template.

        Returns:
            bool. True if the script was created successfully, False otherwise.
        """
        # if output directory given create the script there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the script under the Scripts directory of the pack
        elif os.path.isdir(SCRIPTS_DIR):
            self.full_output_path = os.path.join("Scripts", self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        used_template = self.template
        script_template_files = self.get_template_files()
        if not self.get_remote_templates(script_template_files, dir=SCRIPTS_DIR):
            local_template_path = os.path.normpath(
                os.path.join(__file__, "..", "templates", self.template)
            )
            copy_tree(str(local_template_path), self.full_output_path)

        if self.id != self.template:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.change_template_name_script_py(
                current_suffix=self.template, current_template=used_template
            )
            self.rename(current_suffix=self.template)
            self.yml_reformatting(current_suffix=self.template)
            self.fix_test_file_import(name_to_change=self.template)

        self.copy_common_server_python()
        self.copy_demistotmock()

        secrets = self.find_secrets()
        if secrets:
            new_line = "\n"
            logger.info(
                f"\n[green]The following secrets were detected in the pack:\n"
                f"{new_line.join(secret for secret in secrets)}[/green]"
            )

            ignore_secrets = input(
                "\nWould you like ignore them automatically? Y/N "
            ).lower()
            if ignore_secrets in ["y", "yes"]:
                self.ignore_secrets(secrets)

        logger.info(f"[green]Finished creating script: {self.full_output_path}[/green]")

        return True

    def get_product_and_vendor(self) -> Tuple[Optional[str], Optional[str]]:
        """Gets product vendor from the user.

        Returns:
            Tuple. The product and vendor.
        """
        vendor = None
        product = None
        if self.marketplace == MarketplaceVersions.MarketplaceV2:
            while not vendor:
                vendor = str(input("Please enter vendor name: ").lower())
            while not product:
                product = str(input("Please enter product name: ").lower())
        return product, vendor

    def update_product_and_vendor(
        self, json_file_name: str, product: Optional[str], vendor: Optional[str]
    ) -> None:
        """Addes the product and the vendor to the schema under modeling rules folder.

        Args:
            json_file_name (str): The current name of the json file.
            product (str): The name of the product.
            vendor (str):  The name of the vendor.
        """
        schema_json_path = (
            Path(self.full_output_path)
            .joinpath(f"{json_file_name}_schema")
            .with_suffix(".json")
        )
        if schema_json_path.exists():
            schema_json = get_file(schema_json_path)
            hello_world_raw = schema_json["hello_world_raw"]
            dict_for_schema = {f"{vendor}_{product}_raw": hello_world_raw}
            with open(schema_json_path, "w") as f:
                json.dump(dict_for_schema, f, indent=4)

    def modeling_or_parsing_rules_yml_reformatting(
        self,
        current_suffix: str,
        product: Optional[str] = None,
        vendor: Optional[str] = None,
        is_modeling_rules: bool = False,
        is_parsing_rules: bool = False,
    ):
        """Formats the given yml to fit the newly created modeling/pursing rules.

        Args:
            current_suffix (str): The current suffix of the yml file.
            is_modeling_rules (bool): Indicates whether the file is modeling rules.
            is_parsing_rules (bool): Indicates whether the file is parsing rules.
        """
        yml_file_name = get_dir_name_for_xsiam_item(
            is_modeling_rules=is_modeling_rules,
            is_parsing_rules=is_parsing_rules,
            name=current_suffix,
        )
        yml_path = (
            Path(self.full_output_path).joinpath(yml_file_name).with_suffix(".yml")
        )
        self.update_product_and_vendor(yml_file_name, product, vendor)
        yml_dict = get_yaml(yml_path)
        id_from_yml: str = yml_dict["id"]
        name_from_yml: str = yml_dict["name"]

        yml_dict["id"] = id_from_yml.replace(self.HELLO_WORLD_PACK_NAME, self.dir_name)
        yml_dict["name"] = name_from_yml.replace(
            self.HELLO_WORLD_PACK_NAME, self.dir_name
        )

        content_item = "modeling rules" if is_modeling_rules else "parsing rules"
        if from_version := input(
            f"\nThe fromversion value that will be used for {content_item} (optional): "
        ):
            yml_dict["fromversion"] = from_version

        if not self.validate_version(
            yml_dict.get("fromversion") or DEFAULT_CONTENT_ITEM_FROM_VERSION,
            self.SUPPORTED_FROM_VERSION_XSIAM,
        ):
            yml_dict["fromversion"] = self.SUPPORTED_FROM_VERSION_XSIAM
            logger.info(
                "[yellow]The version is not provided or is lower than the supported version; the value will be set to the default version. [/yellow]"
            )
        with open(yml_path, "w") as f:
            yaml.dump(yml_dict, f)

    def replace_vendor_and_product_py_file(
        self, vendor: Optional[str], product: Optional[str]
    ) -> None:
        """Replace the product and the vendor in the py event collector file.
           Used when creating an event collector.

        Args:
            product (str): The product.
            vendor (str): The vendor.
        """
        python_file_path = (
            Path(self.full_output_path).joinpath(self.dir_name).with_suffix(".py")
        )
        if (
            self.marketplace == MarketplaceVersions.MarketplaceV2
            and python_file_path.exists()
        ):
            with open(python_file_path) as fp:
                file_contents = fp.read()

            file_contents = file_contents.replace(
                "VENDOR = 'hello'", f"VENDOR = '{vendor}'"
            )
            file_contents = file_contents.replace(
                "PRODUCT = 'world'", f"PRODUCT = '{product}'"
            )

            with open(python_file_path, "w") as fp:
                fp.write(file_contents)

    def validate_version(
        self, current_version: str, supported_from_version: str
    ) -> bool:
        """Return bool True if the given version is bigger then the supported version

        Args:
            current_version (str): The current version.
            supported_from_version (str): The supported from version.
        """
        return Version(current_version) >= Version(supported_from_version)

    def yml_reformatting(self, current_suffix: str, integration: bool = False):
        """Formats the given yml to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
            integration (bool): Indicates if integration yml is being reformatted.
        """
        yml_dict = get_yaml(
            os.path.join(self.full_output_path, f"{current_suffix}.yml")
        )
        yml_dict["commonfields"]["id"] = self.id
        yml_dict["name"] = self.id

        from_version = input(
            "\nThe fromversion value that will be used for the content yml (optional): "
        )
        if from_version:
            yml_dict["fromversion"] = from_version

        compared_version = (
            self.SUPPORTED_FROM_VERSION
            if self.marketplace != MarketplaceVersions.MarketplaceV2
            else self.SUPPORTED_FROM_VERSION_XSIAM
        )
        if not self.validate_version(
            yml_dict.get("fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION),
            compared_version,
        ):
            yml_dict["fromversion"] = compared_version
            logger.info(
                "[yellow]The selected version is lower than the supported version; the value will be set to the default version. [/yellow]"
            )

        if integration:
            yml_dict["display"] = self.id
            yml_dict["category"] = (
                self.category
                if self.category
                else (
                    ANALYTICS_AND_SIEM_CATEGORY
                    if self.marketplace == MarketplaceVersions.MarketplaceV2
                    else Initiator.get_valid_user_input(
                        options_list=INTEGRATION_CATEGORIES,
                        option_message="\nIntegration category options: \n",
                    )
                )
            )

        with open(
            os.path.join(self.full_output_path, f"{self.dir_name}.yml"), "w"
        ) as f:
            yaml.dump(yml_dict, f)

        Path(self.full_output_path, f"{current_suffix}.yml").unlink()

    def change_template_name_script_py(
        self, current_suffix: str, current_template: str
    ):
        """Change all script template name appearances with the real script name in the script python file.

        Args:
            current_suffix (str): The py file name
            current_template (str): The script template being used.
        """
        with open(
            os.path.join(self.full_output_path, f"{current_suffix}.py"), "r+"
        ) as f:
            py_file_data = f.read()
            py_file_data = py_file_data.replace(current_template, self.id)
            f.seek(0)
            f.write(py_file_data)
            f.truncate()

    def rename(
        self,
        current_suffix: str,
        is_modeling_rules: bool = False,
        is_parsing_rules: bool = False,
    ):
        """Renames the python, description, test and image file in the path to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        full_output_path = Path(self.full_output_path)
        current_file_path = full_output_path.joinpath(f"{current_suffix}")
        file_path = full_output_path.joinpath(f"{self.dir_name}")
        if current_file_path.with_suffix(".py").exists():
            current_file_path.with_suffix(".py").rename(file_path.with_suffix(".py"))

        if (
            full_output_path.joinpath(f"{current_suffix}_test")
            .with_suffix(".py")
            .exists()
        ):
            full_output_path.joinpath(f"{current_suffix}_test").with_suffix(
                ".py"
            ).rename(
                full_output_path.joinpath(f"{self.dir_name}_test").with_suffix(".py")
            )

        if self.is_integration:
            full_output_path.joinpath(f"{current_suffix}_image").with_suffix(
                ".png"
            ).rename(
                full_output_path.joinpath(f"{self.dir_name}_image").with_suffix(".png")
            )
            full_output_path.joinpath(f"{current_suffix}_description").with_suffix(
                ".md"
            ).rename(
                full_output_path.joinpath(f"{self.dir_name}_description").with_suffix(
                    ".md"
                )
            )

        if is_parsing_rules or is_modeling_rules:
            name = get_dir_name_for_xsiam_item(
                is_modeling_rules=is_modeling_rules,
                is_parsing_rules=is_parsing_rules,
                name=self.dir_name,
            )
            current_file_path = full_output_path.joinpath(f"{current_suffix}")
            file_path = full_output_path.joinpath(f"{name}")
            if current_file_path.with_suffix(".xif").exists():
                current_file_path.with_suffix(".xif").rename(
                    file_path.with_suffix(".xif")
                )

            if current_file_path.with_suffix(".yml").exists():
                current_file_path.with_suffix(".yml").rename(
                    file_path.with_suffix(".yml")
                )

            if (
                full_output_path.joinpath(f"{current_suffix}_schema")
                .with_suffix(".json")
                .exists()
            ):
                full_output_path.joinpath(f"{current_suffix}_schema").with_suffix(
                    ".json"
                ).rename(
                    full_output_path.joinpath(f"{name}_schema").with_suffix(".json")
                )

    def create_new_directory(
        self,
    ) -> bool:
        """Creates a new directory for the integration/script/pack.

        Returns:
            bool. True if directory was successfully created, False otherwise.
        """
        try:
            os.mkdir(self.full_output_path)

        except FileExistsError:
            to_delete = str(
                input(
                    f"The directory {self.full_output_path} "
                    f"already exists.\nDo you want to overwrite it? Y/N "
                )
            ).lower()
            while to_delete != "y" and to_delete != "n":
                to_delete = str(
                    input(
                        "Your response was invalid.\nDo you want to delete it? Y/N "
                    ).lower()
                )

            if to_delete in ["y", "yes"]:
                shutil.rmtree(path=self.full_output_path, ignore_errors=True)
                os.mkdir(self.full_output_path)

            else:
                logger.info(f"[red]Pack not created in {self.full_output_path}[/red]")
                return False

        return True

    def fix_test_file_import(self, name_to_change: str):
        """Fixes the import statement in the _test.py file in the newly created initegration/script

        Args:
            name_to_change (str): The name of the former integration/script to replace in the import.
        """
        with open(
            os.path.join(self.full_output_path, f"{self.dir_name}_test.py")
        ) as fp:
            file_contents = fp.read()

        file_contents = file_contents.replace(f".{name_to_change}", self.dir_name)

        with open(
            os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), "w"
        ) as fp:
            fp.write(file_contents)

    def write_to_file_from_template(self, template_path: Path, output_path: Path):
        """Fixes the import statement in the _test.py file in the newly created initegration/script

        Args:
            name_to_change (str): The name of the former integration/script to replace in the import.
        """
        shutil.copy(template_path, output_path)

    def copy_common_server_python(self):
        """copy commonserverpython from the base pack"""
        if self.common_server:
            try:
                common_server_path = get_common_server_path(self.configuration.env_dir)
                shutil.copy(common_server_path, self.full_output_path)
            except Exception as err:
                logger.debug(f"Could not copy CommonServerPython: {str(err)}")

    def copy_demistotmock(self):
        """copy demistomock from content"""
        if self.demisto_mock:
            try:
                shutil.copy(
                    f"{self.configuration.env_dir}/Tests/demistomock/demistomock.py",
                    self.full_output_path,
                )
            except Exception as err:
                logger.debug(f"Could not copy demistomock: {str(err)}")

    def get_template_files(self):
        """
        Gets the list of the integration/script file names to create according to the selected template.
        Returns:
            set. The names of integration/script files to create.
        """
        if self.is_integration:
            template_files = {
                filename.replace(self.TEMPLATE_INTEGRATION_NAME, self.template)
                for filename in self.TEMPLATE_INTEGRATION_FILES
            }

            if self.template == self.HELLO_WORLD_INTEGRATION:
                template_files = template_files.union(self.HELLO_WORLD_TEST_DATA_FILES)

            elif self.template == self.HELLO_WORLD_FEED_INTEGRATION:
                template_files = template_files.union(
                    self.HELLO_WORLD_FEED_TEST_DATA_FILES
                )

            elif self.template == self.HELLO_WORLD_SLIM_INTEGRATION:
                template_files = template_files.union(
                    self.HELLO_WORLD_SLIM_TEST_DATA_FILES
                )

            elif self.template == self.DEFAULT_INTEGRATION_TEMPLATE:
                template_files = template_files.union(
                    self.DEFAULT_INTEGRATION_TEST_DATA_FILES
                )
            elif self.template == self.HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION:
                template_files = template_files.union(
                    self.DEFAULT_EVENT_COLLECTOR_TEST_DATA_FILES
                )
        elif self.template == self.HELLO_WORLD_MODELING_RULES:
            template_files = set(self.TEMPLATE_MODELING_RULES_FILES)
        elif self.template == self.HELLO_WORLD_PARSING_RULES:
            template_files = set(self.TEMPLATE_PARSING_RULES_FILES)

        else:
            template_files = {
                filename.replace(self.TEMPLATE_SCRIPT_NAME, self.template)
                for filename in self.TEMPLATE_SCRIPT_FILES
            }

            if self.template == self.DEFAULT_SCRIPT_TEMPLATE:
                template_files = template_files.union(
                    self.DEFAULT_SCRIPT_TEST_DATA_FILES
                )
        return template_files

    def get_remote_templates(self, files_list, dir):
        """
        Downloading the object related template-files and saving them in the output path.
        Args:
            files_list: List of files to download.
            dir: The name of the relevant directory (e.g. "Integrations", "Scripts").
        Returns:
            bool. True if the files were downloaded and saved successfully, False otherwise.
        """
        # create test_data dir
        if self.template in [self.HELLO_WORLD_INTEGRATION] + self.DEFAULT_TEMPLATES + [
            self.HELLO_WORLD_FEED_INTEGRATION,
            self.HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION,
        ]:
            os.mkdir(os.path.join(self.full_output_path, self.TEST_DATA_DIR))

        if self.template in self.DEFAULT_TEMPLATES:
            pack_name = self.DEFAULT_TEMPLATE_PACK_NAME

        elif self.template in self.HELLO_WORLD_BASE_TEMPLATES + [
            self.HELLO_WORLD_FEED_INTEGRATION
        ]:
            pack_name = self.HELLO_WORLD_PACK_NAME
        elif self.template in [
            self.HELLO_WORLD_PARSING_RULES,
            self.HELLO_WORLD_MODELING_RULES,
            self.HELLO_WORLD_EVENT_COLLECTOR_INTEGRATION,
        ]:
            pack_name = self.HELLO_WORLD_PACK_NAME
        else:
            pack_name = self.template

        path = os.path.join("Packs", pack_name, dir, self.template)

        for file in files_list:
            try:
                filename = file
                if (
                    "README.md" in file
                    and self.template not in self.HELLO_WORLD_BASE_TEMPLATES
                ):
                    # This is for the cases when the actual readme file name in content repo
                    # is `README_example.md` - which happens when we do not want the readme
                    # files to appear in https://xsoar.pan.dev/docs/reference/index.
                    filename = file.replace("README.md", "README_example.md")
                file_content = tools.get_remote_file(
                    os.path.join(path, filename),
                    return_content=True,
                    # Templates available only in the official repo
                    git_content_config=GitContentConfig(
                        repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                    ),
                )
                with open(os.path.join(self.full_output_path, file), "wb") as f:
                    f.write(file_content)
            except Exception:
                logger.info(
                    f"[yellow]Could not fetch remote template - {path}. Using local templates instead.[/yellow]"
                )
                return False

        return True


def get_suffix_xsiam_content(
    name: str,
    is_parsing_rules: bool = False,
    is_modeling_rules: bool = False,
) -> str:
    """Gets the correct suffix to the xsiam content item

    Args:
        is_parsing_rules (bool): indicating whether the content type is parsing rule.
        is_modeling_rules (bool): indicating whether the content type is modeling rule.
        name (str): a name to attached to the suffix.
    """
    if is_parsing_rules:
        return f"{name}{PARSING_RULE_ID_SUFFIX}"
    return f"{name}{MODELING_RULE_ID_SUFFIX}" if is_modeling_rules else ""


def get_dir_name_for_xsiam_item(
    is_parsing_rules: bool = False, is_modeling_rules: bool = False, name: str = ""
) -> str:
    """Gets the correct directory name to the xsiam content item

    Args:
        is_parsing_rules (bool): indicating whether the content type is parsing rule.
        is_modeling_rules (bool): indicating whether the content type is modeling rule.
    """

    return (
        f"{name}{PARSING_RULES_DIR}"
        if is_parsing_rules
        else f"{name}{MODELING_RULES_DIR}"
    )
