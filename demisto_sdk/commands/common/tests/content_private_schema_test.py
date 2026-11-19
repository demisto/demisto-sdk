"""Tests for the legacy (pykwalify) schemas and the `format` command with the CI injected `is_content_private` key."""

from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import IS_CONTENT_PRIVATE_KEY, FileType
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from TestSuite.pack import Pack

SCHEMAS_PATH = Path(__file__).parents[1] / "schemas"
# Schemas of files that are not content items (the CI does not inject the key into them).
NON_ITEM_SCHEMAS = {
    "releasenotesconfig",
    "modelingruleschema",
    "assetsmodelingruleschema",
}


def _is_valid_scheme(path: str, scheme: FileType) -> bool:
    return StructureValidator(path, predefined_scheme=scheme).is_valid_scheme()


def _create_item(pack: Pack, item_name: str):
    """Returns the file object (with an `update` method) and the file type of a default item."""
    if item_name == "integration":
        return (
            pack.create_integration(yml=load_yaml("integration.yml")).yml,
            FileType.INTEGRATION,
        )
    if item_name == "script":
        script = pack.create_script()
        script.create_default_script()
        return script.yml, FileType.SCRIPT
    if item_name == "playbook":
        playbook = pack.create_playbook()
        playbook.create_default_playbook(name="sample")
        return playbook.yml, FileType.PLAYBOOK
    return pack.create_classifier("TestClassifier", load_json("classifier.json")), (
        FileType.CLASSIFIER
    )


@pytest.mark.parametrize(
    "item_name", ["integration", "script", "playbook", "classifier"]
)
def test_schema_accepts_flag_and_still_rejects_unknown_keys(pack: Pack, item_name: str):
    """
    Given:
        - A valid item (yml and json types).
    When:
        - Running the legacy pykwalify scheme validation, with the CI key and with an unrelated key.
    Then:
        - The item is valid by default and with `is_content_private: true`.
        - An unrelated key is rejected, which proves pykwalify rejects unknown root keys, so the schema
          addition is what makes the CI key valid (negative control).
    """
    item, scheme = _create_item(pack, item_name)
    assert _is_valid_scheme(item.path, scheme)

    item.update({IS_CONTENT_PRIVATE_KEY: True})
    assert _is_valid_scheme(item.path, scheme)

    item.update({"unrelated_key": 1})
    assert not _is_valid_scheme(item.path, scheme)


def test_schema_rejects_flag_with_a_wrong_type(pack: Pack):
    """
    Given:
        - An integration with `is_content_private` that is not a boolean.
    When:
        - Running the legacy pykwalify scheme validation.
    Then:
        - The item is invalid.
    """
    integration, scheme = _create_item(pack, "integration")
    integration.update({IS_CONTENT_PRIVATE_KEY: "yes please"})
    assert not _is_valid_scheme(integration.path, scheme)


@pytest.mark.parametrize(
    "schema_path",
    [
        path
        for path in sorted(SCHEMAS_PATH.glob("*.yml"))
        if path.stem not in NON_ITEM_SCHEMAS
    ],
    ids=lambda path: path.stem,
)
def test_every_item_schema_declares_the_flag_at_the_root(schema_path: Path):
    """
    Given:
        - Each pykwalify schema of a content item.
    When:
        - Reading the root mapping.
    Then:
        - `is_content_private` is a boolean key of the root mapping.
    """
    schema = yaml.load(schema_path.read_text())
    assert schema["mapping"][IS_CONTENT_PRIVATE_KEY] == {"type": "bool"}


def test_format_keeps_the_flag(pack: Pack):
    """
    Given:
        - An integration yml that contains `is_content_private`.
    When:
        - Running the format (including the removal of the keys that are not in the schema).
    Then:
        - The key is kept in the formatted file.
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({IS_CONTENT_PRIVATE_KEY: True})

    formatter = IntegrationYMLFormat(
        integration.yml.path, path=str(SCHEMAS_PATH / "integration.yml")
    )
    formatter.remove_unnecessary_keys()
    formatter.save_yml_to_destination_file()

    assert integration.yml.read_dict()[IS_CONTENT_PRIVATE_KEY] is True
