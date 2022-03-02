import pytest


@pytest.fixture()
def valid_spelled_content_pack(pack):
    """
    Create a pack with valid spelled content.
    """
    for i in range(3):
        pack.create_release_notes(
            version=f"release-note-{i}",
            content="\n#### Scripts\n##### ScriptName\n- Added a feature"
        )
        pack.create_integration(name=f"integration-{i}", yml={"category": "category"})
        pack.create_incident_field(name=f"incident-field-{i}", content={"test": "test"})
        pack.create_script(name=f"script-{i}", yml={"script": "script"})
        pack.create_layout(name=f"layout-{i}", content={"test": "test"})

    return pack


@pytest.fixture()
def invalid_spelled_content_pack(pack):
    """
    Create a pack with invalid spelled content.
    """
    misspelled_files = set()

    for i in range(3):
        rn = pack.create_release_notes(
            version=f"release-note-{i}",
            content="\n#### Scipt\n##### SciptName\n- Added a feature"
        )
        misspelled_files.add(rn.path)
        integration = pack.create_integration(
            name=f"integration-{i}", yml={"display": "invalidd", "description": "invalidd", "category": "category"}
        )
        misspelled_files.add(integration.yml.path)
        pack.create_incident_field(name=f"incident-field-{i}", content={"invalidd": "invalidd"})
        script = pack.create_script(name=f"script-{i}", yml={"comment": "invalidd", "script": "script"})
        misspelled_files.add(script.yml.path)
        pack.create_layout(name=f"layout-{i}", content={"invalidd": "invalidd"})

    return pack, misspelled_files


@pytest.fixture()
def misspelled_integration(invalid_spelled_content_pack):
    """
    Returns a misspelled integration.
    """
    return invalid_spelled_content_pack[0].integrations[0]
