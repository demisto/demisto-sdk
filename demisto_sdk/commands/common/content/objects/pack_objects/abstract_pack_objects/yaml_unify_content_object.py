import copy
from typing import List, Optional, Union

from wcmatch.pathlib import EXTMATCH, Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import (INTEGRATIONS_DIR,
                                                   SCRIPTS_DIR, FileType)
from demisto_sdk.commands.unify.yml_unifier import YmlUnifier

from .yaml_content_object import YAMLContentObject


class YAMLContentUnifiedObject(YAMLContentObject):
    def __init__(self, path: Union[Path, str], content_type: FileType, file_name_prefix: str):
        """YAML content object.

        Built from:
            1. YAMLContentObject.
            2. Code file - python/powershell/javascript.
            3. Unit-tests file.

        Args:
            content_type: Only 2 availble content types - Script / Integration. (Mandatory for init - Used for unify or split)
        """
        super().__init__(path, file_name_prefix)
        self._content_type = content_type

    @property
    def code_path(self) -> Optional[Path]:
        """YAML related code path.

        Returns:
            Code path or None if code file not found.
        """
        patterns = [f"{self.path.stem}.@(ps1|js|py)"]
        return next(self._path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    @property
    def unittest_path(self) -> Optional[Path]:
        """YAML related unit-test path.

        Returns:
            Unit-test path or None if unit-test not found.
        """
        patterns = ["test_*.py", "*_test.py"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def script(self) -> dict:
        """Script item in object dict:
            1. Script - Loacted under main keys.
            2. Integration - Located under second level key (script -> script).
        """
        if self._content_type == FileType.INTEGRATION:
            script = self.get('script', {})
        else:
            script = self.to_dict()

        return script

    @property
    def docker_image(self) -> str:
        """Object docker_image attribute.

        Returns:
            str: docker image name.

        References:
            1. Attribute info - https://xsoar.pan.dev/docs/integrations/docker#why-use-docker
        """
        return self.script.get('dockerimage', '')

    @property
    def docker_image_4_5(self) -> str:
        """Object docker_image_4_5 attribute.

        Returns:
            str: docker image name.

        References:
            1. Attribute info - https://xsoar.pan.dev/docs/integrations/docker#why-use-docker
        """
        return self.script.get('dockerimage45', '')

    def is_unify(self) -> bool:
        """Check if Content object is unified or not.

        Returns:
            bool: True if unified else False.
        """
        return self.code_path is None

    def _unify(self, dest_dir: Path) -> List[Path]:
        """Unify YAMLContentUnfiedObject in destination dir.

        Args:
            dest_dir: Destination directory.

        Returns:
            List[Path]: List of new created files.

        TODO:
            1. Add Exception raising in unify module.
            2. Verbosity to quiet mode option in unify module.
        """
        # Directory configuration - Integrations or Scripts
        unify_dir = SCRIPTS_DIR if self._content_type == FileType.SCRIPT else INTEGRATIONS_DIR
        # Unify step
        unifier = YmlUnifier(input=str(self.path.parent), dir_name=unify_dir, output=dest_dir, force=True)
        created_files: List[str] = unifier.merge_script_package_to_yml()
        # Validate that unify succeed - there is not exception raised in unify module.
        if not created_files:
            raise exc.ContentDumpError(self, self.path, "Unable to unify object")

        return [Path(path) for path in created_files]

    def _split_yaml_4_5_0(self, dest_dir: Path) -> List[Path]:
        """Split YAMLContentUnfiedObject in destination dir.

        Args:
            dest_dir: Destination directory.

        Returns:
            List[Path]: List of new created files.

        Notes:
            1. If object contain docker_image_4_5 key with value -> should split to:
                a. <original_file>
                b. <original_file_name>_4_5.yml

        TODO:
            1. Add Exception raising in unify module.
            2. Verbosity to quiet mode option in unify module.
        """
        # Directory configuration - Integrations or Scripts
        unify_dir = SCRIPTS_DIR if self._content_type == FileType.SCRIPT else INTEGRATIONS_DIR
        # Split step
        unifier = YmlUnifier(input=str(self.path.parent), dir_name=unify_dir, output=str(dest_dir / self.path.name),
                             force=True)
        yaml_dict = self.to_dict()
        yaml_dict_copy = copy.deepcopy(yaml_dict)
        script_object = self.script
        created_files: List[str] = unifier.write_yaml_with_docker(yaml_dict_copy, yaml_dict, script_object).keys()
        # Validate that split succeed - there is not exception raised in unify module.
        if not created_files:
            raise exc.ContentDumpError(self, self.path, "Unable to split object")

        return [Path(path) for path in created_files]

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, change_log: Optional[bool] = False,
             readme: Optional[bool] = False, unify: bool = True) -> List[Path]:
        """ Dump YAMLContentUnfiedObject.

        Args:
            dest_dir: Destination directory.
            change_log: True if to dump also related CHANGELOG.md.
            readme: True if to dump also related README.md.
            unify: True if dump as unify else dump as is.

        Returns:
            List[Path]: Path of new created files.

        TODO:
            1. Handling case where object changed and need to be serialized.
            2. Specific handling if unified and unit-tests or code.
        """
        created_files: List[Path] = []
        dest_dir = self._create_target_dump_dir(dest_dir)

        # Handling case where object is not unified and dump should be unify.
        if unify and not self.is_unify():
            # Unify in dest dir.
            created_files.extend(self._unify(dest_dir))
            # Adding readme and changelog if requested.
            created_files.extend(super().dump(dest_dir=dest_dir, yaml=False,
                                              readme=readme, change_log=change_log))

        # Handling case where object is unified
        else:
            # Handling case where object include docker_image_4_5, In that case should split the file to:
            #   1. <original_file>
            #   2. <original_file_name>_4_5.yml
            if self.docker_image_4_5:
                # Split file as described above.
                created_files.extend(self._split_yaml_4_5_0(dest_dir))
                # Adding readme and changelog if requested.
                created_files.extend(super().dump(dest_dir=dest_dir, yaml=False,
                                                  readme=readme, change_log=change_log))

            # Handling case where copy of object should be without modifications.
            else:
                # Dump as YAMLContentObject
                created_files.extend(super().dump(dest_dir=dest_dir,
                                                  readme=readme, change_log=change_log))

        return created_files
