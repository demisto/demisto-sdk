import copy
from typing import List, Optional, Union

from demisto_sdk.commands.common.constants import SCRIPTS_DIR, INTEGRATIONS_DIR
from ...base_objects.dictionary_file_mixins import DictBaseFileMixin
from ...utils import normalize_file_name
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import YamlFile
from wcmatch.pathlib import EXTMATCH, Path

from demisto_sdk.commands.unify.unifier import Unifier
from .yaml_pack_mixins import YamlPackMixin


def unify_handler(source_dir: Path, dest_dir: Path) -> List[Path]:
    """Unify YAMLContentUnfiedObject in destination dir.

    Args:
        source_dir:
        file_type:
        dest_dir: Destination directory.

    Returns:
        List[Path]: List of new created files.
    """
    # Directory configuration - Integrations or Scripts
    unify_dir = SCRIPTS_DIR if SCRIPTS_DIR in source_dir.parts else INTEGRATIONS_DIR
    # Unify step
    unifier = Unifier(input=str(source_dir), dir_name=unify_dir, output=str(dest_dir), force=True)
    created_files: List[str] = unifier.merge_script_package_to_yml()
    # Validate that unify succeed - there is not exception raised in unify module.
    if not created_files:
        raise Exception()

    return [Path(path) for path in created_files]


def split_yaml_4_5_0(source_dir: Path, source_dict: dict) -> List[Path]:
    """Split YAMLContentUnfiedObject in destination dir.

    Args:
        source_dict:
        source_dir:
        file_type:

    Returns:
        List[Path]: List of new created files.

    Notes:
        1. If object contain docker_image_4_5 key with value -> should split to:
            a. <original_file>
            b. <original_file_name>_4_5.yml
    """
    # Directory configuration - Integrations or Scripts
    unify_dir = SCRIPTS_DIR if SCRIPTS_DIR in source_dir.parts else INTEGRATIONS_DIR
    # Split step
    unifier = Unifier(input=str(source_dir), dir_name=unify_dir, output=source_dir, force=True)
    source_dict_copy = copy.deepcopy(source_dict)
    script_values = source_dict if SCRIPTS_DIR in source_dir.parts else source_dict.get('script', {})
    created_files: List[str] = unifier.write_yaml_with_docker(source_dict_copy, source_dict, script_values).keys()
    # Validate that split succeed - there is not exception raised in unify module.
    if not created_files:
        raise Exception()

    return [Path(path) for path in created_files]


class YamlPackUnifyMixin(YamlPackMixin):
    @property
    def code_path(self: DictBaseFileMixin) -> Optional[Path]:
        """YAML related code path.

        Returns:
            Code path or None if code file not found.
        """
        patterns = [f"{self.path.stem}.@(ps1|js|py)"]
        return next(self.path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    @property
    def unittest_path(self: DictBaseFileMixin) -> Optional[Path]:
        """YAML related unit-test path.

        Returns:
            Unit-test path or None if unit-test not found.
        """
        patterns = ["test_*.py", "*_test.py"]
        return next(self.path.parent.glob(patterns=patterns), None)

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


class YamlPackUnifyDumpMixin:
    def dump(self: Union[DictBaseFileMixin, YamlPackUnifyMixin, YamlFile],
             dest_dir: Optional[Union[str, Path]] = None, readme: Optional[bool] = False, unify: bool = True,
             version_split: bool = True) -> List[Path]:
        """ Dump YAMLContentUnfiedObject.

        Args:
            version_split:
            dest_dir: Destination directory.
            readme: True if to dump also related README.md.
            unify: True if dump as unify else dump as is.

        Returns:
            List[Path]: Path of new created files.
        """
        created_files: List[Path] = []
        # Create directory and add prefix if not exists
        if not dest_dir:
            dest_dir = self.path.parent
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / normalize_file_name(file_name=self.path.name, file_prefix=self._prefix)

        # handle case where should be unified
        if unify and not self.is_unify():
            # If not unified -> Save old data a side -> serialize -> unify -> revert to old data
            old_data = self.path.read_bytes()
            self._serialize(dest_file)
            created_files.extend(unify_handler(source_dir=self.path.parent, dest_dir=dest_dir, file_type=type(self)))
            self.path.write_bytes(old_data)
        else:
            created_files.append(self._serialize(dest_file))

        # IF docker_4_5 exists split file to seprated files.
        if version_split and self.docker_image_4_5:
            created_files.extend(split_yaml_4_5_0(source_dir=self.path.parent, source_dict=self.__dict__(),
                                                  file_type=type(self)))
        # Dump readme if requested and availble
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))

        return created_files
