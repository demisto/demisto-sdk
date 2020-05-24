from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class WidgetValidator(ContentEntityValidator):
    def is_valid_version(self):
        """Return if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()
