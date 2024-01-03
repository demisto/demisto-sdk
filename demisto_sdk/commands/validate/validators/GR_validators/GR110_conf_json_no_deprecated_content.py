from __future__ import annotations

import itertools
from typing import Iterable, List

from more_itertools import one

from demisto_sdk.commands.content_graph.objects.conf_json import ConfJson
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ConfJson


class ConfJSONLinkValidator(BaseValidator[ContentTypes]):
    error_code = "GR110"
    description = (
        "Validates that all content items mentioned in conf.json are not deprecated."
    )
    error_message = f"{0} is deprecated, remove it from conf.json"
    content_types = ContentTypes
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        graph_conf_json: ContentTypes = one(
            self.graph.search(
                object_id=one(content_items).object_id
            )  # type:ignore[assignment]
        )
        deprecated_objects = [
            relationship.content_item_to
            for relationship in itertools.chain.from_iterable(
                graph_conf_json.relationships_data.values()
            )
            if (
                isinstance(
                    relationship.content_item_to, ContentItem
                )  # TODO is this the best class to check against?
                and relationship.content_item_to.deprecated
            )
        ]

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(missing_object.object_id),
                content_object=missing_object,
            )
            for missing_object in sorted(deprecated_objects, key=lambda o: o.object_id)
        ]
