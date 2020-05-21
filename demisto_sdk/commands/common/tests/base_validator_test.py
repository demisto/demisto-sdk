from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator


def test_handle_error():
    base_validator = BaseValidator(ignored_errors=['SC101', 'SC103', "BA"])
    formatted_error = base_validator.handle_error("Error-message", "SC102", "PATH")
    assert formatted_error == 'PATH: [SC102] - Error-message\n'

    formatted_error = base_validator.handle_error("ignore-this", "SC101", "PATH")
    assert formatted_error is None

    formatted_error = base_validator.handle_error("ignore-this-as-well", "BA100", "PATH")
    assert formatted_error is None
