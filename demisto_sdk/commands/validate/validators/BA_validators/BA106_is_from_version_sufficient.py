from __future__ import annotations

from abc import ABC

from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)


class IsFromVersionSufficientValidator(BaseValidator, ABC):
    error_code = "BA106"
    fix_message = "Raised the fromversion field to {0}"
    rationale = (
        "The 'fromversion' field in an integration indicates the server version that is compatible with the integration. "
        "If the server version is below the 'fromversion', the integration will not display in the Settings area. "
        "Ensuring the 'fromversion' is high enough according to whether the integration is a powershell, feed, or regular type "
        "helps maintain compatibility and proper functioning of the integration within the system."
    )
    related_field = "fromversion"
    is_auto_fixable = True
