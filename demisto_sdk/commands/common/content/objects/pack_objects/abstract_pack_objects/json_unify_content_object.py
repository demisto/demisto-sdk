from demisto_sdk.commands.unify.generic_module_unifier import GenericModuleUnifier
from demisto_sdk.commands.common.constants import (GENERIC_MODULES_DIR, FileType)
from .json_content_object import JSONContentObject
from typing import List, Optional, Union
from wcmatch.pathlib import EXTMATCH, Path
import demisto_sdk.commands.common.content.errors as exc


class JsonContentUnifiedObject(JSONContentObject):
    def __init__(self, path: Union[Path, str], content_type: FileType, file_name_prefix: str):
        """JSON content object.

        Built from:
            1. JSONContentObject.
            2. Json file

        Args:
            content_type: Only 2 availble content types - Script / Integration. (Mandatory for init - Used for unify or split)
        """
        super().__init__(path, file_name_prefix)
        self._content_type = content_type



    @property
    def file_path(self) -> Optional[Path]:
        """JSON related file path.

        Returns:
            file path or None if file not found.
        """
        patterns = [f"{self.path.stem}.json"]
        return next(self._path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    def is_unify(self) -> bool:
        """Check if Content object is unified or not.

        Returns:
            bool: True if unified else False.
        """
        return self.code_path is None

    def _unify(self, dest_dir: Path) -> List[Path]:
        """Unify JSONContentUnfiedObject in destination dir.

        Args:
            dest_dir: Destination directory.

        Returns:
            List[Path]: List of new created files.
        """
        # Directory configuration - generic modules
        if self._content_type == FileType.GENERIC_MODULE:
            unify_dir = GENERIC_MODULES_DIR
        # Unify step
        unifier = GenericModuleUnifier(input=str(self.path.parent), dir_name=unify_dir, output=dest_dir, force=True)
        created_files: List[str] = unifier.merge_generic_module_with_its_dashboards()
        # Validate that unify succeed - there is not exception raised in unify module.
        if not created_files:
            raise exc.ContentDumpError(self, self.path, "Unable to unify object")

        return [Path(path) for path in created_files]

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, change_log: Optional[bool] = False,
                 readme: Optional[bool] = False, unify: bool = True) -> List[Path]:
        """ Dump JSONContentUnfiedObject.

        Args:
            dest_dir: Destination directory.
            change_log: True if to dump also related CHANGELOG.md.
            readme: True if to dump also related README.md.
            unify: True if dump as unify else dump as is.

        Returns:
            List[Path]: Path of new created files.
        """
        created_files: List[Path] = []
        dest_dir = self._create_target_dump_dir(dest_dir)

        # Handling case where object is not unified and dump should be unify.
        if unify:
            # Unify in dest dir.
            created_files.extend(self._unify(dest_dir))
            # Adding readme and changelog if requested.
            created_files.extend(super().dump(dest_dir=dest_dir,  change_log=change_log, readme=readme))
        return created_files