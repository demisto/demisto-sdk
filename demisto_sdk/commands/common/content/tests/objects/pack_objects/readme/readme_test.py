import pytest
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (
    CONTRIBUTORS_README_TEMPLATE,
    PACKS_DIR,
    PLAYBOOKS_DIR,
)
from demisto_sdk.commands.common.content.objects.pack_objects import Readme
from demisto_sdk.commands.common.content.objects.pack_objects.contributors.contributors import (
    Contributors,
)
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
README = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / "README.md"
CONTRIBUTORS = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / "CONTRIBUTORS2.json"
PLAYBOOK_README = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / PLAYBOOKS_DIR
    / "playbook-sample_new_README.md"
)


@pytest.mark.parametrize(argnames="file", argvalues=[README, PLAYBOOK_README])
def test_objects_factory(file: Path):
    obj = path_to_pack_object(README)
    assert isinstance(obj, Readme)


def test_prefix():
    obj = Readme(README)
    assert obj.normalize_file_name() == README.name


def test_mention_contributors_in_readme(pack):
    """
    Given: pack README with the following text: Test README content

    When: creating artifacts and a CONTRIBUTORS file with a list of two contributors: ["Contributor1", "Contributor2"]
        exist in the pack

    Then: Ensure the generated readme contains the original text followed by the credit to contributors section.
    """
    initial_readme_text = "Test README content\n"
    readme = pack._create_text_based("README.md", initial_readme_text)
    contributors = pack._create_json_based(
        "CONTRIBUTORS.json", "", ["Contributor1", "Contributor2"]
    )
    obj = Readme(readme.path)
    obj.contributors = Contributors(contributors.path)
    obj.mention_contributors_in_readme()

    expected_contribution_section = CONTRIBUTORS_README_TEMPLATE.format(
        contributors_names=" - Contributor1\n - Contributor2\n"
    )
    expected_readme = initial_readme_text + expected_contribution_section
    with open(readme.path) as readme_file:
        readme_file_content = readme_file.read()
    assert readme_file_content == expected_readme
