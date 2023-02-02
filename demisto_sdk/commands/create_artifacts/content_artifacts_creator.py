import logging
import os
import re
import sys
import time
from concurrent.futures import as_completed
from contextlib import contextmanager
from shutil import make_archive, rmtree
from typing import Callable, Dict, List, Optional, Union

from packaging.version import parse
from pebble import ProcessFuture, ProcessPool
from wcmatch.pathlib import BRACE, EXTMATCH, NEGATE, NODIR, SPLIT, Path

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    CLASSIFIERS_DIR,
    CONTENT_ITEMS_DISPLAY_FOLDERS,
    CORRELATION_RULES_DIR,
    DASHBOARDS_DIR,
    DOCUMENTATION_DIR,
    GENERIC_DEFINITIONS_DIR,
    GENERIC_FIELDS_DIR,
    GENERIC_MODULES_DIR,
    GENERIC_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATIONS_DIR,
    JOBS_DIR,
    LAYOUT_RULES_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    MODELING_RULES_DIR,
    PACKS_DIR,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    PRE_PROCESS_RULES_DIR,
    RELEASE_NOTES_DIR,
    REPORTS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    TOOLS_DIR,
    TRIGGER_DIR,
    WIDGETS_DIR,
    WIZARDS_DIR,
    XDRC_TEMPLATE_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
    ContentItems,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content import (
    Content,
    ContentError,
    ContentFactoryError,
    Pack,
)
from demisto_sdk.commands.common.content.objects.abstract_objects.text_object import (
    TextObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects import (
    JSONContentObject,
    Script,
    YAMLContentObject,
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.tools import arg_to_list, open_id_set_file

from .artifacts_report import ArtifactsReport, ObjectReport

####################
# Global variables #
####################

FIRST_MARKETPLACE_VERSION = parse("6.0.0")
IGNORED_PACKS = ["ApiModules"]
IGNORED_TEST_PLAYBOOKS_DIR = "Deprecated"

ContentObject = Union[
    YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject, TextObject
]
logger = logging.getLogger("demisto-sdk")
EX_SUCCESS = 0
EX_FAIL = 1

XSOAR_MARKETPLACE_ITEMS_TO_DUMP = [
    FileType.CLASSIFIER,
    FileType.CONNECTION,
    FileType.INCIDENT_FIELD,
    FileType.INCIDENT_TYPE,
    FileType.INDICATOR_FIELD,
    FileType.INDICATOR_TYPE,
    FileType.INTEGRATION,
    FileType.JOB,
    FileType.LAYOUT,
    FileType.LISTS,
    FileType.PLAYBOOK,
    FileType.SCRIPT,
    FileType.TEST_PLAYBOOK,
    FileType.RELEASE_NOTES,
    FileType.RELEASE_NOTES_CONFIG,
    FileType.WIZARD,
    FileType.DASHBOARD,
    FileType.GENERIC_DEFINITION,
    FileType.GENERIC_MODULE,
    FileType.GENERIC_TYPE,
    FileType.GENERIC_FIELD,
    FileType.PRE_PROCESS_RULES,
    FileType.REPORT,
    FileType.WIDGET,
    FileType.TOOL,
    FileType.PACK_METADATA,
    FileType.METADATA,
    FileType.README,
    FileType.AUTHOR_IMAGE,
]
XSIAM_MARKETPLACE_ITEMS_TO_DUMP = [
    FileType.CLASSIFIER,
    FileType.CONNECTION,
    FileType.INCIDENT_FIELD,
    FileType.INCIDENT_TYPE,
    FileType.INDICATOR_FIELD,
    FileType.INDICATOR_TYPE,
    FileType.INTEGRATION,
    FileType.JOB,
    FileType.LAYOUT,
    FileType.LISTS,
    FileType.PLAYBOOK,
    FileType.SCRIPT,
    FileType.TEST_PLAYBOOK,
    FileType.RELEASE_NOTES,
    FileType.RELEASE_NOTES_CONFIG,
    FileType.WIZARD,
    FileType.PARSING_RULE,
    FileType.MODELING_RULE,
    FileType.CORRELATION_RULE,
    FileType.XSIAM_DASHBOARD,
    FileType.XSIAM_REPORT,
    FileType.TRIGGER,
    FileType.XDRC_TEMPLATE,
    FileType.TOOL,
    FileType.PACK_METADATA,
    FileType.METADATA,
    FileType.README,
    FileType.AUTHOR_IMAGE,
    FileType.LAYOUT_RULE,
]
XPANSE_MARKETPLACE_ITEMS_TO_DUMP = [
    FileType.INCIDENT_FIELD,
    FileType.INCIDENT_TYPE,
    FileType.INTEGRATION,
    FileType.PLAYBOOK,
    FileType.SCRIPT,
    FileType.RELEASE_NOTES,
    FileType.RELEASE_NOTES_CONFIG,
    FileType.PACK_METADATA,
    FileType.METADATA,
    FileType.README,
    FileType.AUTHOR_IMAGE,
]

MARKETPLACE_TO_ITEMS_MAPPING = {
    MarketplaceVersions.XSOAR.value: XSOAR_MARKETPLACE_ITEMS_TO_DUMP,
    MarketplaceVersions.MarketplaceV2.value: XSIAM_MARKETPLACE_ITEMS_TO_DUMP,
    MarketplaceVersions.XPANSE.value: XPANSE_MARKETPLACE_ITEMS_TO_DUMP,
}
##############
# Main logic #
##############


class ArtifactsManager:
    def __init__(
        self,
        artifacts_path: str,
        zip: bool,
        packs: bool,
        content_version: str,
        suffix: str,
        cpus: int,
        marketplace: str = MarketplaceVersions.XSOAR.value,
        id_set_path: str = "",
        pack_names: str = "all",
        signature_key: str = "",
        sign_directory: Path = None,
        remove_test_playbooks: bool = True,
        filter_by_id_set: bool = False,
        alternate_fields: bool = False,
    ):
        """Content artifacts configuration

        Args:
            artifacts_path: existing destination directory for creating artifacts.
            zip: True for zip all content artifacts to 3 different zip files in same structure else False.
            packs: create only content_packs artifacts if True.
            content_version: release content version.
            suffix: suffix to add all file we creates.
            cpus: available cpus in the computer.
            marketplace: The marketplace the artifacts are created for. deafults is xsoar marketplace.
            id_set_path: the full path of id_set.json.
            pack_names: Packs to create artifacts for.
            signature_key: Base64 encoded signature key used for signing packs.
            sign_directory: Path to the signDirectory executable file.
            remove_test_playbooks: Should remove test playbooks from content packs or not.
        """
        # options arguments
        self.artifacts_path = Path(artifacts_path)
        self.zip_artifacts = zip
        self.only_content_packs = packs
        self.content_version = content_version
        self.suffix = suffix
        self.cpus = cpus
        self.id_set_path = id_set_path
        self.id_set: dict = {}
        self.signature_key = signature_key
        self.signDirectory = sign_directory
        self.remove_test_playbooks = remove_test_playbooks
        self.marketplace = marketplace.lower()
        self.filter_by_id_set = filter_by_id_set
        self.pack_names = arg_to_list(pack_names)
        self.packs_section_from_id_set: dict = {}
        self.alternate_fields = alternate_fields
        # run related arguments
        self.content_new_path = self.artifacts_path / "content_new"
        self.content_test_path = self.artifacts_path / "content_test"
        self.content_packs_path = self.artifacts_path / "content_packs"
        self.content_all_path = self.artifacts_path / "all_content"
        self.content_uploadable_zips_path = self.artifacts_path / "uploadable_packs"

        if self.filter_by_id_set or self.alternate_fields:
            self.id_set = open_id_set_file(id_set_path)

        # inits
        self.content = Content.from_cwd()
        self.execution_start = time.time()

        self.packs = self.content.packs
        self.exit_code = EX_SUCCESS

        if self.filter_by_id_set:
            self.packs_section_from_id_set = self.id_set.get("Packs", {})
            if self.pack_names == ["all"]:
                self.pack_names = list(self.packs_section_from_id_set.keys())
            else:
                self.pack_names = list(
                    set(self.packs_section_from_id_set.keys()).intersection(
                        set(self.pack_names)
                    )
                )

    def create_content_artifacts(self) -> int:
        with ArtifactsDirsHandler(self), ProcessPoolHandler(self) as pool:
            futures: List[ProcessFuture] = []
            # content/Packs
            futures.extend(dump_packs(self, pool))
            # content/TestPlaybooks
            if not self.remove_test_playbooks:
                futures.append(pool.schedule(dump_tests_conditionally, args=(self,)))
            # content/content-descriptor.json
            futures.append(pool.schedule(dump_content_descriptor, args=(self,)))
            # content/Documentation/doc-*.json
            futures.append(pool.schedule(dump_content_documentations, args=(self,)))
            # Wait for all futures to be finished
            wait_futures_complete(futures, self)
            # Add suffix
            suffix_handler(self)

        if os.path.exists("keyfile"):
            os.remove("keyfile")
        logger.info(f"\nExecution time: {time.time() - self.execution_start} seconds")

        return self.exit_code

    def get_relative_pack_path(self, content_object: ContentObject):
        """

        Args:
            content_object: the object to get the relative path for

        Returns:
            the path of the given object relative from the pack directory, for example HelloWorld/Scripts/some_script

        """
        return content_object.path.relative_to(self.content.path / PACKS_DIR)

    def get_base_path(self) -> Path:
        """

        Returns:
            the path that all artifacts are relative to
        """
        return self.content.path

    def get_dir_to_delete(self):
        """

        Returns:
            list of directories to delete after artifacts was created
        """
        return [
            self.content_test_path,
            self.content_new_path,
            self.content_packs_path,
            self.content_all_path,
        ]


class ContentItemsHandler:
    def __init__(self, id_set=None, alternate_fields=False):
        self.server_min_version = parse("1.0.0")
        self.content_items: Dict[ContentItems, List] = {
            ContentItems.SCRIPTS: [],
            ContentItems.PLAYBOOKS: [],
            ContentItems.INTEGRATIONS: [],
            ContentItems.INCIDENT_FIELDS: [],
            ContentItems.INCIDENT_TYPES: [],
            ContentItems.DASHBOARDS: [],
            ContentItems.INDICATOR_FIELDS: [],
            ContentItems.REPORTS: [],
            ContentItems.INDICATOR_TYPES: [],
            ContentItems.LAYOUTS: [],
            ContentItems.PRE_PROCESS_RULES: [],
            ContentItems.JOB: [],
            ContentItems.CLASSIFIERS: [],
            ContentItems.WIDGETS: [],
            ContentItems.GENERIC_FIELDS: [],
            ContentItems.GENERIC_TYPES: [],
            ContentItems.GENERIC_MODULES: [],
            ContentItems.GENERIC_DEFINITIONS: [],
            ContentItems.LISTS: [],
            ContentItems.PARSING_RULES: [],
            ContentItems.MODELING_RULES: [],
            ContentItems.CORRELATION_RULES: [],
            ContentItems.XSIAM_DASHBOARDS: [],
            ContentItems.XSIAM_REPORTS: [],
            ContentItems.TRIGGERS: [],
            ContentItems.WIZARDS: [],
            ContentItems.XDRC_TEMPLATE: [],
            ContentItems.LAYOUT_RULES: [],
        }
        self.content_folder_name_to_func: Dict[str, Callable] = {
            SCRIPTS_DIR: self.add_script_as_content_item,
            PLAYBOOKS_DIR: self.add_playbook_as_content_item,
            INTEGRATIONS_DIR: self.add_integration_as_content_item,
            INCIDENT_FIELDS_DIR: self.add_incident_field_as_content_item,
            INCIDENT_TYPES_DIR: self.add_incident_type_as_content_item,
            DASHBOARDS_DIR: self.add_dashboard_as_content_item,
            INDICATOR_FIELDS_DIR: self.add_indicator_field_as_content_item,
            INDICATOR_TYPES_DIR: self.add_indicator_type_as_content_item,
            REPORTS_DIR: self.add_report_as_content_item,
            LAYOUTS_DIR: self.add_layout_as_content_item,
            PRE_PROCESS_RULES_DIR: self.add_pre_process_rules_as_content_item,
            LISTS_DIR: self.add_lists_as_content_item,
            JOBS_DIR: self.add_jobs_as_content_item,
            CLASSIFIERS_DIR: self.add_classifier_as_content_item,
            WIDGETS_DIR: self.add_widget_as_content_item,
            GENERIC_TYPES_DIR: self.add_generic_type_as_content_item,
            GENERIC_FIELDS_DIR: self.add_generic_field_as_content_item,
            GENERIC_MODULES_DIR: self.add_generic_module_as_content_item,
            GENERIC_DEFINITIONS_DIR: self.add_generic_definition_as_content_item,
            PARSING_RULES_DIR: self.add_parsing_rule_as_content_item,
            MODELING_RULES_DIR: self.add_modeling_rule_as_content_item,
            CORRELATION_RULES_DIR: self.add_correlation_rule_as_content_item,
            XSIAM_DASHBOARDS_DIR: self.add_xsiam_dashboard_as_content_item,
            XSIAM_REPORTS_DIR: self.add_xsiam_report_as_content_item,
            TRIGGER_DIR: self.add_trigger_as_content_item,
            WIZARDS_DIR: self.add_wizards_as_content_item,
            XDRC_TEMPLATE_DIR: self.add_xdrc_template_as_content_item,
            LAYOUT_RULES_DIR: self.add_layout_rule_as_content_item,
        }
        self.id_set = id_set
        self.alternate_fields = alternate_fields

    def handle_content_item(self, content_object: ContentObject):
        """Verifies the validity of the content object and parses it to the correct entities list.

        Args:
            content_object (ContentObject): The object to add to entities list.

        """
        content_object_directory = content_object.path.parts[-3]
        if content_object_directory not in self.content_folder_name_to_func.keys():
            # In the case where the content object is nested directly in the entities directory (Playbooks for example).
            content_object_directory = content_object.path.parts[-2]

        if content_object.to_version < FIRST_MARKETPLACE_VERSION:
            return

        # skip content items that are not displayed in contentItems
        if content_object_directory not in CONTENT_ITEMS_DISPLAY_FOLDERS:
            return

        self.server_min_version = max(
            self.server_min_version, content_object.from_version
        )

        self.content_folder_name_to_func[content_object_directory](content_object)

    def add_script_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.SCRIPTS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("comment", ""),
                "tags": content_object.get("tags", []),
            }
        )

    def add_playbook_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.PLAYBOOKS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_integration_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.INTEGRATIONS].append(
            {
                "name": content_object.get("display", ""),
                "description": content_object.get("description", ""),
                "category": content_object.get("category", ""),
                "commands": [
                    {
                        "name": command.get("name", ""),
                        "description": command.get("description", ""),
                    }
                    for command in content_object.script.get("commands", [])
                ],
            }
        )

    def add_incident_field_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.INCIDENT_FIELDS].append(
            {
                "name": content_object.get("name", ""),
                "type": content_object.get("type", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_incident_type_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.INCIDENT_TYPES].append(
            {
                "name": content_object.get("name", ""),
                "playbook": content_object.get("playbookId", ""),
                "closureScript": content_object.get("closureScript", ""),
                "hours": int(content_object.get("hours", 0)),
                "days": int(content_object.get("days", 0)),
                "weeks": int(content_object.get("weeks", 0)),
            }
        )

    def add_dashboard_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.DASHBOARDS].append(
            {"name": content_object.get("name", "")}
        )

    def add_indicator_field_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.INDICATOR_FIELDS].append(
            {
                "name": content_object.get("name", ""),
                "type": content_object.get("type", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_indicator_type_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.INDICATOR_TYPES].append(
            {
                "details": content_object.get("details", ""),
                "reputationScriptName": content_object.get("reputationScriptName", ""),
                "enhancementScriptNames": content_object.get(
                    "enhancementScriptNames", []
                ),
            }
        )

    def add_report_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.REPORTS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_layout_as_content_item(self, content_object: ContentObject):
        if content_object.get("description") is not None:
            self.content_items[ContentItems.LAYOUTS].append(
                {
                    "name": content_object.get("name", ""),
                    "description": content_object.get("description"),
                }
            )
        else:
            self.content_items[ContentItems.LAYOUTS].append(
                {"name": content_object.get("name", "")}
            )

    def add_pre_process_rules_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.PRE_PROCESS_RULES].append(
            {
                "name": content_object.get("name") or content_object.get("id", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_jobs_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.JOB].append(
            {
                "name": content_object.get("name") or content_object.get("id", ""),
                "details": content_object.get("details", ""),
            }
        )

    def add_lists_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.LISTS].append(
            {"name": content_object.get("name") or content_object.get("id", "")}
        )

    def add_classifier_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.CLASSIFIERS].append(
            {
                "name": content_object.get("name") or content_object.get("id", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_widget_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.WIDGETS].append(
            {
                "name": content_object.get("name", ""),
                "dataType": content_object.get("dataType", ""),
                "widgetType": content_object.get("widgetType", ""),
            }
        )

    def add_generic_field_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.GENERIC_FIELDS].append(
            {
                "name": content_object.get("name", ""),
                "type": content_object.get("type", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_generic_type_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.GENERIC_TYPES].append(
            {
                "name": content_object.get("name", ""),
                "details": content_object.get("details", ""),
            }
        )

    def add_generic_definition_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.GENERIC_DEFINITIONS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_generic_module_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.GENERIC_MODULES].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_parsing_rule_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.PARSING_RULES].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_modeling_rule_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.MODELING_RULES].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_correlation_rule_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.CORRELATION_RULES].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_xsiam_dashboard_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.XSIAM_DASHBOARDS].append(
            {
                "name": content_object["dashboards_data"][0].get("name", ""),
                "description": content_object["dashboards_data"][0].get(
                    "description", ""
                ),
            }
        )

    def add_xsiam_report_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.XSIAM_REPORTS].append(
            {
                "name": content_object["templates_data"][0].get("report_name", ""),
                "description": content_object["templates_data"][0].get(
                    "report_description", ""
                ),
            }
        )

    def add_trigger_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.TRIGGERS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_wizards_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.WIZARDS].append(
            {
                "name": content_object.get("name", ""),
                "description": content_object.get("description", ""),
            }
        )

    def add_xdrc_template_as_content_item(self, content_object: ContentObject):
        self.content_items[ContentItems.XDRC_TEMPLATE].append(
            {
                "name": content_object.get("name", ""),
                "os_type": content_object.get("os_type", ""),
                "profile_type": content_object.get("profile_type", ""),
            }
        )

    def add_layout_rule_as_content_item(self, content_object: ContentObject):
        if content_object.get("description") is not None:
            self.content_items[ContentItems.LAYOUT_RULES].append(
                {
                    "name": content_object.get("rule_name", ""),
                    "description": content_object.get("description"),
                }
            )
        else:
            self.content_items[ContentItems.LAYOUT_RULES].append(
                {"name": content_object.get("rule_name", "")}
            )


