from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


def title_to_slug(title: str) -> str:
    """Derive a connector id slug from its human title.

    Mirrors the canonical UCP mapping used when grouped connectors are
    generated. Rules (verified against every grouped connector in the UCP
    repo):

    1. Lowercase the title.
    2. Strip parentheses ``(`` / ``)`` entirely.
    3. Replace spaces with dashes.
    4. Collapse any run of dashes into a single dash, and trim leading/
       trailing dashes.

    Examples:
        "Cisco Security"                 -> "cisco-security"
        "AWS - S3"                       -> "aws-s3"
        "Trellix Endpoint (HX)"          -> "trellix-endpoint-hx"
        "SaaS Security (Aperture)"       -> "saas-security-aperture"
        "Atlassian Automation and Collection"
            -> "atlassian-automation-and-collection"
    """
    s = title.strip().lower()
    # Rule 2: parentheses are removed (space collapse handled by rule 4).
    s = s.replace("(", "").replace(")", "")
    # Rule 3: spaces -> dashes.
    s = s.replace(" ", "-")
    # Rule 4: collapse dash runs + trim.
    s = re.sub(r"-+", "-", s).strip("-")
    return s


class IsConnectorIdTitleAlignedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO103"
    description = (
        "Validates that a grouped connector's id and metadata.title encode "
        "the same name, i.e. slugify(title) == id."
    )
    rationale = (
        "A grouped connector's id is the lowercase-dashes slug of its Title "
        "Case metadata.title (per the UCP slugify rules used by the manifest "
        "generator: lowercase, strip parentheses, spaces to dashes, collapse "
        "dash runs). An id that does not match the slugified title indicates "
        "the two fields have drifted apart."
    )
    error_message = (
        "Connector id '{connector_id}' does not match the slugified "
        "metadata.title '{title}'. Expected id '{expected_id}'."
    )
    related_field = "id"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]

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
