from __future__ import annotations

from abc import ABC

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.GR_validators.GR109_is_supported_modules_compatibility import (
    IsSupportedModulesCompatibility,
)


class IsNonMandatorySupportedModulesCompatibility(IsSupportedModulesCompatibility, ABC):
    """Validates that non-mandatory (optional) dependencies have compatible supportedModules.

    This is the non-mandatory counterpart of GR109. While GR109 checks mandatory USES
    relationships (error), this validator checks non-mandatory USES relationships (warning).
    """

    error_code = "GR114"
    description = "For a non-mandatory dependency where Content Item A relies on Content Item B, the supportedModules of Content Item A should be a subset of Content Item B's supportedModules."
    rationale = "When Content Item A has a non-mandatory dependency on Content Item B, Content Item A's supportedModules should ideally be restricted to only those modules also present in Content Item B's supportedModules. This is a warning since the dependency is optional."
    error_message = (
        "The following non-mandatory dependencies have missing required modules: {0}"
    )
    related_file_type = [RelatedFileType.SCHEMA]
    # Override to check non-mandatory (optional) USES relationships instead of mandatory ones
    mandatory_dependency: bool = False
