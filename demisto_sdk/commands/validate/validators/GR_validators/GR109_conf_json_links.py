from __future__ import annotations

from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)

ContentTypes = ConfJSON


class ConfJSONLinkValidator(BaseValidator[ContentTypes]):
    error_code = "GR109"
    description = (
        "Validates that all content items mentioned in conf.json exist in the repo."
    )
    error_message = f"Cannot find content object(s) mentioned in conf.json, with id(s) {0} in the repo."
    content_types = ContentTypes
    is_auto_fixable = False

    # def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
    #     graph_conf_json: ContentTypes = one(
    #         self.graph.search(
    #             object_id=one(content_items).object_id
    #         )  # type:ignore[assignment]
    #     )
    #     missing_objects = [
    #         relationship.content_item_to
    #         for relationship in itertools.chain.from_iterable(
    #             graph_conf_json.relationships_data.values()
    #         )
    #         if relationship.content_item_to.not_in_repository
    #     ]

    #     return [
    #         ValidationResult(
    #             validator=self,
    #             message=self.error_message.format(missing_object.object_id),
    #             content_object=graph_conf_json,
    #         )
    #         for missing_object in sorted(missing_objects, key=lambda o: o.object_id)
    #     ]
