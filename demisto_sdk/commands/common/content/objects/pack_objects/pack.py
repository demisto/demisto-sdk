import logging
import subprocess
from distutils.version import LooseVersion
from typing import Any, Dict, Iterator, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   CONNECTIONS_DIR,
                                                   DASHBOARDS_DIR,
                                                   DOC_FILES_DIR,
                                                   GENERIC_DEFINITIONS_DIR,
                                                   GENERIC_FIELDS_DIR,
                                                   GENERIC_MODULES_DIR,
                                                   GENERIC_TYPES_DIR,
                                                   INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR,
                                                   INDICATOR_FIELDS_DIR,
                                                   INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR, JOBS_DIR,
                                                   LAYOUTS_DIR, LISTS_DIR,
                                                   PACK_VERIFY_KEY,
                                                   PLAYBOOKS_DIR,
                                                   PRE_PROCESS_RULES_DIR,
                                                   RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   TOOLS_DIR, WIDGETS_DIR,
                                                   FileType)
from demisto_sdk.commands.common.content.objects.pack_objects import (
    AgentTool, AuthorImage, Classifier, ClassifierMapper, Connection,
    Contributors, Dashboard, DocFile, GenericDefinition, GenericField,
    GenericModule, GenericType, IncidentField, IncidentType, IndicatorField,
    IndicatorType, Integration, Job, LayoutObject, Lists, OldClassifier,
    PackIgnore, PackMetaData, Playbook, PreProcessRule, Readme, ReleaseNote,
    ReleaseNoteConfig, Report, Script, SecretIgnore, Widget)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import (get_demisto_version,
                                               is_object_in_id_set)
from demisto_sdk.commands.test_content import tools

TURN_VERIFICATION_ERROR_MSG = "Can not set the pack verification configuration key,\nIn the server - go to Settings -> troubleshooting\
 and manually {action}."
DELETE_VERIFY_KEY_ACTION = f'delete the key "{PACK_VERIFY_KEY}"'
SET_VERIFY_KEY_ACTION = f'set the key "{PACK_VERIFY_KEY}" to ' + '{}'


