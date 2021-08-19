from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import OLD_INDICATOR_TYPE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects import (
    AgentTool, AuthorImage, ChangeLog, Classifier, ClassifierMapper,
    Connection, Contributors, Dashboard, DocFile, GenericDefinition,
    GenericField, GenericModule, GenericType, IncidentField, IncidentType,
    IndicatorField, IndicatorType, Integration, Layout, LayoutsContainer,
    OldClassifier, OldIndicatorType, PackIgnore, PackMetaData, Playbook,
    Readme, ReleaseNote, Report, Script, SecretIgnore, Widget, ReleaseNoteConfig)
from demisto_sdk.commands.common.content.objects.root_objects import \
    Documentation
from demisto_sdk.commands.common.tools import find_type

from .errors import ContentFactoryError

TYPE_CONVERSION_BY_FileType = {
    FileType.INTEGRATION: Integration,
    FileType.BETA_INTEGRATION: Integration,
    FileType.PLAYBOOK: Playbook,
    FileType.SCRIPT: Script,
    FileType.TEST_SCRIPT: Script,
    FileType.TEST_PLAYBOOK: Playbook,
    FileType.DASHBOARD: Dashboard,
    FileType.WIDGET: Widget,
    FileType.REPORT: Report,
    FileType.OLD_CLASSIFIER: OldClassifier,
    FileType.CLASSIFIER: Classifier,
    FileType.MAPPER: ClassifierMapper,
    FileType.LAYOUT: Layout,
    FileType.LAYOUTS_CONTAINER: LayoutsContainer,
    FileType.REPUTATION: IndicatorType,
    FileType.INDICATOR_FIELD: IndicatorField,
    FileType.INCIDENT_FIELD: IncidentField,
    FileType.INCIDENT_TYPE: IncidentType,
    FileType.CHANGELOG: ChangeLog,
    FileType.CONNECTION: Connection,
    FileType.DESCRIPTION: Readme,
    FileType.README: Readme,
    FileType.RELEASE_NOTES: ReleaseNote,
    FileType.RELEASE_NOTES_CONFIG: ReleaseNoteConfig,
    FileType.DOC_IMAGE: DocFile,
    FileType.JAVASCRIPT_FILE: '',
    FileType.POWERSHELL_FILE: '',
    FileType.PYTHON_FILE: '',
    FileType.CONTRIBUTORS: Contributors,
    FileType.GENERIC_TYPE: GenericType,
    FileType.GENERIC_FIELD: GenericField,
    FileType.GENERIC_MODULE: GenericModule,
    FileType.GENERIC_DEFINITION: GenericDefinition
}

TYPE_CONVERSION_BY_FILE_NAME = {
    'pack_metadata.json': PackMetaData,
    '.secrets-ignore': SecretIgnore,
    '.pack-ignore': PackIgnore,
    f'{OLD_INDICATOR_TYPE}.json': OldIndicatorType,
    'Author_image.png': AuthorImage,
}


def path_to_pack_object(path: Union[Path, str]) -> object:
    """ Create content object by path, By the following steps:
            1. Try determinist file name -> pack_metadata.json, .secrets-ignore, .pack-ignore, reputations.json
            2. If 'Tools' in path -> Object is AgentTool.
            3. If file start with 'doc-*' -> Object is Documentation.
            4. Let find_type determine object type.

    Args:
        path: File path to determine object type.

    Returns:
        object: Content object.

    Raises:
        ContentFactoryError: If not able to determine object type from file path.
    """
    path = Path(path)
    # Determinist conversion by file name.
    object_type = TYPE_CONVERSION_BY_FILE_NAME.get(path.name)
    # Tools in path
    if not object_type and 'Tools' in path.parts:
        object_type = AgentTool
    # File name start with doc-*
    if not object_type and path.name.startswith('doc-'):
        object_type = Documentation
    # find_type handling
    if not object_type:
        file_type = find_type(str(path))
        object_type = TYPE_CONVERSION_BY_FileType.get(file_type)
    # Raise exception if not succeed
    if not object_type:
        raise ContentFactoryError(None, path, "Unable to get object type from path.")

    return object_type(path)