@contextmanager
def ProcessPoolHandler(artifact_manager: ArtifactsManager) -> ProcessPool:
    """Process pool Handler which terminate all processes in case of Exception.

    Args:
        artifact_manager: Artifacts manager object.

    Yields:
        ProcessPool: Pebble process pool.
    """
    global logger
    with ProcessPool(max_workers=artifact_manager.cpus, initializer=child_mute) as pool:
        try:
            yield pool
        except KeyboardInterrupt:
            logger.info(
                "\nCTRL+C Pressed!\nGracefully release all resources due to keyboard interrupt..."
            )
            pool.stop()
            pool.join()
            raise
        except Exception as e:
            logger.exception(e)
            logger.error("Gracefully release all resources due to Error...")
            pool.stop()
            pool.join()
            raise
        else:
            pool.close()
            pool.join()
        finally:
            if os.path.exists("keyfile"):
                os.remove("keyfile")


def wait_futures_complete(
    futures: List[ProcessFuture], artifact_manager: ArtifactsManager
):
    """Wait for all futures to complete, Raise exception if occured.

    Args:
        artifact_manager: Artifacts manager object.
        futures: futures to wait for.

    Raises:
        Exception: Raise caught exception for further cleanups.
    """
    global logger
    for future in as_completed(futures):
        try:
            result = future.result()
            if isinstance(result, ArtifactsReport):
                logger.info(result.to_str(artifact_manager.get_base_path()))
        except (ContentError, DuplicateFiles, ContentFactoryError) as e:
            logger.error(e.msg)
            raise
        except Exception as e:
            logger.exception(e)
            raise


