from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


def title_to_slug(title: str) -> str:
    """Derive a connector id slug from its human title.

    Mirrors ``manifest_generator.title_to_slug`` (the canonical UCP mapping
    used when connectors are generated): lowercase the title, replace spaces
    with dashes, then collapse any resulting triple-dash run to a single dash.

    Examples:
        "Cisco Security"                 -> "cisco-security"
        "AWS - S3"                       -> "aws-s3"  (``" - "`` -> ``"---"`` -> ``"-"``)
        "Atlassian Automation and Collection"
            -> "atlassian-automation-and-collection"
    """
    return title.strip().lower().replace(" ", "-").replace("---", "-")


class IsConnectorIdTitleAlignedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO103"
    description = (
        "Validates that a connector's id and metadata.title encode the same "
        "name, i.e. slugify(title) == id."
    )
    rationale = (
        "The connector id is the lowercase-dashes slug of its Title Case "
        "metadata.title (per the UCP slugify rules used by the manifest "
        "generator). An id that does not match the slugified title indicates "
        "the two fields have drifted apart."
    )
    error_message = (
        "Connector id '{connector_id}' does not match the slugified "
        "metadata.title '{title}'. Expected id '{expected_id}'."
    )
    related_field = "id"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            title = connector.connector_metadata.title or ""
            expected_id = title_to_slug(title)
            if connector.object_id != expected_id:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            title=title,
                            expected_id=expected_id,
                        ),
                        content_object=connector,
                    )
                )

        return results
