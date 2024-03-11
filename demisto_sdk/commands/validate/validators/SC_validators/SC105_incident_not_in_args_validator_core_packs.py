from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_core_pack_list,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class IsScriptArgumentsContainIncidentWordValidatorCorePacks(
    BaseValidator[ContentTypes]
):
    error_code = "SC105"
    description = (
        "Checks that script arguments do not container the word incident in core packs"
    )
    rationale = (
        "Server has a feature where the word 'incident' in the system can be replaced by any other keyword of the user's choice. "
        "To ensure compatibility with this feature, we should make sure that command names, command arguments, "
        "and script arguments in core pack integrations and scripts do not use the word 'incident'. "
        "This helps maintain the flexibility of the system and prevents potential issues caused by keyword replacement."
    )
    error_message = "The following arguments {} contain the word incident, remove it"
    related_field = "args"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        core_packs = get_core_pack_list()

        invalid_content_items = []
        for content_item in content_items:
            pack = content_item.in_pack
            if pack:
                pack_name = pack.name
                wrong_arg_names = [
                    argument.name
                    for argument in content_item.args
                    if "incident" in argument.name
                    and not argument.deprecated
                    and pack_name in core_packs
                ]
                if wrong_arg_names:
                    invalid_content_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                ", ".join(wrong_arg_names)
                            ),
                            content_object=content_item,
                        )
                    )
            else:
                logger.error(
                    f"Could not get the pack of script {content_item.content_type} when validating {self.error_code}"
                )
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=f"Script {content_item.name} is not part of any pack, can not validate {self.error_code}",
                        content_object=content_item,
                    )
                )

        return invalid_content_items
