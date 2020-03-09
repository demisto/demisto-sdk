from wcmatch.pathlib import Path
from typing import Callable
from demisto_sdk.commands.lint import linter


class TestYamlParse:
    def test_valid_yaml_key_script_is_dict(self, demisto_content: Callable, create_integration: Callable):
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    type_script_key=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert runner._gather_facts(modules={})

    def test_valid_yaml_key_script_is_not_dict(self):
        pass

    def test_not_valid_yaml(self):
        pass


class TestPythonPack:
    def test_package_is_python_pack(self):
        pass

    def test_package_is_not_python_pack(self):
        pass


class TestDockerImagesCollection:
    def test_docker_images_exists(self):
        pass

    def test_python_version_valid_from_image(self):
        pass

    def test_python_version_not_valid_from_image(self):
        pass


class TestTestsCollection:
    def test_tests_exists(self):
        pass

    def test_tests_not_exists(self):
        pass


class TestLintFilesCollection:
    def test_lint_files_exists_only_relevant_files(self):
        pass

    def test_lint_files_exists(self):
        pass

    def test_lint_files_not_exists(self):
        pass
