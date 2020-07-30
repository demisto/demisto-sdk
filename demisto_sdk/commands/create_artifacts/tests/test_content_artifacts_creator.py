from pathlib import Path
from filecmp import cmp, dircmp
from shutil import rmtree


def test_modify_common_server_constants(datadir):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import modify_common_server_constants
    path_before = Path(datadir['CommonServerPython.py'])
    path_excepted = Path(datadir['CommonServerPython_modified.py'])
    old_data = path_before.read_text()
    modify_common_server_constants(path_before, 'test', '6.0.0')
    assert cmp(path_before, path_excepted)
    path_before.write_text(old_data)


def test_create_content_artifacts():
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    from demisto_sdk.commands.common.content.content import Content
    temp_artifacts_path = Path(__file__).parent / 'test_content_artifacts_creator' / 'test_create_content_artifacts' / 'temp'
    expected_artifacts_path = Path(__file__).parent / 'test_content_artifacts_creator' / 'test_create_content_artifacts' / 'content_expected_artifact'
    config = ArtifactsConfiguration(artifacts_path=temp_artifacts_path,
                                    content_version='6.0.0',
                                    zip=False,
                                    suffix='',
                                    cpus=1,
                                    content_packs=False)
    config.content = Content(Path(__file__).parent / 'test_content_artifacts_creator' /
                             'test_create_content_artifacts' / 'content')
    create_content_artifacts(artifact_conf=config)

    assert not dircmp(temp_artifacts_path, expected_artifacts_path).diff_files
    rmtree(temp_artifacts_path)


def test_create_private_content_artifacts():
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    from demisto_sdk.commands.common.content.content import Content
    temp_artifacts_path = Path(__file__).parent / 'test_content_artifacts_creator' / 'test_create_content_artifacts' / 'temp'
    expected_artifacts_path = Path(__file__).parent / 'test_content_artifacts_creator' / 'test_create_content_artifacts' / 'content_expected_artifact'
    config = ArtifactsConfiguration(artifacts_path=temp_artifacts_path,
                                    content_version='6.0.0',
                                    zip=False,
                                    suffix='',
                                    cpus=1,
                                    content_packs=False)
    config.content = Content(Path(__file__).parent / 'test_content_artifacts_creator' /
                             'test_create_content_artifacts' / 'private_content')
    create_content_artifacts(artifact_conf=config)

    assert not dircmp(temp_artifacts_path, expected_artifacts_path).diff_files
    rmtree(temp_artifacts_path)
