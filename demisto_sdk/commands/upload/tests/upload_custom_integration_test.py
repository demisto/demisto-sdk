"""
Unit tests for the upload-custom-integration command.

Tests cover:
- Happy path: valid _copy marker on both id and name.
- Error path: missing _copy marker without --force-id.
- Force path: missing _copy marker with --force-id (warning emitted, upload proceeds).
- Non-integration YAML input raises an error.
- Only one field missing the _copy marker raises an error.
- Directory input: passing an integration directory instead of a YAML file.
- resolve_integration_yaml: directory resolution helper.
- Top-level id fallback: YAMLs without commonfields but with a top-level id.
- --force-id warning contains actionable guidance and color tags.
"""

from pathlib import Path

import pytest
import typer

from demisto_sdk.commands.upload.upload_custom_integration import (
    _FORCE_ID_ACTIONABLE_GUIDANCE,
    COPY_MARKER,
    is_integration_yaml,
    resolve_integration_yaml,
    upload_custom_integration_entity,
    validate_integration_copy_marker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INTEGRATION_YAML_TEMPLATE = """\
commonfields:
  id: {integration_id}
  version: -1
name: {integration_name}
display: {integration_name}
category: Utilities
description: A test integration.
script:
  type: python
  subtype: python3
  script: ''
  commands: []
"""

_PLAYBOOK_YAML = """\
id: MyPlaybook
name: MyPlaybook
starttaskid: '0'
tasks: {}
"""

_UNIFIED_INTEGRATION_YAML_TEMPLATE = """\
id: {integration_id}
name: {integration_name}
display: {integration_name}
category: Utilities
description: A unified integration (no commonfields section).
script:
  type: python
  subtype: python3
  script: ''
  commands: []
"""


def _write_integration_yaml(
    tmp_path: Path, integration_id: str, integration_name: str
) -> Path:
    """Write a minimal integration YAML to *tmp_path* and return its path."""
    content = _INTEGRATION_YAML_TEMPLATE.format(
        integration_id=integration_id,
        integration_name=integration_name,
    )
    yaml_path = tmp_path / f"{integration_id}.yml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def _write_integration_dir(
    tmp_path: Path, integration_id: str, integration_name: str
) -> Path:
    """Write a minimal integration YAML inside a subdirectory and return the directory path."""
    integration_dir = tmp_path / integration_id
    integration_dir.mkdir()
    content = _INTEGRATION_YAML_TEMPLATE.format(
        integration_id=integration_id,
        integration_name=integration_name,
    )
    (integration_dir / f"{integration_id}.yml").write_text(content, encoding="utf-8")
    return integration_dir


def _write_unified_integration_yaml(
    tmp_path: Path, integration_id: str, integration_name: str
) -> Path:
    """Write a unified integration YAML (no commonfields, top-level id) and return its path."""
    content = _UNIFIED_INTEGRATION_YAML_TEMPLATE.format(
        integration_id=integration_id,
        integration_name=integration_name,
    )
    yaml_path = tmp_path / f"{integration_id}.yml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def _write_playbook_yaml(tmp_path: Path) -> Path:
    """Write a minimal playbook YAML to *tmp_path* and return its path."""
    yaml_path = tmp_path / "MyPlaybook.yml"
    yaml_path.write_text(_PLAYBOOK_YAML, encoding="utf-8")
    return yaml_path


# ---------------------------------------------------------------------------
# Tests: resolve_integration_yaml
# ---------------------------------------------------------------------------


