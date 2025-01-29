from __future__ import annotations

from typing import Iterable, List, Union

import click

from demisto_sdk.commands.common.constants import DOC_FILE_FULL_IMAGE_REGEX
from demisto_sdk.commands.common.tools import (
    extract_image_paths_from_str,
    get_pack_name,
)
from demisto_sdk.commands.content_graph.objects import Pack
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]


class IsImageExistsInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM114"
    description = (
        "Validate that images placed under doc_files folder and used in README exist."
    )
    error_message = "The following images do not exist or have additional characters present in their declaration within the README: {0}"
    rationale = "Missing images are not shown in rendered markdown"
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_lines)),
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (
                any(
                    invalid_lines := self.get_invalid_image_paths(
                        get_pack_name(content_item.path),
                        extract_image_paths_from_str(
                            text=content_item.readme.file_content,
                            regex_str=DOC_FILE_FULL_IMAGE_REGEX,
                        ),
                    )
                )
            )
        ]

    @staticmethod
    def get_invalid_image_paths(pack_name: str, image_paths: List[str]) -> List[str]:
        """
        Args:
            pack_name (str): Pack name to add to path.
            image_paths (List[Path]): List of images with a local path under the doc_files folder. For example: ![<title>](../doc_files/<image name>.png)

        Returns:
            List[Path]: A list of invalid image files full paths.
        """
        path_validate = click.Path(exists=True, dir_okay=False)

        invalid_image_paths = []
        for image_path in image_paths:
            try:
                if "Packs" not in image_path:
                    image_path = f"Packs/{pack_name}/{image_path.replace('../', '')}"
                path_validate.convert(image_path, param=None, ctx=None)

            except click.exceptions.BadParameter:
                try:
                    alternative_path = image_path.removeprefix("Packs/")
                    path_validate.convert(alternative_path, param=None, ctx=None)
                except click.exceptions.BadParameter:
                    invalid_image_paths.append(image_path)

        return invalid_image_paths