#####################################################
# Files include rules functions (Version, Type etc) #
#####################################################


def is_in_content_packs(content_object: ContentObject) -> bool:
    """Rules content_packs:
        1. to_version >= First marketplace version.

    Args:
        content_object: Content object as specified in global variable - ContentObject.

    Returns:
        bool: True if object should be included in content_packs artifacts else False.
    """
    return content_object.to_version >= FIRST_MARKETPLACE_VERSION


def is_in_content_test(
    artifact_manager: ArtifactsManager, content_object: ContentObject
) -> bool:
    """Rules content_test:
        1. flag of only packs is off.
        2. Object located in TestPlaybooks directory (*/TestPlaybooks/*).
        3. from_version < First marketplace version.
        4. Path of object is not including global variable - IGNORED_TEST_PLAYBOOKS_DIR

    Args:
        artifact_manager: Artifacts manager object.
        content_object: Content object as specified in global variable - ContentObject.

    Returns:
        bool: True if object should be included in content_test artifacts else False.
    """
    return (
        not artifact_manager.only_content_packs
        and TEST_PLAYBOOKS_DIR in content_object.path.parts
        and content_object.from_version < FIRST_MARKETPLACE_VERSION
        and IGNORED_TEST_PLAYBOOKS_DIR not in content_object.path.parts
    )


