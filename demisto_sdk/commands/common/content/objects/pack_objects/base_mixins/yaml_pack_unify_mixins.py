from typing import List, Optional, Union

from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import \
    YamlFile
from wcmatch.pathlib import EXTMATCH, Path

from ...utils import normalize_file_name, split_yaml_4_5_0, unify_handler
from .yaml_pack_mixins import YamlPackReamdeMixin


class YamlPackUnifyFilesMixin:
    @property
    def code_path(self: YamlFile) -> Optional[Path]:
        """YAML related code path.

        Returns:
            Code path or None if code file not found.
        """
        patterns = [f"{self.path.stem}.@(ps1|js|py)"]
        return next(self.path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    @property
    def unittest_path(self: YamlFile) -> Optional[Path]:
        """YAML related unit-test path.

        Returns:
            Unit-test path or None if unit-test not found.
        """
        patterns = ["test_*.py", "*_test.py"]
        return next(self.path.parent.glob(patterns=patterns), None)

    def is_unify(self) -> bool:
        """Check if Content object is unified or not.

        Returns:
            bool: True if unified else False.
        """
        return self.code_path is None


class YamlPackUnifyDockerImages:
    @property
    def script(self: YamlFile) -> dict:
        """Script item in object dict:
            1. Script - Loacted under main keys.
            2. Integration - Located under second level key (script -> script).
        """
        if INTEGRATIONS_DIR in self.path.parts:
            script = self.get('script', {})
        else:
            script = self.__dict__()

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


class YamlPackUnifyDumpMixin:
    def dump(self: Union[YamlFile, YamlPackUnifyFilesMixin, YamlPackReamdeMixin, YamlPackUnifyDockerImages],
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
            created_files.extend(unify_handler(source_dir=self.path.parent, dest_dir=dest_dir))
            self.path.write_bytes(old_data)
        else:
            created_files.append(self._serialize(dest_file))

        # IF docker_4_5 exists split file to seprated files.
        if version_split and self.docker_image_4_5:
            created_files.extend(split_yaml_4_5_0(source_dir=self.path.parent, source_dict=self.__dict__()))
        # Dump readme if requested and availble
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))

        return created_files
