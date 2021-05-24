import logging
import subprocess
from typing import Any, Iterator, Optional, Union

from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   CONNECTIONS_DIR,
                                                   DASHBOARDS_DIR,
                                                   DOC_FILES_DIR,
                                                   INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR,
                                                   INDICATOR_FIELDS_DIR,
                                                   INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, PLAYBOOKS_DIR,
                                                   RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   TOOLS_DIR, WIDGETS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects import (
    AgentTool, AuthorImage, Classifier, ClassifierMapper, Connection,
    Dashboard, DocFile, IncidentField, IncidentType, IndicatorField,
    IndicatorType, Integration, LayoutObject, OldClassifier, PackIgnore,
    PackMetaData, Playbook, Readme, ReleaseNote, Report, Script, SecretIgnore,
    Widget)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from wcmatch.pathlib import Path


class Pack:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)
        self._metadata = PackMetaData(self._path.joinpath('metadata.json'))

    def _content_files_list_generator_factory(self, dir_name: str, suffix: str) -> Iterator[Any]:
        """Generic content objcets iterable generator

        Args:
            dir_name: Directory name, for example: Integrations, Documentations etc.
            suffix: file suffix to search for, if not supplied then any suffix.

        Returns:
            object: Any valid content object found in the given directory.
        """
        objects_path = (self._path / dir_name).glob(patterns=[f"*.{suffix}", f"*/*.{suffix}"])
        for object_path in objects_path:
            yield path_to_pack_object(object_path)

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
    def tools(self) -> Iterator[AgentTool]:
        return self._content_dirs_list_generator_factory(dir_name=TOOLS_DIR)

    @property
    def doc_files(self) -> Iterator[DocFile]:
        return self._content_files_list_generator_factory(dir_name=DOC_FILES_DIR,
                                                          suffix="*")

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
            obj = Readme(file)

        return obj

    @property
    def author_image(self) -> Optional[AuthorImage]:
        obj = None
        file = self._path / "Author_image.png"
        if file.exists():
            obj = AuthorImage(file)

        return obj

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
