import unittest

from demisto_sdk.commands.common.errors import Errors


class TestErrors(unittest.TestCase):
    def test_file_name_includes_spaces(self):
        file_name = "test file.gif"
        expected_result = ("Please remove spaces from the file's name: 'test file.gif'.", 'BA103')
        result = Errors.file_name_include_spaces_error(file_name)
        assert expected_result == result

    def test_wrong_required_value(self):
        param_name = "test param"
        expected_result = ("The required field of the test param parameter should be False", "IN102")
        result = Errors.wrong_required_value(param_name)
        assert result == expected_result

    def test_pack_metadata_empty(self):
        expected_result = ("Pack metadata is empty.", "PA105")
        result = Errors.pack_metadata_empty()
        assert result == expected_result

    def test_might_need_rns(self):
        expected_result = "You may need RN in this file, please verify if they are required."
        result = Errors.might_need_release_notes()
        assert result == expected_result

    def test_unknown_file(self):
        expected_result = "File type is unknown, check it out."
        result = Errors.unknown_file()
        assert result == expected_result

    def test_id_change(self):
        expected_result = "You've changed the ID of the file, please undo this change."
        result = Errors.id_changed()
        assert result == expected_result

    def test_id_might_change(self):
        expected_result = "ID may have changed, please make sure to check you have the correct one."
        result = Errors.id_might_changed()
        assert result == expected_result
