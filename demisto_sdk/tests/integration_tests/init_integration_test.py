from os import listdir
from pathlib import Path

from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json

INIT_CMD = "init"


def test_integration_init_integration_positive(monkeypatch, tmp_path, mocker):
    """
    Given
    - Inputs to init pack with integration.

    When
    - Running the init command.

    Then
    - Ensure pack metadata is created successfully.
    - Ensure integration directory contain all files.
    """

    pack_name = "SuperPack"
    fill_pack_metadata = "Y"
    pack_display_name = "SuperPackDisplayName"
    pack_desc = "This is a super pack desc"
    support_type = "2"
    pack_category = "4"
    pack_author = "SuperMario"
    pack_url = "https://www.github.com/supermario"
    pack_email = "mario@super.com"
    pack_dev_email = "mario1@super.com,mario2@super.com"
    pack_tags = "SuperTag1,SuperTag2"
    pack_reviewers = "GithubUser1, GithubUser2"
    create_integration = "Y"
    from_version = "6.0.0"
    use_category_from_pack_metadata = "Y"
    integration_name = "SuperIntegration"
    use_dir_name_as_id = "Y"
    marketplaces = "xsoar , marketplacev2"
    inputs = [
        fill_pack_metadata,
        pack_display_name,
        pack_desc,
        support_type,
        pack_category,
        marketplaces,
        pack_author,
        pack_url,
        pack_email,
        pack_dev_email,
        pack_tags,
        pack_reviewers,
        create_integration,
        use_category_from_pack_metadata,
        integration_name,
        use_dir_name_as_id,
        from_version,
    ]

    d = tmp_path / "TestPacks"
    d.mkdir()
    tmp_dir_path = Path(d)
    tmp_pack_path = tmp_dir_path / pack_name
    tmp_pack_metadata_path = tmp_pack_path / "pack_metadata.json"
    tmp_integration_path = tmp_pack_path / "Integrations" / integration_name

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app, [INIT_CMD, "-o", tmp_dir_path, "-n", pack_name], input="\n".join(inputs)
    )

    assert all(
        [
            current_str in result.output
            for current_str in [
                f"Successfully created the pack SuperPack in: {tmp_pack_path}",
                f"Created pack metadata at path : {tmp_pack_metadata_path}",
                f"Finished creating integration: {tmp_integration_path}.",
            ]
        ]
    )
    assert result.stderr == ""

    with open(tmp_pack_metadata_path) as f:
        metadata_json = json.loads(f.read())
        assert {
            "name": pack_display_name,
            "description": pack_desc,
            "support": "partner",
            "currentVersion": "1.0.0",
            "author": pack_author,
            "url": pack_url,
            "email": pack_email,
            "devEmail": ["mario1@super.com", "mario2@super.com"],
            "categories": ["Endpoint"],
            "tags": pack_tags.split(","),
            "useCases": [],
            "keywords": [],
            "githubUser": ["GithubUser1", "GithubUser2"],
            "marketplaces": ["xsoar", "marketplacev2"],
            # testing for subset (<=) to avoid testing created and modified timestamps
        }.items() <= metadata_json.items()

    integration_dir_files = {file for file in listdir(tmp_integration_path)}
    assert {
        f"{integration_name}.py",
        f"{integration_name}.yml",
        f"{integration_name}_description.md",
        f"{integration_name}_test.py",
        f"{integration_name}_image.png",
        "test_data",
        "README.md",
        "command_examples.txt",
    } == integration_dir_files


def test_integration_init_integration_positive_no_inline_pack_name(
    monkeypatch, tmp_path, mocker
):
    """
    Given
    - Inputs to init pack with integration without a preset pack name in the command line.

    When
    - Running the init command.

    Then
    - Ensure pack metadata is created successfully.
    - Ensure integration directory contain all files.
    """

    pack_name = "SuperPack"
    fill_pack_metadata = "Y"
    pack_display_name = "SuperPackDisplayName"
    pack_desc = "This is a super pack desc"
    support_type = "2"
    pack_category = "4"
    pack_author = "SuperMario"
    pack_url = "https://www.github.com/supermario"
    pack_email = "luigi@super.com"
    pack_dev_email = "mario1@super.com,mario2@super.com"
    pack_tags = "SuperTag1,SuperTag2"
    pack_reviewers = "GithubUser1, GithubUser2"
    create_integration = "Y"
    from_version = "6.0.0"
    use_category_from_pack_metadata = "Y"
    integration_name = "SuperIntegration"
    use_dir_name_as_id = "Y"
    marketplaces = "xsoar,marketplacev2"
    inputs = [
        pack_name,
        fill_pack_metadata,
        pack_display_name,
        pack_desc,
        support_type,
        pack_category,
        marketplaces,
        pack_author,
        pack_url,
        pack_email,
        pack_dev_email,
        pack_tags,
        pack_reviewers,
        create_integration,
        use_category_from_pack_metadata,
        integration_name,
        use_dir_name_as_id,
        from_version,
    ]

    d = tmp_path / "TestPacks"
    d.mkdir()
    tmp_dir_path = Path(d)
    tmp_pack_path = tmp_dir_path / pack_name
    tmp_pack_metadata_path = tmp_pack_path / "pack_metadata.json"
    tmp_integration_path = tmp_pack_path / "Integrations" / integration_name

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, [INIT_CMD, "-o", tmp_dir_path], input="\n".join(inputs))

    assert result.exit_code == 0
    assert all(
        [
            current_str in result.output
            for current_str in [
                f"Successfully created the pack SuperPack in: {tmp_pack_path}",
                f"Created pack metadata at path : {tmp_pack_metadata_path}",
                f"Finished creating integration: {tmp_integration_path}.",
            ]
        ]
    )

    with open(tmp_pack_metadata_path) as f:
        metadata_json = json.loads(f.read())
        assert {
            "name": pack_display_name,
            "description": pack_desc,
            "support": "partner",
            "currentVersion": "1.0.0",
            "author": pack_author,
            "url": pack_url,
            "email": pack_email,
            "devEmail": ["mario1@super.com", "mario2@super.com"],
            "categories": ["Endpoint"],
            "tags": pack_tags.split(","),
            "useCases": [],
            "keywords": [],
            "githubUser": ["GithubUser1", "GithubUser2"],
            "marketplaces": ["xsoar", "marketplacev2"],
            # testing for subset (<=) to avoid testing created and modified timestamps
        }.items() <= metadata_json.items()

    integration_dir_files = {file for file in listdir(tmp_integration_path)}
    assert {
        f"{integration_name}.py",
        f"{integration_name}.yml",
        f"{integration_name}_description.md",
        f"{integration_name}_test.py",
        f"{integration_name}_image.png",
        "test_data",
        "README.md",
        "command_examples.txt",
    } == integration_dir_files
