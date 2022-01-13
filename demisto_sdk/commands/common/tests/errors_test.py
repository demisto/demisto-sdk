import unittest

from demisto_sdk.commands.common.errors import Errors


class TestErrors(unittest.TestCase):
    def test_file_name_includes_spaces(self):
        """
        Given: File Name with spaces
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        file_name = "test file.gif"
        expected_result = ("Please remove spaces from the file's name: 'test file.gif'.", 'BA103')
        result = Errors.file_name_include_spaces_error(file_name)
        assert expected_result == result

    def test_wrong_required_value(self):
        """
        Given: Param value
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        param_name = "test param"
        expected_result = ("The required field of the test param parameter should be False", "IN102")
        result = Errors.wrong_required_value(param_name)
        assert result == expected_result

    def test_pack_metadata_empty(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        expected_result = ("Pack metadata is empty.", "PA105")
        result = Errors.pack_metadata_empty()
        assert result == expected_result

    def test_might_need_rns(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        expected_result = "You may need RN in this file, please verify if they are required."
        result = Errors.might_need_release_notes()
        assert result == expected_result

    def test_unknown_file(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a string containing error.
        """
        expected_result = "File type is unknown, check it out."
        result = Errors.unknown_file()
        assert result == expected_result

    def test_id_change(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a string containing error.
        """
        expected_result = "You've changed the ID of the file, please undo this change."
        result = Errors.id_changed()
        assert result == expected_result

    def test_id_might_change(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a string containing error.
        """
        expected_result = "ID may have changed, please make sure to check you have the correct one."
        result = Errors.id_might_changed()
        assert result == expected_result

    def test_id_should_equal(self):
        """
        Given: File name and file ID
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        expected_result = ("The File's name, which is: 'FileName', should be equal to its ID, which "
                           "is: 'FileID'. please update the file.", "BA101")
        name = "FileName"
        file_id = "FileID"
        result = Errors.id_should_equal_name(name, file_id)
        assert result == expected_result

    def test_file_type_not_supported(self):
        """
        Given: None
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        error_statement = "The file type is not supported in the validate command.\n" \
                          "The validate command supports: Integrations, Scripts, Playbooks, " \
                          "Incident fields, Incident types, Indicator fields, Indicator types, Objects fields," \
                          " Object types, Object modules, Images, Release notes, Layouts, Jobs and Descriptions."
        expected_result = (error_statement, "BA102")
        result = Errors.file_type_not_supported()
        assert result == expected_result

    def test_invalid_context_output(self):
        """
        Given: Command Name and Output Name
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        expected_result = ("Invalid context output for command TestCommand. Output is BadOutput",
                           "IN115")
        command_name = "TestCommand"
        output_name = "BadOutput"
        result = Errors.invalid_context_output(command_name, output_name)
        assert result == expected_result

    def test_wrong_display_name(self):
        """
        Given: Param Name and Param Display
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        expected_result = ('The display name of the ParamName parameter should be \'ParamDisplay\'',
                           "IN100")
        param_name = "ParamName"
        param_display = "ParamDisplay"
        result = Errors.wrong_display_name(param_name, param_display)
        assert result == expected_result

    def test_image_path_error(self):
        """
        Given: Invalid image path and an alternative valid image path
        When: Returning an error message
        Then: Return error message with the input value as a tuple containing error and error code.
        """
        path = "https://github.com/demisto/content/blob/123/Packs/TestPack/doc_files/test.png"
        alternative_path = "https://github.com/demisto/content/raw/123/Packs/TestPack/doc_files/test.png"
        error_statement = f'Detected following image url:\n{path}\n' \
                          f'Which is not the raw link. You probably want to use the following raw image url:\n' \
                          f'{alternative_path}'
        expected_result = (error_statement, "RM101")
        result = Errors.image_path_error(path, alternative_path)
        assert result == expected_result

    def test_integration_is_skipped(self):
        """
        Given: Name of a skipped integration, with no `skip comment`
        When: Returning an error message
        Then: Compile an error message, without the comment part.
        """
        integration_id = "dummy_integration"
        expected = f"The integration {integration_id} is currently in skipped. Please add working tests and unskip."

        assert Errors.integration_is_skipped(integration_id, skip_comment=None)[0] == expected
        assert Errors.integration_is_skipped(integration_id, skip_comment='')[0] == expected
        assert Errors.integration_is_skipped(integration_id)[0] == expected  # skip_comment argument is None by default

    def test_integration_is_skipped__comment(self):
        integration_id = "dummy_integration"
        skip_comment = "Issue 00000"

        expected = f"The integration {integration_id} is currently in skipped. Please add working tests and " + \
                   f"unskip. Skip comment: {skip_comment}"

        result = Errors.integration_is_skipped(integration_id, skip_comment)
        assert result[0] == expected
