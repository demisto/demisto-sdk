from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration

REDUNDANT_SUDDEN_DEATH_ERROR_MESSAGE = (
    "An incremental feed should not have the "
    "suddenDeath option as an expiration policy."
)
MISSING_SUDDEN_DEATH_ERROR_MESSAGE = (
    "The feed's expiration policy does not contain the suddenDeath option. "
    "Either add this option or mark feed as incremental."
)
BAD_TYPE_OR_DISPLAY = (
    "The feed's expiration policy type must be 17 and display must be an empty string."
)
MISSING_EXPIRATION_POLICY = "Missing feedExpirationPolicy parameter."
EXPIRATION_POLICY_PARAMETER_TYPE_NUMBER = 17
INCREMENTAL_FEED_PARAMETER_TYPE_NUMBER = 8


def is_sudden_death(expiration_policy: Parameter):
    return expiration_policy.options and "suddenDeath" in expiration_policy.options


class IsValidFeedExpirationPolicyValidator(BaseValidator[ContentTypes]):
    error_code = "IN163"
    description = (
        "Validate feedExpirationPolicy parameter is in the right format"
        "for both incremental and fully fetched feeds"
    )
    rationale = (
        "Malformed expiration policy can lead to errors or incomplete data."
        "For more details, see https://xsoar.pan.dev/docs/integrations/feeds"
    )
    error_message = "The feed's expiration policy is not in the correct format."
    related_field = "feedExpirationPolicy"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        invalid_content_items = []

        for content_item in content_items:
            if not content_item.is_feed:
                continue

            incremental_feed_param = next(
                (
                    param
                    for param in content_item.params
                    if param.name == "feedIncremental"
                    and param.hidden
                    and param.type == INCREMENTAL_FEED_PARAMETER_TYPE_NUMBER
                    and param.defaultvalue
                ),
                None,
            )

            expiration_policy = next(
                (
                    param
                    for param in content_item.params
                    if param.name == "feedExpirationPolicy"
                ),
                None,
            )

            elaborate_error_message = ""

            if not expiration_policy:
                elaborate_error_message = MISSING_EXPIRATION_POLICY

            elif (
                expiration_policy.display != ""
                or expiration_policy.type != EXPIRATION_POLICY_PARAMETER_TYPE_NUMBER
            ):
                elaborate_error_message = BAD_TYPE_OR_DISPLAY

            elif incremental_feed_param and is_sudden_death(expiration_policy):
                elaborate_error_message = REDUNDANT_SUDDEN_DEATH_ERROR_MESSAGE

            elif not incremental_feed_param and not is_sudden_death(expiration_policy):
                elaborate_error_message = MISSING_SUDDEN_DEATH_ERROR_MESSAGE

            if elaborate_error_message:
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message + " " + elaborate_error_message,
                        content_object=content_item,
                    )
                )

        return invalid_content_items
