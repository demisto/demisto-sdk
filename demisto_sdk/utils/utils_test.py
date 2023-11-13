from pathlib import Path

from utils import FileUtils


def test_get_file_diff():
    # TODO implement
    original = Path("/private/var/folders/zh/6p76m__d45qdfctpkcbm7qbxy0trwt/T/pytest-of-kgal/pytest-37/test_process_existing_pack_exi0/content_repo/Packs/HelloWorld/Integrations/HelloWorld/README.md"),
    modified = Path("/private/var/folders/zh/6p76m__d45qdfctpkcbm7qbxy0trwt/T/pytest-of-kgal/pytest-37/test_process_existing_pack_exi0/contribution/Integrations/HelloWorld/README.md")

    o = FileUtils.merge_files(f1=original, f2=modified, output_dir="/tmp")
    assert True
