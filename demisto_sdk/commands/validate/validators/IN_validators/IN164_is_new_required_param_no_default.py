from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsNewRequiredParamNoDefaultIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN164"
    description = "Ensure that new *required* parameters added to an existing integration must have a default value."
    rationale = (
        "Adding a new required parameter or changing a non-required one to required without specifying a "
        "default value breaks backward compatibility and will prevent users from upgrading their "
        "integration instances."
    )
    error_message = (
        "Possible backward compatibility break: "
        "You have added the following new *required* parameters: {param_list}. "
        "Please undo the changes or provide default values. If cannot give default value, "
        "please make the parameter not required and check in code implementation that it was configured."
    )
    related_field = "configuration"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            # If there is no old content item, this is a new integration so there is no issue creating a required param
            if not old_content_item:
                continue

            new_required_params_with_no_default = [
                param.name
                for param in content_item.params
                if param.required
                and not param.defaultvalue  # And ensure no default value
                # If it is a required param with no default, check if it was required before
                and not self._param_was_required_before(param, old_content_item)
            ]

            if new_required_params_with_no_default:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            param_list=", ".join(new_required_params_with_no_default)
                        ),
                        content_object=content_item,
                    )
                )

        return results

    def _param_was_required_before(
        self, required_param: Parameter, old_content_item: BaseContent
    ) -> bool:
        """
        Check if this parameter was already required in the old version.
        """

        # Find the parameter in the old version by name
        for old_param in old_content_item.params:  # type: ignore
            if old_param.name == required_param.name:
                return old_param.required

        # Parameter didn't exist before, so it's new
        return False
