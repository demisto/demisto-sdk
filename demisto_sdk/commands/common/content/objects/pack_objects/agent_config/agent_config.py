from typing import List, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import (AGENT_CONFIG,
                                                   ENTITY_TYPE_TO_DIR,
                                                   FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
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

    def _unify(self, dest_dir: Path = None) -> List[Path]:
        """Unify AgentConfig in destination dir.

        Args:
            dest_dir: Destination directory.

        Returns:
            List[Path]: List of new created files.
        """

        unify_dir = ENTITY_TYPE_TO_DIR[FileType.AGENT_CONFIG.value]

        # Unify step
        unifier = AgentConfigUnifier(input=str(self.path.parent), output=dest_dir, dir_name=unify_dir)

        created_files: List[str] = unifier.unify()

        # Validate that unify succeed - there is no exception raised in unify module.
        if not created_files:
            raise exc.ContentDumpError(self, self.path, "Unable to unify Agent Config object")

        return [Path(path) for path in created_files]

    def _create_target_dump_dir(self, dest_dir: Optional[Union[Path, str]] = None) -> Path:
        """Create destination directory, Destination must be valid directory, If not specified dump in
         path of origin object.

        Args:
            dest_dir: destination directory to dump object.

        Returns:
            Path: Destionaion directory.

        Raises:
            DumpContentObjectError: If not valid directory path - not directory or not exists.
        """
        if dest_dir:
            dest_dir = Path(dest_dir)
            if dest_dir.exists() and not Path(dest_dir).is_dir():
                raise exc.ContentDumpError(self, self._path, "Destiantion is not valid directory path")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            dest_dir = self._path.parent

        return dest_dir

    def dump(self, dest_dir: Optional[Union[Path, str]] = None, unify: bool = True) -> List[Path]:
        """
        Dump AgentConfig.

        Args:
            dest_dir: Destination directory.
            unify: True if dump as unify else dump as is.

        Returns:
            List[Path]: Path of new created files.
        """
        dest_dir = self._create_target_dump_dir(dest_dir)

        created_files: List[Path] = []
        # Handling case where object is not unified and dump should be unify.
        if unify:
            # Unify in dest dir.
            created_files.extend(self._unify(dest_dir))

        else:
            created_files.extend(super().dump(dest_dir=dest_dir))

        return created_files
