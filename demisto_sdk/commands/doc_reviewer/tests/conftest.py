from pathlib import PosixPath
from types import SimpleNamespace
from typing import List

import pytest

from TestSuite.pack import Pack


@pytest.fixture()
def valid_spelled_content_pack(pack):
    """
    Create a pack with valid spelled content.
    """
    for i in range(3):
        pack.create_release_notes(
            version=f"release-note-{i}",
            content="\n#### Scripts\n##### ScriptName\n- Added the feature.",
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
            content="\n#### Scipt\n##### SciptName\n- Added the feature.",
        )
        misspelled_files.add(rn.path)
        integration = pack.create_integration(
            name=f"integration-{i}",
            yml={
                "display": "invalidd",
                "description": "invalidd",
                "category": "category",
            },
        )
        misspelled_files.add(integration.yml.path)
        pack.create_incident_field(
            name=f"incident-field-{i}", content={"invalidd": "invalidd"}
        )
        script = pack.create_script(
            name=f"script-{i}", yml={"comment": "invalidd", "script": "script"}
        )
        misspelled_files.add(script.yml.path)
        pack.create_layout(name=f"layout-{i}", content={"invalidd": "invalidd"})

    return pack, misspelled_files


@pytest.fixture()
def misspelled_integration(invalid_spelled_content_pack):
    """
    Returns a misspelled integration.
    """
    return invalid_spelled_content_pack[0].integrations[0]


@pytest.fixture(name="supported_pack")
def valid_spelled_xsoar_supported_content_pack(tmp_path: PosixPath) -> Pack:
    """
    Create a Pack with valid spelled content.
    """

    temp_pack_dir = tmp_path / "Packs"
    temp_pack_dir.mkdir()

    temp_repo = SimpleNamespace()
    setattr(temp_repo, "path", str(temp_pack_dir / ".git"))

    pack = Pack(packs_dir=temp_pack_dir, name="TempPack", repo=temp_repo)
    pack.create_release_notes(
        version="release-note-1",
        content="\n#### Scripts\n##### ScriptName\n- Added the feature.",
    )
    pack.pack_metadata.update({"support": "xsoar"})

    return pack


@pytest.fixture(name="supported_packs")
def valid_spelled_xsoar_supported_content_packs(tmp_path: PosixPath) -> List[Pack]:
    """
    Create two Packs with valid spelled content.
    """

    packs: List[Pack] = []

    temp_pack_dir = tmp_path / "Packs"
    if not temp_pack_dir.exists():
        temp_pack_dir.mkdir()

    for i in range(2):

        temp_repo = SimpleNamespace()
        setattr(temp_repo, "path", str(temp_pack_dir / ".git"))

        pack = Pack(packs_dir=temp_pack_dir, name=f"TempPack-{i}", repo=temp_repo)
        pack.create_release_notes(
            version="release-note-1",
            content="\n#### Scripts\n##### ScriptName\n- Added the feature.",
        )
        pack.pack_metadata.update({"support": "xsoar"})

        packs.append(pack)

    return packs


@pytest.fixture(name="non_supported_pack")
def valid_spelled_xsoar_non_supported_content_pack(tmp_path: PosixPath) -> Pack:
    """
    Create a Pack with valid spelled content.
    """

    temp_pack_dir = tmp_path / "Packs"
    temp_pack_dir.mkdir()

    temp_repo = SimpleNamespace()
    setattr(temp_repo, "path", str(temp_pack_dir / ".git"))

    pack = Pack(packs_dir=temp_pack_dir, name="TempPack", repo=temp_repo)
    pack.create_release_notes(
        version="release-note-1",
        content="\n#### Scripts\n##### ScriptName\n- Added the feature.",
    )
    pack.pack_metadata.update({"support": "community"})

    return pack


@pytest.fixture(name="non_supported_pack_mispelled")
def invalid_xsoar_non_supported_content_pack(tmp_path: PosixPath) -> Pack:
    """
    Create a non-XSOAR-supported Pack with mispelled content.
    """

    temp_pack_dir = tmp_path / "Packs"
    temp_pack_dir.mkdir()

    temp_repo = SimpleNamespace()
    setattr(temp_repo, "path", str(temp_pack_dir / ".git"))

    pack = Pack(packs_dir=temp_pack_dir, name="TempPack", repo=temp_repo)
    pack.create_release_notes(
        version="release-note-1",
        content="\n#### Scrts\n##### ScrName\n-.",
    )
    pack.pack_metadata.update({"support": "community"})

    return pack


@pytest.fixture(name="supported_pack_mispelled")
def invalid_xsoar_supported_content_pack(tmp_path: PosixPath) -> Pack:
    """
    Create a non-XSOAR-supported Pack with mispelled content.
    """

    temp_pack_dir = tmp_path / "Packs"
    temp_pack_dir.mkdir()

    temp_repo = SimpleNamespace()
    setattr(temp_repo, "path", str(temp_pack_dir / ".git"))

    pack = Pack(packs_dir=temp_pack_dir, name="TempPack", repo=temp_repo)
    pack.create_release_notes(
        version="release-note-1",
        content="\n#### Scrts\n##### ScrName\n-.",
    )
    pack.pack_metadata.update({"support": "xsoar"})

    return pack