class Pack:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)
        # in case the given path are a Pack and not zipped pack - we init the metadata from the pack
        if not str(path).endswith('.zip'):
            self._metadata = PackMetaData(self._path.joinpath('metadata.json'))
        self._filter_items_by_id_set = False
        self._pack_info_from_id_set: Dict[Any, Any] = {}

    def _content_files_list_generator_factory(self, dir_name: str, suffix: str) -> Iterator[Any]:
        """Generic content objects iterable generator

        Args:
            dir_name: Directory name, for example: Integrations, Documentations etc.
            suffix: file suffix to search for, if not supplied then any suffix.

        Returns:
            object: Any valid content object found in the given directory.
        """
        objects_path = (self._path / dir_name).glob(patterns=[f"*.{suffix}", f"*/*.{suffix}"])
        for object_path in objects_path:
            content_object = path_to_pack_object(object_path)
            # skip content items that are not displayed in the id set, if the corresponding flag is used
            if self._filter_items_by_id_set and content_object.type().value not in [FileType.RELEASE_NOTES.value,
                                                                                    FileType.RELEASE_NOTES_CONFIG.value]:
                object_id = content_object.get_id()
                if is_object_in_id_set(object_id, self._pack_info_from_id_set):
                    yield content_object
                else:
                    logging.warning(f'Skipping object {object_path} with id {object_id} since its missing from '
                                    f'the given id set')
            else:
                yield content_object

    def _content_dirs_list_generator_factory(self, dir_name) -> Iterator[Any]:
        """Generic content objects iterable generator

        Args:
            dir_name: Directory name, for example: Tools.

        Returns:
            object: Any valid content object found in the given directory.
        """
        objects_path = (self._path / dir_name).glob(patterns=["*/"])
        for object_path in objects_path:
            yield path_to_pack_object(object_path)

    @property
    def id(self) -> str:
        return self._path.parts[-1]

    @property
    def path(self) -> Path:
        return self._path

    @property
    def integrations(self) -> Iterator[Integration]:
        return self._content_files_list_generator_factory(dir_name=INTEGRATIONS_DIR,
                                                          suffix="yml")

    @property
    def scripts(self) -> Iterator[Script]:
        return self._content_files_list_generator_factory(dir_name=SCRIPTS_DIR,
                                                          suffix="yml")

    @property
    def playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(dir_name=PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def reports(self) -> Iterator[Report]:
        return self._content_files_list_generator_factory(dir_name=REPORTS_DIR,
                                                          suffix="json")

    @property
    def dashboards(self) -> Iterator[Dashboard]:
        return self._content_files_list_generator_factory(dir_name=DASHBOARDS_DIR,
                                                          suffix="json")

    @property
    def incident_types(self) -> Iterator[IncidentType]:
        return self._content_files_list_generator_factory(dir_name=INCIDENT_TYPES_DIR,
                                                          suffix="json")

    @property
    def incident_fields(self) -> Iterator[IncidentField]:
        return self._content_files_list_generator_factory(dir_name=INCIDENT_FIELDS_DIR,
                                                          suffix="json")

    @property
    def layouts(self) -> Iterator[LayoutObject]:
        return self._content_files_list_generator_factory(dir_name=LAYOUTS_DIR,
                                                          suffix="json")

    @property
    def pre_process_rules(self) -> Iterator[PreProcessRule]:
        return self._content_files_list_generator_factory(dir_name=PRE_PROCESS_RULES_DIR,
                                                          suffix="json")

    @property
    def lists(self) -> Iterator[Lists]:
        return self._content_files_list_generator_factory(dir_name=LISTS_DIR,
                                                          suffix="json")

    @property
    def classifiers(self) -> Iterator[Union[Classifier, OldClassifier, ClassifierMapper]]:
        return self._content_files_list_generator_factory(dir_name=CLASSIFIERS_DIR,
                                                          suffix="json")

    @property
    def indicator_types(self) -> Iterator[IndicatorType]:
        return self._content_files_list_generator_factory(dir_name=INDICATOR_TYPES_DIR,
                                                          suffix="json")

    @property
    def indicator_fields(self) -> Iterator[IndicatorField]:
        return self._content_files_list_generator_factory(dir_name=INDICATOR_FIELDS_DIR,
                                                          suffix="json")

    @property
    def connections(self) -> Iterator[Connection]:
        return self._content_files_list_generator_factory(dir_name=CONNECTIONS_DIR,
                                                          suffix="json")

    @property
    def test_playbooks(self) -> Iterator[Union[Playbook, Script]]:
        return self._content_files_list_generator_factory(dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def widgets(self) -> Iterator[Widget]:
        return self._content_files_list_generator_factory(dir_name=WIDGETS_DIR,
                                                          suffix="json")

    @property
    def release_notes(self) -> Iterator[ReleaseNote]:
        return self._content_files_list_generator_factory(dir_name=RELEASE_NOTES_DIR,
                                                          suffix="md")

    @property
    def release_notes_config(self) -> Iterator[ReleaseNoteConfig]:
        return self._content_files_list_generator_factory(dir_name=RELEASE_NOTES_DIR,
                                                          suffix="json")

    @property
    def generic_definitions(self) -> Iterator[GenericDefinition]:
        return self._content_files_list_generator_factory(dir_name=GENERIC_DEFINITIONS_DIR,
                                                          suffix="json")

    @property
    def generic_modules(self) -> Iterator[GenericModule]:
        return self._content_files_list_generator_factory(dir_name=GENERIC_MODULES_DIR,
                                                          suffix="json")

    @property
    def generic_types(self) -> Iterator[GenericType]:
        return self._content_files_list_generator_factory(dir_name=GENERIC_TYPES_DIR,
                                                          suffix="json")

    @property
    def generic_fields(self) -> Iterator[GenericField]:
        return self._content_files_list_generator_factory(dir_name=GENERIC_FIELDS_DIR,
                                                          suffix="json")

    @property
    def tools(self) -> Iterator[AgentTool]:
        return self._content_dirs_list_generator_factory(dir_name=TOOLS_DIR)

    @property
    def doc_files(self) -> Iterator[DocFile]:
        return self._content_files_list_generator_factory(dir_name=DOC_FILES_DIR,
                                                          suffix="*")

    @property
    def jobs(self) -> Iterator[Job]:
        return self._content_files_list_generator_factory(JOBS_DIR,
                                                          suffix="json")

    @property
    def pack_metadata(self) -> Optional[PackMetaData]:
        obj = None
        file = self._path / "pack_metadata.json"
        if file.exists():
            obj = PackMetaData(file)

        return obj

    @property
    def metadata(self) -> PackMetaData:
        return self._metadata

    @metadata.setter
    def metadata(self, metadata: Optional[PackMetaData]):
        self._metadata = metadata

    @property
    def secrets_ignore(self) -> Optional[SecretIgnore]:
        obj = None
        file = self._path / ".secrets-ignore"
        if file.exists():
            obj = SecretIgnore(file)

        return obj

    @property
    def pack_ignore(self) -> Optional[PackIgnore]:
        obj = None
        file = self._path / ".pack-ignore"
        if file.exists():
            obj = PackIgnore(file)

        return obj

    @property
    def readme(self) -> Optional[Readme]:
        obj = None
        file = self._path / "README.md"
        if file.exists():
            obj = Readme(path=file)

        return obj

    @property
    def author_image(self) -> Optional[AuthorImage]:
        obj = None
        file = self._path / "Author_image.png"
        if file.exists():
            obj = AuthorImage(file)

        return obj

    @property
    def contributors(self) -> Optional[Contributors]:
        obj = None
        file = self._path / "CONTRIBUTORS.md"
        if file.exists():
            obj = Contributors(path=file)

        return obj

    @property
    def filter_items_by_id_set(self) -> bool:
        return self._filter_items_by_id_set

    @filter_items_by_id_set.setter
    def filter_items_by_id_set(self, filter_by_id_set: bool):
        self._filter_items_by_id_set = filter_by_id_set

    @property
    def pack_info_from_id_set(self) -> dict:
        return self._pack_info_from_id_set

    @pack_info_from_id_set.setter
    def pack_info_from_id_set(self, pack_section_from_id_set: dict):
        self._pack_info_from_id_set = pack_section_from_id_set.get(self.id, {}) if pack_section_from_id_set else {}

    def sign_pack(self, logger: logging.Logger, dumped_pack_dir: Path, sign_directory: Path):
        """ Signs pack folder and creates signature file.

        Args:
            logger (logging.Logger): System logger already initialized.
            dumped_pack_dir (Path): Path to the updated pack to sign.
            sign_directory (Path): Path to the signDirectory executable file.

        """
        try:
            full_command = f'{sign_directory} {dumped_pack_dir} keyfile base64'

            signing_process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, err = signing_process.communicate()
            signing_process.wait()

            if err:
                logger.error(f'Failed to sign pack for {self.path.name} - {str(err)}')
                return

            logger.info(f'Signed {self.path.name} pack successfully')
        except Exception as error:
            logger.error(f'Error while trying to sign pack {self.path.name}.\n {error}')

    def is_server_version_ge(self, client, server_version_to_check):
        server_version = get_demisto_version(client)
        return LooseVersion(server_version.base_version) >= LooseVersion(server_version_to_check)  # type: ignore

    def upload(self, logger: logging.Logger, client: demisto_client, skip_validation: bool):
        """
        Upload the pack zip to demisto_client,
        from 6.5 server version we have the option to use skip_verify arg instead of server configuration.
        Args:
            logger (logging.Logger): System logger already initialized.
            client: The demisto_client object of the desired XSOAR machine to upload to.
            skip_validation: if true will skip upload packs validation.
        Returns:
            The result of the upload command from demisto_client
        """
        if self.is_server_version_ge(client, '6.6.0') and skip_validation:
            try:
                logger.info('Uploading...')
                return client.upload_content_packs(
                    file=self.path, skip_verify='true', skip_validation='true')  # type: ignore

            except Exception as err:
                raise Exception(f'Failed to upload pack, error: {err}')

        if self.is_server_version_ge(client, '6.5.0'):
            try:
                logger.info('Uploading...')
                return client.upload_content_packs(file=self.path, skip_verify='true')  # type: ignore

            except Exception as err:
                raise Exception(f'Failed to upload pack, error: {err}')

        # the flow are - turn off the sign check -> upload -> turn back the check to be as previously
        logger.info('Turn off the server verification for signed packs')
        _, _, prev_conf = tools.update_server_configuration(client=client,
                                                            server_configuration={PACK_VERIFY_KEY: 'false'},
                                                            error_msg='Can not turn off the pack verification')
        try:
            logger.info('Uploading...')
            return client.upload_content_packs(file=self.path)  # type: ignore
        finally:
            config_keys_to_update = None
            config_keys_to_delete = None
            try:
                prev_key_val = prev_conf.get(PACK_VERIFY_KEY, None)
                if prev_key_val is not None:
                    config_keys_to_update = {PACK_VERIFY_KEY: prev_key_val}
                else:
                    config_keys_to_delete = {PACK_VERIFY_KEY}
                logger.info('Setting the server verification to be as previously')
                tools.update_server_configuration(client=client,
                                                  server_configuration=config_keys_to_update,
                                                  config_keys_to_delete=config_keys_to_delete,
                                                  error_msg='Can not turn on the pack verification')
            except (Exception, KeyboardInterrupt):
                action = DELETE_VERIFY_KEY_ACTION if prev_key_val is None \
                    else SET_VERIFY_KEY_ACTION.format(prev_key_val)
                raise Exception(TURN_VERIFICATION_ERROR_MSG.format(action=action))