def is_in_content_new(
    artifact_manager: ArtifactsManager, content_object: ContentObject
) -> bool:
    """Rules content_new:
        1. flag of only packs is off.
        2. Object not located in TestPlaybooks directory (*/TestPlaybooks/*).
        3. from_version < First marketplace version

    Args:
        artifact_manager: Artifacts manager object.
        content_object: Content object as specified in global variable - ContentObject.

    Returns:
        bool: True if object should be included in content_new artifacts else False.
    """
    return (
        not artifact_manager.only_content_packs
        and TEST_PLAYBOOKS_DIR not in content_object.path.parts
        and content_object.from_version < FIRST_MARKETPLACE_VERSION
    )


def is_in_content_all(
    artifact_manager: ArtifactsManager, content_object: ContentObject
) -> bool:
    """Rules content_all:
        1. If in content_new or content_test.

    Args:
        artifact_manager: Artifacts manager object.
        content_object: Content object as specified in global variable - ContentObject.

    Returns:
        bool: True if object should be included in content_all artifacts else False.
    """
    return is_in_content_new(artifact_manager, content_object) or is_in_content_test(
        artifact_manager, content_object
    )


############################
# Documentations functions #
############################


def dump_content_documentations(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """Dumping Documentation/doc-*.json into:
            1. content_new
            2. content_all

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.
    """
    report = ArtifactsReport("Documentations:")
    for documentation in artifact_manager.content.documentations:
        object_report = ObjectReport(documentation, content_packs=True)
        created_files = documentation.dump(
            artifact_manager.content_packs_path / BASE_PACK / DOCUMENTATION_DIR
        )
        if not artifact_manager.only_content_packs:
            object_report.set_content_new()
            object_report.set_content_all()
            for dest in [
                artifact_manager.content_new_path,
                artifact_manager.content_all_path,
            ]:
                created_files = dump_link_files(
                    artifact_manager, documentation, dest, created_files
                )
        report.append(object_report)

    return report


########################
# Descriptor functions #
########################


def dump_content_descriptor(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """Dumping content/content_descriptor.json into:
            1. content_test
            2. content_new
            3. content_all

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.

    Notes:
        1. content_descriptor.json created during build run time.
    """
    report = ArtifactsReport("Content descriptor:")
    if (
        not artifact_manager.only_content_packs
        and artifact_manager.content.content_descriptor
    ):
        descriptor = artifact_manager.content.content_descriptor
        object_report = ObjectReport(
            descriptor, content_test=True, content_new=True, content_all=True
        )
        created_files: List[Path] = []
        for dest in [
            artifact_manager.content_test_path,
            artifact_manager.content_new_path,
            artifact_manager.content_all_path,
        ]:
            created_files = dump_link_files(
                artifact_manager, descriptor, dest, created_files
            )
        report.append(object_report)

    return report


##################################
# Content Testplaybook functions #
##################################


def dump_tests_conditionally(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """Dump test scripts/playbooks conditionally into:
            1. content_test

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.

    """
    report = ArtifactsReport("TestPlaybooks:")
    for test in artifact_manager.content.test_playbooks:
        object_report = ObjectReport(test)
        if is_in_content_test(artifact_manager, test):
            object_report.set_content_test()
            test_created_files = dump_link_files(
                artifact_manager, test, artifact_manager.content_test_path
            )
            dump_link_files(
                artifact_manager,
                test,
                artifact_manager.content_all_path,
                test_created_files,
            )
        report += object_report

    return report


###########################
# Content packs functions #
###########################


def dump_packs(
    artifact_manager: ArtifactsManager, pool: ProcessPool
) -> List[ProcessFuture]:
    """Create futures which dumps conditionally content/Packs.

    Args:
        artifact_manager: Artifacts manager object.
        pool: Process pool to schedule new processes.

    Returns:
        List[ProcessFuture]: List of pebble futures to wait for.
    """
    futures = []
    if "all" in artifact_manager.pack_names:
        for pack_name, pack in artifact_manager.packs.items():
            if pack_name not in IGNORED_PACKS:
                futures.append(pool.schedule(dump_pack, args=(artifact_manager, pack)))

    else:
        for pack_name in artifact_manager.pack_names:
            if pack_name not in IGNORED_PACKS and pack_name in artifact_manager.packs:
                futures.append(
                    pool.schedule(
                        dump_pack,
                        args=(artifact_manager, artifact_manager.packs[pack_name]),
                    )
                )

    return futures


def handle_incident_field(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for incident_field in pack.incident_fields:
        content_items_handler.handle_content_item(incident_field)
        pack_report += dump_pack_conditionally(artifact_manager, incident_field)


def handle_integration(
    content_items_handler, pack, pack_report, artifact_manager, is_feed_pack, **kwargs
):
    for integration in pack.integrations:
        content_items_handler.handle_content_item(integration)
        is_feed_pack = is_feed_pack or integration.is_feed
        pack_report += dump_pack_conditionally(artifact_manager, integration)


def handle_playbook(
    content_items_handler, pack, pack_report, artifact_manager, is_feed_pack, **kwargs
):
    for playbook in pack.playbooks:
        content_items_handler.handle_content_item(playbook)
        is_feed_pack = is_feed_pack or playbook.get("name", "").startswith("TIM")
        pack_report += dump_pack_conditionally(artifact_manager, playbook)


def handle_script(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for script in pack.scripts:
        content_items_handler.handle_content_item(script)
        pack_report += dump_pack_conditionally(artifact_manager, script)


def handle_release_notes(pack, pack_report, artifact_manager, **kwargs):
    for release_note in pack.release_notes:
        pack_report += ObjectReport(release_note, content_packs=True)
        release_note.dump(
            artifact_manager.content_packs_path / pack.id / RELEASE_NOTES_DIR
        )


def handle_release_note_config(pack, pack_report, artifact_manager, **kwargs):
    for release_note_config in pack.release_notes_config:
        pack_report += ObjectReport(release_note_config, content_packs=True)
        release_note_config.dump(
            artifact_manager.content_packs_path / pack.id / RELEASE_NOTES_DIR
        )


def handle_classifier(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for classifier in pack.classifiers:
        content_items_handler.handle_content_item(classifier)
        pack_report += dump_pack_conditionally(artifact_manager, classifier)


def handle_connection(pack, pack_report, artifact_manager, **kwargs):
    for connection in pack.connections:
        pack_report += dump_pack_conditionally(artifact_manager, connection)


def handle_incident_type(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for incident_type in pack.incident_types:
        content_items_handler.handle_content_item(incident_type)
        pack_report += dump_pack_conditionally(artifact_manager, incident_type)


def handle_indicator_field(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for indicator_field in pack.indicator_fields:
        content_items_handler.handle_content_item(indicator_field)
        pack_report += dump_pack_conditionally(artifact_manager, indicator_field)


def handle_indicator_type(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for indicator_type in pack.indicator_types:
        # list of indicator types in one file (i.e. old format) instead of one per file aren't supported
        # from 6.0.0 server version
        if indicator_type.is_file_structure_list():
            logger.error(
                f'Indicator type "{indicator_type.path.name}" file holds a list and therefore is not supported.'
            )
        else:
            content_items_handler.handle_content_item(indicator_type)
            pack_report += dump_pack_conditionally(artifact_manager, indicator_type)


def handle_job(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for job in pack.jobs:
        content_items_handler.handle_content_item(job)
        pack_report += dump_pack_conditionally(artifact_manager, job)


def handle_layout(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for layout in pack.layouts:
        content_items_handler.handle_content_item(layout)
        pack_report += dump_pack_conditionally(artifact_manager, layout)


def handle_list_item(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for list_item in pack.lists:
        content_items_handler.handle_content_item(list_item)
        pack_report += dump_pack_conditionally(artifact_manager, list_item)


def handle_test_playbook(pack, pack_report, artifact_manager, **kwargs):
    for test_playbook in pack.test_playbooks:
        pack_report += dump_pack_conditionally(artifact_manager, test_playbook)


def handle_wizard(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for wizard in pack.wizards:
        content_items_handler.handle_content_item(wizard)
        pack_report += dump_pack_conditionally(artifact_manager, wizard)


def handle_dashboard(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for dashboard in pack.dashboards:
        content_items_handler.handle_content_item(dashboard)
        pack_report += dump_pack_conditionally(artifact_manager, dashboard)


def handle_generic_definition(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for generic_definition in pack.generic_definitions:
        content_items_handler.handle_content_item(generic_definition)
        pack_report += dump_pack_conditionally(artifact_manager, generic_definition)


def handle_generic_module(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for generic_module in pack.generic_modules:
        content_items_handler.handle_content_item(generic_module)
        pack_report += dump_pack_conditionally(artifact_manager, generic_module)


def handle_generic_type(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for generic_type in pack.generic_types:
        content_items_handler.handle_content_item(generic_type)
        pack_report += dump_pack_conditionally(artifact_manager, generic_type)


def handle_generic_field(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for generic_field in pack.generic_fields:
        content_items_handler.handle_content_item(generic_field)
        pack_report += dump_pack_conditionally(artifact_manager, generic_field)


def handle_pre_process_rule(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for pre_process_rule in pack.pre_process_rules:
        content_items_handler.handle_content_item(pre_process_rule)
        pack_report += dump_pack_conditionally(artifact_manager, pre_process_rule)


def handle_report(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for report in pack.reports:
        content_items_handler.handle_content_item(report)
        pack_report += dump_pack_conditionally(artifact_manager, report)


def handle_widget(content_items_handler, pack, pack_report, artifact_manager, **kwargs):
    for widget in pack.widgets:
        content_items_handler.handle_content_item(widget)
        pack_report += dump_pack_conditionally(artifact_manager, widget)


def handle_parsing_rule(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for parsing_rule in pack.parsing_rules:
        content_items_handler.handle_content_item(parsing_rule)
        pack_report += dump_pack_conditionally(artifact_manager, parsing_rule)


def handle_modeling_rule(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for modeling_rule in pack.modeling_rules:
        content_items_handler.handle_content_item(modeling_rule)
        pack_report += dump_pack_conditionally(artifact_manager, modeling_rule)


def handle_correlation_rule(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for correlation_rule in pack.correlation_rules:
        content_items_handler.handle_content_item(correlation_rule)
        pack_report += dump_pack_conditionally(artifact_manager, correlation_rule)


def handle_xsiam_dashboard(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for xsiam_dashboard in pack.xsiam_dashboards:
        content_items_handler.handle_content_item(xsiam_dashboard)
        pack_report += dump_pack_conditionally(artifact_manager, xsiam_dashboard)


def handle_xsiam_report(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for xsiam_report in pack.xsiam_reports:
        content_items_handler.handle_content_item(xsiam_report)
        pack_report += dump_pack_conditionally(artifact_manager, xsiam_report)


def handle_trigger(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for trigger in pack.triggers:
        content_items_handler.handle_content_item(trigger)
        pack_report += dump_pack_conditionally(artifact_manager, trigger)


def handle_xdrc_template(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for xdrc_template in pack.xdrc_templates:
        content_items_handler.handle_content_item(xdrc_template)
        pack_report += dump_pack_conditionally(artifact_manager, xdrc_template)


def handle_layout_rule(
    content_items_handler, pack, pack_report, artifact_manager, **kwargs
):
    for layout_rule in pack.layout_rules:
        content_items_handler.handle_content_item(layout_rule)
        pack_report += dump_pack_conditionally(artifact_manager, layout_rule)


def handle_tools(pack, pack_report, artifact_manager, **kwargs):
    for tool in pack.tools:
        object_report = ObjectReport(tool, content_packs=True)
        created_files = tool.dump(
            artifact_manager.content_packs_path / pack.id / TOOLS_DIR
        )
        if not artifact_manager.only_content_packs:
            object_report.set_content_new()
            dump_link_files(
                artifact_manager, tool, artifact_manager.content_new_path, created_files
            )
            object_report.set_content_all()
            dump_link_files(
                artifact_manager, tool, artifact_manager.content_all_path, created_files
            )
        pack_report += object_report


def handle_pack_metadata(pack, pack_report, artifact_manager, **kwargs):
    if pack.pack_metadata:
        pack_report += ObjectReport(pack.pack_metadata, content_packs=True)
        pack.pack_metadata.dump(artifact_manager.content_packs_path / pack.id)


def handle_metadata(
    content_items_handler, is_feed_pack, pack, pack_report, artifact_manager, **kwargs
):
    if pack.metadata:
        pack_report += ObjectReport(pack.metadata, content_packs=True)
        pack.metadata.content_items = content_items_handler.content_items
        pack.metadata.server_min_version = (
            pack.metadata.server_min_version or content_items_handler.server_min_version
        )
        if artifact_manager.id_set_path and not artifact_manager.filter_by_id_set:
            # Dependencies can only be done when id_set file is given.
            pack.metadata.handle_dependencies(
                pack.path.name, artifact_manager.id_set_path, logger
            )
        else:
            logger.warning(
                "Skipping dependencies extraction since no id_set file was provided."
            )
        if is_feed_pack and "TIM" not in pack.metadata.tags:
            pack.metadata.tags.append("TIM")
        pack.metadata.dump_metadata_file(artifact_manager.content_packs_path / pack.id)


def handle_readme(pack, pack_report, artifact_manager, **kwargs):
    if pack.readme or pack.contributors:
        if not pack.readme:
            readme_file = os.path.join(pack.path, "README.md")
            open(readme_file, "a+").close()
        readme_obj = pack.readme
        readme_obj.contributors = pack.contributors
        pack_report += ObjectReport(readme_obj, content_packs=True)
        readme_obj.dump(artifact_manager.content_packs_path / pack.id)


def handle_author_image(pack, pack_report, artifact_manager, **kwargs):
    if pack.author_image:
        pack_report += ObjectReport(pack.author_image, content_packs=True)
        pack.author_image.dump(artifact_manager.content_packs_path / pack.id)


def dump_pack(
    artifact_manager: ArtifactsManager, pack: Pack
) -> ArtifactsReport:  # noqa: C901
    """Dumping content/Packs/<pack_id>/ into:
            1. content_test
            2. content_new
            3. content_all
            4. content_packs
            5. uploadable_packs

    Args:
        artifact_manager: Artifacts manager object.
        pack: Pack object.

    Notes:
        1. Include all file object, excluding:
            a. Change_log files (Deprecated).
            b. Integration/Script/Playbook readme (Used for website documentation deployment).
            c. .pack-ignore (Internal only).
            d. .secrets-ignore (Internal only).

    Returns:
        ArtifactsReport: ArtifactsReport object.
    """
    global logger
    pack_report = ArtifactsReport(f"Pack {pack.id}:")

    pack.metadata.load_user_metadata(pack.id, pack.path.name, pack.path, logger)
    pack.filter_items_by_id_set = artifact_manager.filter_by_id_set
    pack.pack_info_from_id_set = artifact_manager.packs_section_from_id_set
    content_items_handler = ContentItemsHandler(
        artifact_manager.id_set, artifact_manager.alternate_fields
    )
    is_feed_pack = False

    content_items_to_handler = {
        FileType.RELEASE_NOTES: handle_release_notes,
        FileType.RELEASE_NOTES_CONFIG: handle_release_note_config,
        FileType.CONNECTION: handle_connection,
        FileType.TEST_PLAYBOOK: handle_test_playbook,
        FileType.SCRIPT: handle_script,
        FileType.INCIDENT_FIELD: handle_incident_field,
        FileType.INTEGRATION: handle_integration,
        FileType.PLAYBOOK: handle_playbook,
        FileType.CLASSIFIER: handle_classifier,
        FileType.INCIDENT_TYPE: handle_incident_type,
        FileType.INDICATOR_FIELD: handle_indicator_field,
        FileType.INDICATOR_TYPE: handle_indicator_type,
        FileType.JOB: handle_job,
        FileType.LAYOUT: handle_layout,
        FileType.LISTS: handle_list_item,
        FileType.WIZARD: handle_wizard,
        FileType.DASHBOARD: handle_dashboard,
        FileType.GENERIC_DEFINITION: handle_generic_definition,
        FileType.GENERIC_MODULE: handle_generic_module,
        FileType.GENERIC_TYPE: handle_generic_type,
        FileType.GENERIC_FIELD: handle_generic_field,
        FileType.PRE_PROCESS_RULES: handle_pre_process_rule,
        FileType.REPORT: handle_report,
        FileType.WIDGET: handle_widget,
        FileType.PARSING_RULE: handle_parsing_rule,
        FileType.MODELING_RULE: handle_modeling_rule,
        FileType.CORRELATION_RULE: handle_correlation_rule,
        FileType.XSIAM_DASHBOARD: handle_xsiam_dashboard,
        FileType.XSIAM_REPORT: handle_xsiam_report,
        FileType.TRIGGER: handle_trigger,
        FileType.XDRC_TEMPLATE: handle_xdrc_template,
        FileType.TOOL: handle_tools,
        FileType.PACK_METADATA: handle_pack_metadata,
        FileType.METADATA: handle_metadata,
        FileType.README: handle_readme,
        FileType.AUTHOR_IMAGE: handle_author_image,
        FileType.LAYOUT_RULE: handle_layout_rule,
    }

    items_to_dump = MARKETPLACE_TO_ITEMS_MAPPING.get(
        artifact_manager.marketplace, XSOAR_MARKETPLACE_ITEMS_TO_DUMP
    )
    for item in items_to_dump:
        content_items_to_handler[item](
            content_items_handler=content_items_handler,
            pack=pack,  # type: ignore[operator]
            pack_report=pack_report,
            artifact_manager=artifact_manager,
            is_feed_pack=is_feed_pack,
        )

    return pack_report


def dump_pack_conditionally(
    artifact_manager: ArtifactsManager, content_object: ContentObject
) -> ObjectReport:
    """Dump pack object by the following logic

    Args:
        artifact_manager: Artifacts manager object.
        content_object: content_object (e.g. Integration/Script/Layout etc)

    Returns:
        ObjectReport: ObjectReport object.
    """
    object_report = ObjectReport(content_object)
    pack_created_files: List[Path] = []
    test_new_created_files: List[Path] = []

    with content_files_handler(artifact_manager, content_object) as files_to_remove:
        # Content packs filter - When unify also _45.yml created which should be deleted after copy it if needed
        if is_in_content_packs(content_object):
            object_report.set_content_packs()
            # Unify will create *_45.yml files which shouldn't be in content_packs
            pack_created_files.extend(
                dump_link_files(
                    artifact_manager,
                    content_object,
                    artifact_manager.content_packs_path
                    / calc_relative_packs_dir(artifact_manager, content_object),
                )
            )
            # Collecting files *_45.yml which created and need to be removed after execution.
            files_to_remove.extend(
                [
                    created_file
                    for created_file in pack_created_files
                    if created_file.name.endswith("_45.yml")
                ]
            )

        # Content test filter
        if is_in_content_test(artifact_manager, content_object):
            object_report.set_content_test()
            test_new_created_files = dump_link_files(
                artifact_manager,
                content_object,
                artifact_manager.content_test_path,
                pack_created_files,
            )

        # Content new filter
        if is_in_content_new(artifact_manager, content_object):
            object_report.set_content_new()
            test_new_created_files = dump_link_files(
                artifact_manager,
                content_object,
                artifact_manager.content_new_path,
                pack_created_files,
            )
        # Content all filter
        if is_in_content_all(artifact_manager, content_object):
            object_report.set_content_all()
            dump_link_files(
                artifact_manager,
                content_object,
                artifact_manager.content_all_path,
                test_new_created_files,
            )

    return object_report


@contextmanager
def content_files_handler(
    artifact_manager: ArtifactsManager, content_object: ContentObject
):
    """Pre-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py global variables:
                a. CONTENT_RELEASE_VERSION to given content version flag.
                b. CONTENT_BRANCH_NAME to active branch

        Post-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py to original state.
            2. Unifier creates *_45.yml files in content_pack by default which is not support due to_version lower than
                NEWEST_SUPPORTED_VERSION, Therefor after copy it to content_new, delete it.

    Args:
        artifact_manager: Command line configuration.
        content_object: content_object (e.g. Integration/Script/Layout etc)

    Yields:
        List[Path]: List of file to be removed after execution.
    """
    files_to_remove: List[Path] = []

    try:
        if (
            (BASE_PACK in content_object.path.parts)
            and isinstance(content_object, Script)
            and content_object.code_path
            and content_object.code_path.name == "CommonServerPython.py"
        ):
            # Modify CommonServerPython.py global variables
            repo = artifact_manager.content.git()
            modify_common_server_constants(
                content_object.code_path,
                artifact_manager.content_version,
                "master" if not repo else repo.active_branch,
            )
        yield files_to_remove
    finally:
        if (
            (BASE_PACK in content_object.path.parts)
            and isinstance(content_object, Script)
            and content_object.code_path
            and content_object.code_path.name == "CommonServerPython.py"
        ):
            # Modify CommonServerPython.py global variables
            modify_common_server_constants(content_object.code_path, "0.0.0", "master")

        # Delete yaml which created by Unifier in packs and to_version/toVersion lower than NEWEST_SUPPORTED_VERSION
        for file_path in files_to_remove:
            file_path.unlink()


def modify_common_server_constants(
    code_path: Path, content_version: str, branch_name: Optional[str] = None
):
    """Modify content/Packs/Base/Scripts/CommonServerPython.py global variables:
            a. CONTENT_RELEASE_VERSION to given content version flag.
            b. CONTENT_BRANCH_NAME to active branch

    Args:
        code_path: Packs/Base/Scripts/CommonServerPython.py full code path.
        branch_name: branch name to update in CONTENT_BRANCH_NAME
        content_version: content version to update in CONTENT_RELEASE_VERSION
    """
    file_content_new = re.sub(
        r"CONTENT_RELEASE_VERSION = '\d.\d.\d'",
        f"CONTENT_RELEASE_VERSION = '{content_version}'",
        code_path.read_text(),
    )
    file_content_new = re.sub(
        r"CONTENT_BRANCH_NAME = '\w+'",
        f"CONTENT_BRANCH_NAME = '{branch_name}'",
        file_content_new,
    )
    code_path.write_text(file_content_new)


########################
# Suffix add functions #
########################


def suffix_handler(artifact_manager: ArtifactsManager):
    """Add suffix to file names exclude:
            1. pack_metadata.json
            2. README.
            3. content_descriptor.json
            3. ReleaseNotes/**

        Include:
            1. *.json
            2. *.(yaml|yml)

    Args:
        artifact_manager: Artifacts manager object.
    """
    files_pattern_to_add_suffix = (
        "!reputations.json|!pack_metadata.json|"
        "!doc-*.json|!content-descriptor.json|*.{json,yml,yaml}"
    )
    if artifact_manager.suffix:
        files_content_packs = artifact_manager.content_packs_path.rglob(
            files_pattern_to_add_suffix, flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE
        )
        files_content_test = artifact_manager.content_test_path.rglob(
            files_pattern_to_add_suffix, flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE
        )
        files_content_new = artifact_manager.content_new_path.rglob(
            files_pattern_to_add_suffix, flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE
        )
        files_content_all = artifact_manager.content_all_path.rglob(
            files_pattern_to_add_suffix, flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE
        )
        for files in [
            files_content_new,
            files_content_packs,
            files_content_test,
            files_content_all,
        ]:
            for file in files:
                file_name_split = file.name.split(".")
                file_real_stem = ".".join(file_name_split[:-1])
                suffix = file_name_split[-1]
                file.rename(
                    file.with_name(
                        f"{file_real_stem}{artifact_manager.suffix}.{suffix}"
                    )
                )


###########
# Helpers #
###########


class DuplicateFiles(Exception):
    def __init__(self, exiting_file: Path, src: Path):
        """Exception raised when 2 files with the same name existing in same directory when creating artifacts

        Args:
            exiting_file: File allready exists in artifacts.
            src: File source which copy or link to same directory.
        """
        self.exiting_file = exiting_file
        self.src = src
        self.msg = f"\nFound duplicate files\n1. {src}\n2. {exiting_file}"


def dump_link_files(
    artifact_manager: ArtifactsManager,
    content_object: ContentObject,
    dest_dir: Path,
    created_files: Optional[List[Path]] = None,
) -> List[Path]:
    """Dump content object to requested destination dir.
    Due to performance issue if known files already created and dump is done for the same object, This function
    will link files instead of creating the files from scratch (Reduce unify, split etc.)

    Args:
        artifact_manager: Artifacts manager object.
        content_object: Content object.
        dest_dir: Destination dir.
        created_files: Pre-created file (Not mandatory).

    Returns:
        List[Path]: List of new created files.

    Raises:
        DuplicateFiles: Exception occurred if duplicate files exists in the same dir (Protect from override).
    """
    new_created_files = []
    # Handle case where files already created
    if created_files:
        for file in created_files:
            new_file = dest_dir / file.name
            if (
                new_file.exists()
                and new_file.stat().st_mtime >= artifact_manager.execution_start
            ):
                raise DuplicateFiles(new_file, content_object.path)
            else:
                os.link(file, new_file)
                new_created_files.append(new_file)
    # Handle case where object first time dump.
    else:
        target = dest_dir / content_object.normalize_file_name()
        if (
            target.exists()
            and target.stat().st_mtime >= artifact_manager.execution_start
        ):
            raise DuplicateFiles(target, content_object.path)
        else:
            new_created_files.extend(content_object.dump(dest_dir=dest_dir))

    return new_created_files


def calc_relative_packs_dir(
    artifact_manager: ArtifactsManager, content_object: ContentObject
) -> Path:
    relative_pack_path = artifact_manager.get_relative_pack_path(content_object)
    if (
        (
            INTEGRATIONS_DIR in relative_pack_path.parts
            and relative_pack_path.parts[-2] != INTEGRATIONS_DIR
        )
        or (
            SCRIPTS_DIR in relative_pack_path.parts
            and relative_pack_path.parts[-2] != SCRIPTS_DIR
        )
        or (
            PARSING_RULES_DIR in relative_pack_path.parts
            and relative_pack_path.parts[-2] != PARSING_RULES_DIR
        )
        or (
            MODELING_RULES_DIR in relative_pack_path.parts
            and relative_pack_path.parts[-2] != MODELING_RULES_DIR
        )
        or (
            XDRC_TEMPLATE_DIR in relative_pack_path.parts
            and relative_pack_path.parts[-2] != XDRC_TEMPLATE_DIR
        )
    ):
        relative_pack_path = relative_pack_path.parent.parent
    else:
        relative_pack_path = relative_pack_path.parent

    return relative_pack_path


def child_mute():
    """Mute child process inorder to keep log clean"""
    sys.stdout = open(os.devnull, "w")


###################################
# Artifacts Directories functions #
###################################


@contextmanager
def ArtifactsDirsHandler(artifact_manager: ArtifactsManager):
    """Artifacts Directories handler.
    Logic by time line:
        1. Delete artifacts directories if exists.
        2. Create directories.
        3. If any error occurred -> Delete artifacts directories -> Exit.
        4. If finish successfully:
            a. If zip:
                1. Sign packs if needed.
                2. Zip artifacts zip.
                3. Zip packs for uploading.
                4. Delete artifacts directories.
        5. log report.

    Args:
        artifact_manager: Artifacts manager object.
    """
    try:
        delete_dirs(artifact_manager)
        create_dirs(artifact_manager)
        yield
    except (Exception, KeyboardInterrupt):
        delete_dirs(artifact_manager)
        artifact_manager.exit_code = EX_FAIL
    else:
        if artifact_manager.zip_artifacts:
            sign_packs(artifact_manager)
            zip_packs(artifact_manager)
            zip_dirs(artifact_manager)
            delete_dirs(artifact_manager)

        report_artifacts_paths(artifact_manager)


def delete_dirs(artifact_manager: ArtifactsManager):
    """Delete artifacts directories"""
    for artifact_dir in artifact_manager.get_dir_to_delete():
        if artifact_dir.exists():
            rmtree(artifact_dir)


def create_dirs(artifact_manager: ArtifactsManager):
    """Create artifacts directories"""
    if artifact_manager.only_content_packs:
        artifact_manager.content_packs_path.mkdir(parents=True)
    else:
        for artifact_dir in [
            artifact_manager.content_test_path,
            artifact_manager.content_new_path,
            artifact_manager.content_packs_path,
            artifact_manager.content_all_path,
        ]:
            artifact_dir.mkdir(parents=True)


def zip_dirs(artifact_manager: ArtifactsManager):
    """Zip artifacts directories"""
    if artifact_manager.only_content_packs:
        make_archive(
            artifact_manager.content_packs_path.as_posix(),
            "zip",
            artifact_manager.content_packs_path,
        )
    else:
        with ProcessPoolHandler(artifact_manager) as pool:
            for artifact_dir in [
                artifact_manager.content_test_path,
                artifact_manager.content_new_path,
                artifact_manager.content_packs_path,
                artifact_manager.content_all_path,
            ]:
                pool.schedule(make_archive, args=(artifact_dir, "zip", artifact_dir))


def zip_packs(artifact_manager: ArtifactsManager):
    """Zip packs directories"""
    with ProcessPoolHandler(artifact_manager) as pool:
        for pack_name, pack in artifact_manager.packs.items():
            if (
                artifact_manager.pack_names != ["all"]
                and pack_name not in artifact_manager.pack_names
            ):
                continue
            dumped_pack_dir = os.path.join(artifact_manager.content_packs_path, pack.id)
            zip_path = os.path.join(
                artifact_manager.content_uploadable_zips_path, pack.id
            )

            pool.schedule(make_archive, args=(zip_path, "zip", dumped_pack_dir))


def report_artifacts_paths(artifact_manager: ArtifactsManager):
    """Report artifacts results destination"""
    global logger

    logger.info("\nArtifacts created:")
    if artifact_manager.zip_artifacts:
        template = "\n\t - {}.zip"
    else:
        template = "\n\t - {}"

    logger.info(template.format(artifact_manager.content_packs_path))

    if not artifact_manager.only_content_packs:
        for artifact_dir in [
            artifact_manager.content_test_path,
            artifact_manager.content_new_path,
            artifact_manager.content_all_path,
        ]:
            logger.info(template.format(artifact_dir))

    if artifact_manager.zip_artifacts:
        logger.info(f"\n\t - {artifact_manager.content_uploadable_zips_path}")


def sign_packs(artifact_manager: ArtifactsManager):
    """Sign packs directories"""
    global logger

    if artifact_manager.signDirectory and artifact_manager.signature_key:
        with ProcessPoolHandler(artifact_manager) as pool:
            with open("keyfile", "wb") as keyfile:
                keyfile.write(artifact_manager.signature_key.encode())

            futures: List[ProcessFuture] = []
            if "all" in artifact_manager.pack_names:
                for pack_name, pack in artifact_manager.packs.items():
                    dumped_pack_dir = os.path.join(
                        artifact_manager.content_packs_path, pack.id
                    )
                    futures.append(
                        pool.schedule(
                            pack.sign_pack,
                            args=(
                                logger,
                                dumped_pack_dir,
                                artifact_manager.signDirectory,
                            ),
                        )
                    )
            else:
                for pack_name in artifact_manager.pack_names:
                    if pack_name in artifact_manager.packs:
                        pack = artifact_manager.packs[pack_name]
                        dumped_pack_dir = os.path.join(
                            artifact_manager.content_packs_path, pack.id
                        )
                        futures.append(
                            pool.schedule(
                                pack.sign_pack,
                                args=(
                                    logger,
                                    dumped_pack_dir,
                                    artifact_manager.signDirectory,
                                ),
                            )
                        )

        wait_futures_complete(futures, artifact_manager)

    elif artifact_manager.signDirectory or artifact_manager.signature_key:
        logger.error(
            "Failed to sign packs. In order to do so, you need to provide both signature_key and "
            "sign_directory arguments."
        )
