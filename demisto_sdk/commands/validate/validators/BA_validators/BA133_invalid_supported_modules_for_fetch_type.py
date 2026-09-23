from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, Iterable, List, Optional, Set

from demisto_sdk.commands.common.constants import (
    XSIAM_AND_AGENTIX_MODULES,
    XSIAM_AND_EXPOSURE_MANAGEMENT_MODULES,
    XSIAM_ONLY_MODULES,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import (
    get_content_item_supported_modules,
    get_parameter_supported_modules,
)
from demisto_sdk.commands.content_graph.objects.integration import (
    Integration,
    Parameter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration

MAX_FETCH_PARAM = "max_fetch"
# Fetch Credentials has no top-level flag; it is active when this param exists.
IS_FETCH_CREDENTIALS_PARAM = "isFetchCredentials"

# Default field templates used by the auto-fix when adding a missing required param.
SERVER_LEVEL_PARAM_TEMPLATES: Dict[str, Dict] = {
    "isFetch": {
        "display": "Fetch incidents",
        "type": 8,
        "required": False,
        "section": "Collect",
    },
    "incidentType": {
        "display": "Incident type",
        "type": 13,
        "required": False,
        "section": "Collect",
    },
    "incidentFetchInterval": {
        "display": "Incidents Fetch Interval",
        "type": 19,
        "required": False,
        "defaultvalue": "1",
        "advanced": True,
        "section": "Collect",
    },
    "isFetchEvents": {
        "display": "Fetch events",
        "type": 8,
        "required": False,
        "section": "Collect",
        "hidden": ["xsoar"],
    },
    "eventFetchInterval": {
        "display": "Events Fetch Interval",
        "type": 19,
        "required": False,
        "defaultvalue": "1",
        "advanced": True,
        "section": "Collect",
        "hidden": ["xsoar"],
    },
    "isFetchAssets": {
        "display": "Fetch assets and vulnerabilities",
        "type": 8,
        "required": False,
        "section": "Collect",
        "hidden": ["xsoar"],
    },
    "assetsFetchInterval": {
        "display": "Assets and vulnerabilities fetch interval",
        "type": 19,
        "required": False,
        "advanced": True,
        "section": "Collect",
        "defaultvalue": "1440",
        "hidden": ["xsoar"],
    },
    "feed": {
        "display": "Fetch indicators",
        "type": 8,
        "required": False,
        "defaultvalue": "true",
        "section": "Collect",
    },
    "feedReliability": {
        "display": "Source Reliability",
        "type": 15,
        "required": True,
        "additionalinfo": "Reliability of the source providing the intelligence data",
        "defaultvalue": "F - Reliability cannot be judged",
        "options": [
            "A - Completely reliable",
            "B - Usually reliable",
            "C - Fairly reliable",
            "D - Not usually reliable",
            "E - Unreliable",
            "F - Reliability cannot be judged",
        ],
        "section": "Collect",
    },
    "feedReputation": {
        "display": "Indicator Reputation",
        "type": 18,
        "required": False,
        "additionalinfo": "Indicators from this integration instance will be marked with this reputation",
        "defaultvalue": "Bad",
        "options": ["None", "Good", "Suspicious", "Bad"],
        "section": "Collect",
    },
    "feedFetchInterval": {
        "display": "Feed Fetch Interval",
        "type": 19,
        "required": False,
        "defaultvalue": "240",
        "section": "Collect",
    },
    "feedExpirationPolicy": {
        "display": "",
        "type": 17,
        "required": False,
        "options": ["never", "interval", "indicatorType", "suddenDeath"],
        "section": "Collect",
    },
    "feedExpirationInterval": {
        "display": "",
        "type": 1,
        "required": False,
        "defaultvalue": "20160",
        "section": "Collect",
    },
    "feedBypassExclusionList": {
        "display": "Bypass exclusion list",
        "type": 8,
        "required": False,
        "additionalinfo": "When selected, the exclusion list is ignored for indicators from this feed.",
        "section": "Collect",
    },
    "feedTags": {
        "display": "Tags",
        "type": 0,
        "required": False,
        "additionalinfo": "Supports CSV values.",
        "section": "Collect",
    },
    "tlp_color": {
        "display": "Traffic Light Protocol Color",
        "type": 15,
        "required": False,
        "additionalinfo": "The Traffic Light Protocol (TLP) designation to apply to indicators fetched from the feed",
        "options": ["RED", "AMBER+STRICT", "AMBER", "GREEN", "CLEAR"],
        "defaultvalue": "CLEAR",
        "section": "Collect",
    },
}


@dataclass(frozen=True)
class FetchType:
    """A fetch type and the configuration parameters associated with it."""

    display_name: str
    allowed_modules: Set[str]
    required_params: Set[str] = field(default_factory=set)
    optional_params: Set[str] = field(default_factory=set)
    flag_attr: Optional[str] = None
    activation_param: Optional[str] = None

    @property
    def all_params(self) -> Set[str]:
        return self.required_params | self.optional_params

    def is_active(self, content_item: ContentTypes, param_names: Set[str]) -> bool:
        """Whether the fetch type is active (via top-level flag or activation param)."""
        if self.flag_attr is not None:
            return bool(getattr(content_item, self.flag_attr, False))
        if self.activation_param is not None:
            return self.activation_param in param_names
        return False


FETCH_TYPES: List[FetchType] = [
    FetchType(
        flag_attr="is_fetch",
        display_name="Fetch Incidents",
        allowed_modules=XSIAM_AND_AGENTIX_MODULES,
        required_params={"isFetch", "incidentFetchInterval", "incidentType"},
        optional_params={MAX_FETCH_PARAM},
    ),
    FetchType(
        flag_attr="is_fetch_events",
        display_name="Fetch Events",
        allowed_modules=XSIAM_ONLY_MODULES,
        required_params={"isFetchEvents", "eventFetchInterval"},
        optional_params={MAX_FETCH_PARAM},
    ),
    FetchType(
        flag_attr="is_fetch_assets",
        display_name="Fetch Assets",
        allowed_modules=XSIAM_AND_EXPOSURE_MANAGEMENT_MODULES,
        required_params={"isFetchAssets", "assetsFetchInterval"},
    ),
    FetchType(
        flag_attr="is_feed",
        display_name="Fetch Indicators",
        allowed_modules=XSIAM_AND_AGENTIX_MODULES,
        required_params={
            "feed",
            "feedReliability",
            "feedReputation",
            "feedFetchInterval",
            "feedExpirationPolicy",
            "feedExpirationInterval",
            "feedBypassExclusionList",
            "feedTags",
            "tlp_color",
        },
        optional_params={"feedIncremental", "first_fetch"},
    ),
    FetchType(
        activation_param=IS_FETCH_CREDENTIALS_PARAM,
        display_name="Fetch Credentials",
        allowed_modules=XSIAM_AND_AGENTIX_MODULES,
        optional_params={
            IS_FETCH_CREDENTIALS_PARAM,
            "credential_names",
            "credentialNames",
            "secrets",
        },
    ),
]


@dataclass
class FixPlan:
    """The per-integration auto-fix plan.

    params_to_add: required params missing from the YAML -> modules to create them with.
    cleaned_modules_by_param: existing param -> modules to keep after removing un-allowed ones.
    """

    params_to_add: Dict[str, List[str]] = field(default_factory=dict)
    cleaned_modules_by_param: Dict[str, List[str]] = field(default_factory=dict)


class InvalidSupportedModulesForFetchTypeValidator(BaseValidator[ContentTypes]):
    error_code = "BA133"
    description = (
        "Validates that the fetch-related configuration parameters in an "
        "integration exist as required by their fetch type and resolve to "
        "'supportedModules' that are consistent with that fetch type."
    )
    rationale = (
        "Each fetch type is only available under a specific set of platform "
        "modules and requires a specific set of configuration parameters. A "
        "fetch-related parameter must exist when required, and resolve to a "
        "'supportedModules' set that is a subset of the modules allowed for its "
        "fetch type."
    )
    error_message = (
        "The configuration parameter '{0}' in '{1}' resolves to the following "
        "supported modules that are not allowed for its fetch type: {2}. "
        "The allowed modules for this parameter are: {3}."
    )
    missing_param_message = (
        "The required configuration parameter '{0}' for fetch type '{1}' is "
        "missing in '{2}'."
    )
    fix_message = "Fixed the following fetch-related parameters in '{0}': {1}."
    related_field = "supportedModules"
    is_auto_fixable = True
    fix_plans: ClassVar[Dict[str, FixPlan]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Validate the fetch-related parameters of each integration.

        Args:
            content_items (Iterable[ContentTypes]): The integrations to validate.

        Returns:
            List[ValidationResult]: One result per missing required parameter and
            per parameter resolving to disallowed modules.
        """
        results: List[ValidationResult] = []

        for content_item in content_items:
            # supportedModules are only meaningful for platform integrations.
            if MarketplaceVersions.PLATFORM not in content_item.marketplaces:
                continue

            param_names = {param.name for param in content_item.params}
            active_fetch_types = [
                fetch_type
                for fetch_type in FETCH_TYPES
                if fetch_type.is_active(content_item, param_names)
            ]
            if not active_fetch_types:
                continue

            allowed_by_param = self._build_allowed_modules_by_param(active_fetch_types)
            fix_plan = FixPlan()
            messages = self._collect_missing_required_messages(
                content_item, active_fetch_types, allowed_by_param, fix_plan
            ) + self._collect_invalid_module_messages(
                content_item, allowed_by_param, fix_plan
            )

            if messages:
                self.fix_plans[content_item.object_id] = fix_plan
                results.extend(
                    ValidationResult(
                        validator=self,
                        message=message,
                        content_object=content_item,
                    )
                    for message in messages
                )

        return results

    def _collect_missing_required_messages(
        self,
        content_item: ContentTypes,
        active_fetch_types: List[FetchType],
        allowed_by_param: Dict[str, Set[str]],
        fix_plan: FixPlan,
    ) -> List[str]:
        """Collect a message per required server-level param missing from the YAML.

        Args:
            content_item (ContentTypes): The integration to inspect.
            active_fetch_types (List[FetchType]): The integration's active fetch types.
            allowed_by_param (Dict[str, Set[str]]): Param name -> allowed modules.
            fix_plan (FixPlan): Populated with the params to add.

        Returns:
            List[str]: The missing-required error messages.
        """
        existing_param_names = {param.name for param in content_item.params}
        messages: List[str] = []
        resolved_item_modules = get_content_item_supported_modules(content_item)

        for fetch_type in active_fetch_types:
            for required_param in sorted(fetch_type.required_params):
                if required_param not in existing_param_names:
                    messages.append(
                        self.missing_param_message.format(
                            required_param,
                            fetch_type.display_name,
                            content_item.path.name,
                        )
                    )
                    fix_plan.params_to_add[required_param] = sorted(
                        allowed_by_param[required_param] & resolved_item_modules
                    )

        return messages

    def _collect_invalid_module_messages(
        self,
        content_item: ContentTypes,
        allowed_by_param: Dict[str, Set[str]],
        fix_plan: FixPlan,
    ) -> List[str]:
        """Collect a message per present fetch param resolving to disallowed modules.

        Args:
            content_item (ContentTypes): The integration to inspect.
            allowed_by_param (Dict[str, Set[str]]): Param name -> allowed modules.
            fix_plan (FixPlan): Populated with the cleaned modules to keep per param.

        Returns:
            List[str]: The invalid-module error messages.
        """
        messages: List[str] = []

        for param in content_item.params:
            allowed_modules = allowed_by_param.get(param.name)
            if allowed_modules is None:
                continue

            resolved_modules = get_parameter_supported_modules(param, content_item)
            invalid_modules = resolved_modules - allowed_modules
            if invalid_modules:
                messages.append(
                    self.error_message.format(
                        param.name,
                        content_item.path.name,
                        ", ".join(sorted(invalid_modules)),
                        ", ".join(sorted(allowed_modules)) or "none",
                    )
                )
                fix_plan.cleaned_modules_by_param[param.name] = sorted(
                    resolved_modules - invalid_modules
                )

        return messages

    @staticmethod
    def _build_allowed_modules_by_param(
        active_fetch_types: List[FetchType],
    ) -> Dict[str, Set[str]]:
        """Map each fetch param to its allowed modules (union across active fetch types)."""
        allowed_by_param: Dict[str, Set[str]] = {}
        for fetch_type in active_fetch_types:
            for param_name in fetch_type.all_params:
                allowed_by_param[param_name] = (
                    allowed_by_param.get(param_name, set()) | fetch_type.allowed_modules
                )
        return allowed_by_param

    def fix(self, content_item: ContentTypes) -> FixResult:
        """Remove un-allowed modules from existing params and add missing required ones.

        Args:
            content_item (ContentTypes): The integration to fix.

        Returns:
            FixResult: A description of the parameters that were fixed.
        """
        fix_plan = self.fix_plans[content_item.object_id]
        fixed_descriptions: List[str] = []
        existing_params = {param.name: param for param in content_item.params}

        # Remove un-allowed modules, keeping the allowed ones (empty list if none left).
        for param_name, cleaned_modules in sorted(
            fix_plan.cleaned_modules_by_param.items()
        ):
            param = existing_params.get(param_name)
            if param is not None:
                param.supportedModules = cleaned_modules
                fixed_descriptions.append(
                    f"cleaned supportedModules of '{param_name}' to {cleaned_modules}"
                )

        # Add missing required params with their allowed modules.
        for param_name, modules in sorted(fix_plan.params_to_add.items()):
            if param_name in existing_params:
                continue
            template = dict(SERVER_LEVEL_PARAM_TEMPLATES.get(param_name, {}))
            new_param = Parameter(name=param_name, supportedModules=modules, **template)
            content_item.params.append(new_param)
            existing_params[param_name] = new_param
            fixed_descriptions.append(
                f"added required parameter '{param_name}' with supportedModules {modules}"
            )

        return FixResult(
            validator=self,
            message=self.fix_message.format(
                content_item.path.name, "; ".join(fixed_descriptions)
            ),
            content_object=content_item,
        )
