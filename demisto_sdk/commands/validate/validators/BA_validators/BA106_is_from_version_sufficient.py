from __future__ import annotations

from abc import ABC

from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)


class IsFromVersionSufficientValidator(BaseValidator, ABC):
    error_code = "BA106"
    fix_message = "Raised the fromversion field to {0}"
    rationale = (
        "This field makes sure content can use the latest and greatest features of the platform. "
        "The minimal value is the third-last platform release version."
    )
    related_field = "fromversion"
    is_auto_fixable = True
