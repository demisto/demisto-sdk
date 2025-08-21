from pathlib import Path

import click
import pytest

from demisto_sdk.commands.upload.upload_setup import upload_content_entity
from demisto_sdk.commands.upload.uploader import SUCCESS_RETURN_CODE


def test_upload_called_for_each_input(mocker):
    """
    GIVEN multiple valid input paths are returned by parse_multiple_path_inputs
          and the upload method returns SUCCESS for each.

    WHEN upload_content_entity is called with those inputs

    THEN the upload method should be called once per input path
         and the command should exit with SUCCESS_RETURN_CODE.
    """
    # Arrange
    num_inputs = 3
    mock_inputs = [Path(f"/fake/path/input_{i}") for i in range(num_inputs)]

    # Patch with correct paths
    mocker.patch(
        "demisto_sdk.commands.upload.upload.parse_multiple_path_inputs",
        return_value=mock_inputs,
    )
    mocker.patch(
        "demisto_sdk.commands.upload.upload.parse_marketplace_kwargs",
        return_value="marketplace",
    )
    mocker.patch(
        "demisto_sdk.commands.upload.upload.update_command_args_from_config_file"
    )

    mock_uploader_instance = mocker.MagicMock()
    mock_uploader_instance.upload.return_value = SUCCESS_RETURN_CODE
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.Uploader",
        return_value=mock_uploader_instance,
    )

    kwargs = {
        "input": "path1,path2,path3",  # Simulated input, will be replaced by mock_inputs
        "keep_zip": None,
        "zip": False,
    }

    # Act
    with pytest.raises(click.exceptions.Exit) as e:
        upload_content_entity(**kwargs)

    # Assert
    assert e.value.args[0] == SUCCESS_RETURN_CODE
    assert mock_uploader_instance.upload.call_count == num_inputs
