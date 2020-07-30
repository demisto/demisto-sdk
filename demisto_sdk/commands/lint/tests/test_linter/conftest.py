from typing import Callable, List, Optional

import pytest
from demisto_sdk.commands.lint import linter
from demisto_sdk.commands.lint.linter import Linter
from ruamel.yaml import YAML
from wcmatch.pathlib import Path


@pytest.fixture
def linter_obj(mocker) -> Linter:
    mocker.patch.object(linter, 'docker')
    return Linter(pack_dir=Path(__file__).parent / 'content' / 'Integrations' / 'Sample_integration',
                  content_repo=Path(__file__).parent / 'data',
                  req_3=["pytest==3.0"],
                  req_2=["pytest==2.0"],
                  docker_engine=True)


@pytest.fixture(scope='session')
def lint_files() -> List[Path]:
    return [Path(__file__).parent / 'test_data' / 'Integration' / 'intergration_sample' / 'intergration_sample.py']


@pytest.fixture
def demisto_content() -> Callable:
    import shutil
    # Init git repo
    content_path = Path(__file__).parent / 'content'

    # Create file structure
    dirs = ['Integrations', 'Scripts']
    for dir_n in dirs:
        (content_path / dir_n).mkdir(parents=True)
        (content_path / 'Packs' / 'Sample' / dir_n).mkdir(parents=True)

    yield content_path

    shutil.rmtree(content_path)


@pytest.fixture
def create_integration(mocker) -> Callable:
    def _create_integration(content_path: Path, path: str = 'Integrations', no_lint_file: bool = False,
                            flake8: bool = False, bandit: bool = False, mypy: bool = False, vulture: bool = False,
                            pylint: bool = False, test: bool = False, no_tests: bool = False, yml: bool = False,
                            js_type: bool = False, type_script_key: bool = False, image: bool = False,
                            image_py_num: float = 3.7, test_reqs: bool = False) -> Path:
        """ Creates tmp content repositry for integration test

        Args:
            content_path(Path): Content path from demisto_content fixture.
            path(str): Path to create integration.
            no_lint_file(bool): True for not creating pack.py file.
            flake8(bool): True for creating flake8 error.
            bandit(bool): True for creating bandit error.
            mypy(bool): True for creating mypy error.
            vulture(bool): True for creating vulture error.
            pylint(bool): True for creating pylint error.
            test(bool): True for creating test error.
            no_tests(bool): True for not creating tests in pack.
            yml(bool): True for creating yml structure error.
            js_type(bool): True for definig pack as JavaScript in yml.
            type_script_key(bool): True for define type in script key.
            image(str): Image to define in yml.
            image_py_num(float): Image python version.
            test_reqs(bool): True to include a test-requirements.txt file.

        Returns:
            Path: Path to tmp integration
        """
        integration_name = 'Sample_integration'
        integration_path = Path(content_path / path / integration_name)
        integration_path.mkdir()
        files_ext = ['.py', '.yml', '_description.md', '_image.png', '_test.py']
        for ext in files_ext:
            if (ext == '_test.py' and no_tests) or (ext == '.py' and no_lint_file):
                continue
            (integration_path / f'{integration_name}{ext}').touch()
        if test_reqs:
            (integration_path / 'test-requirements.txt').touch()
            (integration_path / 'test-requirements.txt').write_text('\nmock\npre-commit\npytest')
        if flake8:
            (integration_path / f'{integration_name}.py').write_text('\nfrom typing import *')
        if bandit:
            (integration_path / f'{integration_name}.py').write_text('\nimport os\n  os.chmod(\'/etc/hosts\', 0o777)')
        if mypy:
            (integration_path / f'{integration_name}.py').write_text('\nx: int = "hello"')
        if vulture:
            (integration_path / f'{integration_name}.py').write_text('\nfrom typing import *')
        if pylint:
            (integration_path / f'{integration_name}.py').write_text('\ntest()')
        if test and not no_tests:
            (integration_path / f'{integration_name}_test.py').write_text('\nassert False')
        yml_file = integration_path / f'{integration_name}.yml'
        if yml:
            yml_file.write_text('')
        else:
            yml_dict = {}
            if js_type:
                yml_dict['type'] = 'javascript'
                if type_script_key:
                    yml_dict['script'] = {'type': 'javascript'}
            else:
                yml_dict['type'] = 'python'
                if type_script_key:
                    yml_dict['script'] = {'type': 'python'}
            if image:
                yml_dict['dockerimage'] = image
            from demisto_sdk.commands.lint import linter
            mocker.patch.object(linter, 'get_python_version_from_image')
            linter.get_python_version_from_image.return_value = image_py_num

            yaml = YAML()
            yaml.dump(stream=yml_file.open(mode='w'), data=yml_dict)

        return integration_path

    return _create_integration


@pytest.fixture
def docker_mock(mocker):
    def _docker_mock(BuildException: Optional[Exception] = None, image_id: str = "image-id"):
        from demisto_sdk.commands.lint import linter
        import docker
        mocker.patch.object(docker, 'from_env')
        mocker.patch.object(linter, '')
