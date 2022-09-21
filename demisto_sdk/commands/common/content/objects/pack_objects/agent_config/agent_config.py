import shutil
from typing import List, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import AGENT_CONFIG, FileType, ENTITY_TYPE_TO_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import JSONContentObject
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name
from demisto_sdk.commands.unify.agent_config_unifier import AgentConfigUnifier


class AgentConfig(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, AGENT_CONFIG)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, AGENT_CONFIG)

    def upload(self, client: demisto_client):
        """
        Upload the agent_config to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_parsing_rules(file=self.path)
        pass

    def type(self):
        return FileType.AGENT_CONFIG

    def _unify(self, dest_dir: Path) -> List[Path]:
        """Unify AgentConfig in destination dir.

        Args:
            dest_dir: Destination directory.

        Returns:
            List[Path]: List of new created files.
        """
        # Directory configuration - Integrations or Scripts
        unify_dir = ENTITY_TYPE_TO_DIR[FileType.AGENT_CONFIG.value]

        # Unify step
        unifier = AgentConfigUnifier(input=str(self.path.parent), output=dest_dir, dir_name=unify_dir, force=True)

        created_files: List[str] = unifier.unify()

        # Validate that unify succeed - there is no exception raised in unify module.
        if not created_files:
            raise exc.ContentDumpError(self, self.path, "Unable to unify Agent Config object")

        return [Path(path) for path in created_files]

    def dump(self, dest_dir: Optional[Union[Path, str]] = None, unify: bool = True) -> List[Path]:
        """
        Dump AgentConfig.

        Args:
            dest_dir: Destination directory.
            unify: True if dump as unify else dump as is.

        Returns:
            List[Path]: Path of new created files.
        """
        created_files: List[Path] = []

        # Handling case where object is not unified and dump should be unify.
        if unify:
            # Unify in dest dir.
            created_files.extend(self._unify(dest_dir))

        else:
            created_files.extend(super().dump(dest_dir=dest_dir))

        return created_files
