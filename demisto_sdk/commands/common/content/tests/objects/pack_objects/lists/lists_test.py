import json
import tempfile
from pathlib import Path

from demisto_sdk.commands.common.constants import LISTS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Lists
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
LIST_GOOD = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / LISTS_DIR
    / "list-checked_integrations.json"
)
LIST_BAD = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / LISTS_DIR / "bad_name.json"
LIST_BAD_NORMALIZED = (
    TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / LISTS_DIR / "list-bad_name.json"
)


def test_objects_factory():
    obj = path_to_pack_object(LIST_GOOD)
    assert isinstance(obj, Lists)


def test_prefix():
    obj = Lists(LIST_GOOD)
    assert obj.normalize_file_name() == LIST_GOOD.name

    obj = Lists(LIST_BAD)
    assert obj.normalize_file_name() == LIST_BAD_NORMALIZED.name


def test_lists_data_files_are_filtered_out():
    """
    Given:
        - A pack with Lists in subdirectory format containing both metadata and data files
        - The data file (e.g., ExampleList_data.json) contains a JSON array

    When:
        - Iterating over the pack's lists property

    Then:
        - Only the metadata files should be returned, not the data files
        - This prevents "list indices must be integers or slices, not str" errors
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create pack structure
        pack_path = Path(tmp_dir) / "TestPack"
        lists_dir = pack_path / LISTS_DIR / "ExampleList"
        lists_dir.mkdir(parents=True)

        # Create pack_metadata.json (required for Pack initialization)
        pack_metadata = {
            "name": "TestPack",
            "description": "Test pack for lists",
            "support": "xsoar",
            "currentVersion": "1.0.0",
            "author": "Test",
            "categories": [],
            "tags": [],
            "useCases": [],
            "keywords": [],
        }
        (pack_path / "pack_metadata.json").write_text(json.dumps(pack_metadata))

        # Create metadata.json (required for Pack initialization)
        metadata = {"name": "TestPack", "id": "TestPack"}
        (pack_path / "metadata.json").write_text(json.dumps(metadata))

        # Create the list metadata file (dict structure)
        list_metadata = {
            "allRead": False,
            "data": "-",  # Placeholder, actual data is in _data file
            "id": "ExampleList",
            "name": "ExampleList",
            "type": "plain_text",
            "fromVersion": "6.5.0",
        }
        (lists_dir / "ExampleList.json").write_text(json.dumps(list_metadata))

        # Create the data file (could be a list/array which would cause the error)
        list_data = ["item1", "item2", "item3"]
        (lists_dir / "ExampleList_data.json").write_text(json.dumps(list_data))

        # Create Pack and iterate over lists
        pack = Pack(pack_path)
        lists_items = list(pack.lists)

        # Should only have 1 list item (the metadata file), not 2
        assert len(lists_items) == 1
        assert lists_items[0].path.name == "ExampleList.json"
        # Verify we can access dict properties without error
        assert lists_items[0].get("name") == "ExampleList"
