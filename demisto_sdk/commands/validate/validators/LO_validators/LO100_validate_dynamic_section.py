from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.tools import is_string_uuid
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.case_layout import CaseLayout
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Layout, CaseLayout]


class IsValidDynamicSectionValidator(BaseValidator[ContentTypes]):
    error_code = "LO100"
    description = (
        "Ensures that dynamic sections in the layout contains existing scripts."
    )
    rationale = "Section query value has to be a valid script name."
    error_message_uuid = "The tab {0} contains UUID value: {1} in the query field, please change it to valid script name."
    error_message_unknown_script = (
        "The tab {0} contains the following script that not exists in the repo: {1}."
    )
    related_field = "tabs.sections.query"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []

        for content_item, tab, section in (
            (content_item, tab, section)
            for content_item in content_items
            for layout_data in content_item.data.values()
            if isinstance(layout_data, dict)
            for tab in layout_data.get("tabs", [])
            for section in tab.get("sections", [])
            if section.get("query")
        ):
            # get the query value
            query = section["query"]
            if isinstance(query, str) and ":" not in query:
                # check if the query value is UUID
                if is_string_uuid(query):
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message_uuid.format(
                                tab.get("name", ""), query
                            ),
                            content_object=content_item,
                        )
                    )
                    continue
                # check if the query value is valid script name
                script_found = self.graph.search(
                    object_id=query,
                    content_type=ContentType.SCRIPT,
                )

                if not script_found:
                    validation_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message_unknown_script.format(
                                tab.get("name", ""), query
                            ),
                            content_object=content_item,
                        )
                    )

        return validation_results
