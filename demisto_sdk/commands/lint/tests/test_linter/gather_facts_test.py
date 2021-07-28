from typing import Callable

from wcmatch.pathlib import Path

from demisto_sdk.commands.lint import linter


def initiate_linter(demisto_content, integration_path, docker_engine=False):
    return linter.Linter(content_repo=demisto_content,
                         pack_dir=integration_path,
                         req_2=[],
                         req_3=[],
                         docker_engine=docker_engine,
                         docker_timeout=60)


class TestYamlParse:
    def test_valid_yaml_key_script_is_dict(self, demisto_content, create_integration: Callable, mocker):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    type_script_key=True)
        mocker.patch.object(linter.Linter, '_update_support_level')
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_valid_yaml_key_script_is_not_dict(self, demisto_content: Callable, create_integration: Callable, mocker):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    type_script_key=False)
        mocker.patch.object(linter.Linter, '_update_support_level')
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_not_valid_yaml(self, demisto_content: Callable, create_integration: Callable):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    yml=True)
        runner = initiate_linter(demisto_content, integration_path)
        assert runner._gather_facts(modules={})

    def test_checks_common_server_python(self, repo):
        """
        Given
        - Repo with CommonServerPython script
        When
        - Running lint on a repo with a change to CommonServerPython
        Then
        - Validate that the CommonServerPython is in the file list to check
        """
        pack = repo.create_pack('Base')
        script = pack.create_script('CommonServerPython')
        script.create_default_script()
        script_path = Path(script.path)
        runner = initiate_linter(pack.path, script_path)
        runner._gather_facts(modules={})
        common_server_python_path = runner._facts.get('lint_files')[0]
        assert 'Packs/Base/Scripts/CommonServerPython/CommonServerPython.py' in str(
            common_server_python_path)


class TestPythonPack:
    def test_package_is_python_pack(self, demisto_content: Callable, create_integration: Callable, mocker):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    js_type=False)
        mocker.patch.object(linter.Linter, '_update_support_level')
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_package_is_not_python_pack(self, demisto_content: Callable, create_integration: Callable):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    js_type=True)
        runner = initiate_linter(demisto_content, integration_path)
        assert runner._gather_facts(modules={})


class TestDockerImagesCollection:
    def test_docker_images_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        exp_image = "test-image:12.0"
        exp_py_num = 2.7
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    image=exp_image,
                                                    image_py_num=exp_py_num)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})

        assert runner._facts["images"][0][0] == exp_image
        assert runner._facts["images"][0][1] == exp_py_num

    def test_docker_images_not_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        exp_image = "demisto/python:1.3-alpine"
        exp_py_num = 2.7
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    image="",
                                                    image_py_num=exp_py_num)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})

        assert runner._facts["images"][0][0] == exp_image
        assert runner._facts["images"][0][1] == exp_py_num


class TestTestsCollection:
    def test_tests_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_tests=False)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["test"]

    def test_tests_not_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_tests=True)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["test"]


class TestLintFilesCollection:
    def test_lint_files_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_lint_file=False)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["lint_files"][0] == integration_path / f'{integration_path.name}.py'
        assert runner._facts['lint_unittest_files'][0] == integration_path / f'{integration_path.name}_test.py'

    def test_lint_files_not_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_lint_file=True)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["lint_files"]


class TestTestRequirementsCollection:
    def test_test_requirements_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content, test_reqs=True)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["additional_requirements"]
        test_requirements = ['mock', 'pre-commit', 'pytest']
        for test_req in test_requirements:
            assert test_req in runner._facts["additional_requirements"]

    def test_test_requirements_not_exists(self, mocker, demisto_content: Callable, create_integration: Callable):
        mocker.patch.object(linter.Linter, '_docker_login')
        mocker.patch.object(linter.Linter, '_update_support_level')

        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["additional_requirements"]
