from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.constants import FEED_REQUIRED_PARAMS
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.tools import find_param
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidFeedIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN122"
    description = (
        "Validate that all existing params are in the right format for feed params."
    )
    rationale = (
        "Malformed or missing parameters can lead to errors or incomplete data. "
        "For more details, see https://xsoar.pan.dev/docs/integrations/feeds"
    )
    error_message = "The integration is a feed integration with malformed params: {0}"
    related_field = "configuration"
    invalid_params: ClassVar[Dict[str, Dict[str, Dict]]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"The param '{key}' should be in the following structure: {self.create_param_structure(value)}"
                            for key, value in invalid_params.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_feed
            and (
                invalid_params := self.get_invalid_feed_params(
                    content_item.name, content_item.params
                )
            )
        ]

    def create_param_structure(self, value: dict) -> str:
        """Create a msg that reflects the required param template.

        Args:
            value (dict): The missing / malformed param fields.

        Returns:
            str: The param template.
        """
        msg = ""
        if must_equal := value.get("must_equal"):
            for key, val in must_equal.items():
                msg = f"{msg}\n\tThe field '{key}' must be equal '{val}'."
        if must_contain := value.get("must_contain"):
            for key, val in must_contain.items():
                msg = f"{msg}\n\tThe field '{key}' must appear and contain '{val}'."
        if must_be_one_of := value.get("must_be_one_of"):
            for key, val in must_be_one_of.items():
                msg = f"{msg}\n\tThe field '{key}' must be one of the following {', '.join(val['options'])}."
        return msg

    def get_invalid_feed_params(
        self, integration_name: str, params: List[Parameter]
    ) -> Dict[str, Dict]:
        """Collect the malformed feed params.

        Args:
            integration_name (str): The name of the current integration to validate.
            params (List[dict]): The list of the integration params.

        Returns:
            Dict[str, Dict]: The invalid params by name: structure.
        """
        invalid_params = {}
        for required_param in FEED_REQUIRED_PARAMS:
            if current_param := find_param(params, required_param.get("name", "")):  # type: ignore[arg-type]
                equal_key_values: dict = required_param.get("must_equal", dict())  # type: ignore[assignment]
                contained_key_values: dict = required_param.get("must_contain", dict())  # type: ignore[assignment]
                must_be_one_of: dict = required_param.get("must_be_one_of", list())  # type: ignore[assignment]
                param_details = current_param.dict()
                if not all(
                    [
                        (
                            any(
                                k in param_details and param_details[k] in v
                                for k, v in must_be_one_of.items()
                            )
                            or not must_be_one_of
                        ),
                        all(
                            k in param_details and param_details[k] == v
                            for k, v in equal_key_values.items()
                        ),
                        all(
                            k in param_details and v in param_details[k]
                            for k, v in contained_key_values.items()
                        ),
                    ]
                ):
                    invalid_params[current_param.name] = {
                        "must_equal": equal_key_values,
                        "must_contain": contained_key_values,
                        "must_be_one_of": must_be_one_of,
                    }
        self.invalid_params[integration_name] = invalid_params
        return invalid_params
