from typing import Callable


class TestYamlParse:
    def test_valid_yaml_key_script_is_dict(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    type_script_key=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert not runner._gather_facts(modules={})

    def test_valid_yaml_key_script_is_not_dict(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    type_script_key=False)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert not runner._gather_facts(modules={})

    def test_not_valid_yaml(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    yml=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert runner._gather_facts(modules={})


class TestPythonPack:
    def test_package_is_python_pack(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    js_type=False)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert not runner._gather_facts(modules={})

    def test_package_is_not_python_pack(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    js_type=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        assert runner._gather_facts(modules={})


class TestDockerImagesCollection:
    def test_docker_images_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        tested_image = "test-image:12.0"
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    image=tested_image)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert runner._facts["images"][0][0] == tested_image

    def test_docker_images_not_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    image="")
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert runner._facts["images"][0][0] == "demisto/python:1.3-alpine"


class TestTestsCollection:
    def test_tests_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_tests=False)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert runner._facts["test"]

    def test_tests_not_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_tests=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert not runner._facts["test"]


class TestLintFilesCollection:
    def test_lint_files_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_lint_file=False)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert runner._facts["lint_files"][0] == integration_path / f'{integration_path.name}.py'

    def test_lint_files_not_exists(self, demisto_content: Callable, create_integration: Callable):
        from demisto_sdk.commands.lint import linter
        from wcmatch.pathlib import Path
        integration_path: Path = create_integration(content_path=demisto_content,
                                                    no_lint_file=True)
        runner = linter.Linter(content_path=demisto_content,
                               pack_dir=integration_path,
                               req_2=[],
                               req_3=[])
        runner._gather_facts(modules={})
        assert not runner._facts["lint_files"]
