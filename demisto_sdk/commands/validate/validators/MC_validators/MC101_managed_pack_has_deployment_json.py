from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import DEPLOYMENT_JSON_FILENAME
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.tools import get_platform_managed_and_source
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class ManagedPackHasDeploymentJsonValidator(BaseValidator[ContentTypes]):
    error_code = "MC101"
    description = (
        "Validate that managed packs have a deployment.json file in the pack folder."
    )
    rationale = (
        "Packs with pack_metadata managed: true must include a deployment.json file "
        "in the pack folder to define deployment configuration."
    )
    error_message = (
        "The pack is managed (managed: true in pack_metadata) "
        "but is missing a 'deployment.json' file in the pack folder."
    )
    related_field = "managed"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            if not is_managed_pack_with_deployment_json(content_item):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message,
                        content_object=content_item,
                    )
                )
        return results


def is_managed_pack_with_deployment_json(pack: ContentTypes) -> bool:
    """
    Check if a managed pack has a deployment.json file in its folder.

    The managed check is resolved for the PLATFORM marketplace only: the pack is
    considered managed when its platform-specific ``managed`` (``managed:platform``
    if present, otherwise the plain ``managed``) is true.

    Args:
        pack: The pack to validate.

    Returns:
        bool: True if the pack is valid (either not managed for platform, or
              managed and has deployment.json), False if the pack is managed for
              platform but missing deployment.json.
    """
    managed, _ = get_platform_managed_and_source(pack)
    if not managed:
        # Not a managed pack for the platform marketplace — no deployment.json required
        return True

    deployment_json_path = pack.path / DEPLOYMENT_JSON_FILENAME
    return deployment_json_path.exists()
