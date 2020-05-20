from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator


def test_handle_error():
    base_validator = BaseValidator(ignored_errors=['101', '103'])
    formatted_error = base_validator.handle_error("Error-message", "102")
    assert formatted_error == '(102) Error-message'

    formatted_error = base_validator.handle_error("ignore-this", "101")
    assert formatted_error is None