class TestResolveIntegrationYaml:
    def test_file_path_returned_unchanged(self, tmp_path):
        """
        GIVEN a path to an existing YAML file
        WHEN resolve_integration_yaml is called
        THEN the same path is returned
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        assert resolve_integration_yaml(yaml_path) == yaml_path

    def test_directory_with_single_yaml_resolved(self, tmp_path):
        """
        GIVEN a directory containing exactly one YAML file
        WHEN resolve_integration_yaml is called
        THEN the YAML file path inside the directory is returned
        """
        integration_dir = _write_integration_dir(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        resolved = resolve_integration_yaml(integration_dir)
        assert resolved.is_file()
        assert resolved.suffix == ".yml"

    def test_nonexistent_path_returned_unchanged(self, tmp_path):
        """
        GIVEN a path that does not exist
        WHEN resolve_integration_yaml is called
        THEN the original path is returned (no exception)
        """
        missing = tmp_path / "does_not_exist"
        assert resolve_integration_yaml(missing) == missing


# ---------------------------------------------------------------------------
# Tests: is_integration_yaml
# ---------------------------------------------------------------------------


class TestIsIntegrationYaml:
    def test_returns_true_for_integration_yaml(self, tmp_path):
        """
        GIVEN a valid integration YAML with a 'commonfields' section
        WHEN is_integration_yaml is called
        THEN it returns True
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        assert is_integration_yaml(yaml_path) is True

    def test_returns_true_for_integration_directory(self, tmp_path):
        """
        GIVEN a directory containing a single integration YAML
        WHEN is_integration_yaml is called with the directory path
        THEN it returns True (directory is resolved transparently)
        """
        integration_dir = _write_integration_dir(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        assert is_integration_yaml(resolve_integration_yaml(integration_dir)) is True

    def test_returns_false_for_playbook_yaml(self, tmp_path):
        """
        GIVEN a playbook YAML without a 'commonfields' section
        WHEN is_integration_yaml is called
        THEN it returns False
        """
        yaml_path = _write_playbook_yaml(tmp_path)
        assert is_integration_yaml(yaml_path) is False

    def test_returns_false_for_nonexistent_file(self, tmp_path):
        """
        GIVEN a path that does not exist
        WHEN is_integration_yaml is called
        THEN it returns False (no exception raised)
        """
        assert is_integration_yaml(tmp_path / "does_not_exist.yml") is False


# ---------------------------------------------------------------------------
# Tests: validate_integration_copy_marker
# ---------------------------------------------------------------------------


class TestValidateIntegrationCopyMarker:
    def test_valid_copy_marker_passes(self, tmp_path):
        """
        GIVEN an integration YAML where both commonfields.id and name end with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=False
        THEN no exception is raised
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        # Should not raise
        validate_integration_copy_marker(yaml_path, force_id=False)

    def test_missing_copy_marker_raises_without_force(self, tmp_path):
        """
        GIVEN an integration YAML where neither id nor name ends with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=False
        THEN typer.BadParameter is raised with a message mentioning '_copy' and system pack risk
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        with pytest.raises(typer.BadParameter) as exc_info:
            validate_integration_copy_marker(yaml_path, force_id=False)

        error_message = str(exc_info.value)
        assert COPY_MARKER in error_message
        assert "system" in error_message.lower()

    def test_missing_copy_marker_with_force_warns_and_does_not_raise(
        self, tmp_path, mocker
    ):
        """
        GIVEN an integration YAML where neither id nor name ends with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=True
        THEN no exception is raised and logger.warning is called once
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        mock_warning = mocker.patch(
            "demisto_sdk.commands.upload.upload_custom_integration.logger"
        )
        # Should not raise
        validate_integration_copy_marker(yaml_path, force_id=True)
        mock_warning.warning.assert_called_once()
        warning_text = mock_warning.warning.call_args[0][0]
        assert COPY_MARKER in warning_text

    def test_force_id_warning_contains_actionable_guidance(self, tmp_path, mocker):
        """
        GIVEN an integration YAML where neither id nor name ends with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=True
        THEN the warning message contains the three uniqueness checklist items
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        mock_logger = mocker.patch(
            "demisto_sdk.commands.upload.upload_custom_integration.logger"
        )
        validate_integration_copy_marker(yaml_path, force_id=True)

        warning_text = mock_logger.warning.call_args[0][0]
        assert "completely unique" in warning_text
        assert "repository" in warning_text
        assert "Marketplace" in warning_text
        # The constant itself should be embedded
        assert _FORCE_ID_ACTIONABLE_GUIDANCE in warning_text

    def test_force_id_warning_contains_color_tags(self, tmp_path, mocker):
        """
        GIVEN an integration YAML where neither id nor name ends with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=True
        THEN the warning string contains <yellow> and <red> loguru color tags
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        mock_logger = mocker.patch(
            "demisto_sdk.commands.upload.upload_custom_integration.logger"
        )
        validate_integration_copy_marker(yaml_path, force_id=True)

        warning_text = mock_logger.warning.call_args[0][0]
        assert "<yellow>" in warning_text
        assert "</yellow>" in warning_text
        assert "<red>" in warning_text
        assert "</red>" in warning_text

    def test_only_id_missing_copy_raises(self, tmp_path):
        """
        GIVEN an integration YAML where name ends with '_copy' but id does not
        WHEN validate_integration_copy_marker is called with force_id=False
        THEN typer.BadParameter is raised
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration", "MyIntegration_copy"
        )
        with pytest.raises(typer.BadParameter) as exc_info:
            validate_integration_copy_marker(yaml_path, force_id=False)
        assert "commonfields.id" in str(exc_info.value)

    def test_only_name_missing_copy_raises(self, tmp_path):
        """
        GIVEN an integration YAML where id ends with '_copy' but name does not
        WHEN validate_integration_copy_marker is called with force_id=False
        THEN typer.BadParameter is raised
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration"
        )
        with pytest.raises(typer.BadParameter) as exc_info:
            validate_integration_copy_marker(yaml_path, force_id=False)
        assert "name" in str(exc_info.value)

    def test_unified_yaml_top_level_id_fallback(self, tmp_path):
        """
        GIVEN a unified integration YAML with no 'commonfields' but a top-level 'id' ending with '_copy'
        WHEN validate_integration_copy_marker is called with force_id=False
        THEN no exception is raised (top-level id fallback works)
        """
        yaml_path = _write_unified_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        # Should not raise
        validate_integration_copy_marker(yaml_path, force_id=False)

    def test_directory_input_validates_correctly(self, tmp_path):
        """
        GIVEN a directory containing a valid integration YAML with '_copy' markers
        WHEN validate_integration_copy_marker is called with the directory path
        THEN no exception is raised (directory resolved transparently)
        """
        integration_dir = _write_integration_dir(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        # Should not raise
        validate_integration_copy_marker(
            resolve_integration_yaml(integration_dir), force_id=False
        )


# ---------------------------------------------------------------------------
# Tests: upload_custom_integration_entity
# ---------------------------------------------------------------------------


class TestUploadCustomIntegrationEntity:
    def test_valid_copy_marker_calls_upload(self, tmp_path, mocker):
        """
        GIVEN an integration YAML with valid '_copy' markers
        WHEN upload_custom_integration_entity is called
        THEN upload_content_entity is called exactly once with the resolved YAML path
        """
        yaml_path = _write_integration_yaml(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )

        upload_custom_integration_entity(input=yaml_path)

        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["input"] == yaml_path

    def test_directory_input_resolves_and_calls_upload(self, tmp_path, mocker):
        """
        GIVEN an integration directory (not a YAML file) with valid '_copy' markers
        WHEN upload_custom_integration_entity is called with the directory path
        THEN the YAML is resolved automatically and upload_content_entity is called
             with the resolved YAML path (not the directory)
        """
        integration_dir = _write_integration_dir(
            tmp_path, "MyIntegration_copy", "MyIntegration_copy"
        )
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )

        upload_custom_integration_entity(input=integration_dir)

        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["input"].is_file()
        assert call_kwargs["input"].suffix == ".yml"

    def test_missing_copy_marker_raises_without_force(self, tmp_path, mocker):
        """
        GIVEN an integration YAML without '_copy' markers
        WHEN upload_custom_integration_entity is called with force_id=False (default)
        THEN typer.BadParameter is raised and upload_content_entity is NOT called
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )

        with pytest.raises(typer.BadParameter):
            upload_custom_integration_entity(input=yaml_path)

        mock_upload.assert_not_called()

    def test_missing_copy_marker_with_force_calls_upload_and_warns(
        self, tmp_path, mocker
    ):
        """
        GIVEN an integration YAML without '_copy' markers
        WHEN upload_custom_integration_entity is called with force_id=True
        THEN logger.warning is called and upload_content_entity is called once
        """
        yaml_path = _write_integration_yaml(tmp_path, "MyIntegration", "MyIntegration")
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )
        mock_logger = mocker.patch(
            "demisto_sdk.commands.upload.upload_custom_integration.logger"
        )

        upload_custom_integration_entity(input=yaml_path, force_id=True)

        mock_logger.warning.assert_called_once()
        mock_upload.assert_called_once()

    def test_non_integration_yaml_raises(self, tmp_path, mocker):
        """
        GIVEN a playbook YAML (no 'commonfields' section)
        WHEN upload_custom_integration_entity is called
        THEN typer.BadParameter is raised and upload_content_entity is NOT called
        """
        yaml_path = _write_playbook_yaml(tmp_path)
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )

        with pytest.raises(typer.BadParameter) as exc_info:
            upload_custom_integration_entity(input=yaml_path)

        assert "integration YAML" in str(exc_info.value)
        mock_upload.assert_not_called()

    def test_none_input_raises(self, mocker):
        """
        GIVEN no input path (None)
        WHEN upload_custom_integration_entity is called
        THEN typer.BadParameter is raised
        """
        mock_upload = mocker.patch(
            "demisto_sdk.commands.upload.upload.upload_content_entity"
        )

        with pytest.raises(typer.BadParameter):
            upload_custom_integration_entity(input=None)

        mock_upload.assert_not_called()
