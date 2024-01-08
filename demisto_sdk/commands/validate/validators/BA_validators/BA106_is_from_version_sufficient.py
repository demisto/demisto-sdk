from __future__ import annotations

from abc import ABC

from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)


class IsFromVersionSufficientValidator(BaseValidator, ABC):
    error_code = "BA106"
    fix_message = "Raised the fromversion field to {0}"
    related_field = "fromversion"
    is_auto_fixable = True
