import base64
import os
from pathlib import Path

import yaml

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter


def test_extract_long_description(tmpdir):

    # Test when script
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml',
                            output='', file_type='script', no_demisto_mock=False,
                            no_common_server=False, configuration=Configuration())
    assert extractor.extract_long_description('output_path') == 0

    # Test opening the file and writing to it
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                            output=str(tmpdir.join('temp_text.txt')), file_type='integration')

    extractor.extract_long_description(extractor.output)
    with open(extractor.output, 'rb') as temp_description:
        assert temp_description.read().decode('utf-8') == 'detaileddescription'
    os.remove(extractor.output)


def test_extract_image(tmpdir):

    # Test when script
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/script-test_script.yml',
                            output='', file_type='script')
    assert extractor.extract_image('output_path') == 0

    # Test opening the file and writing to it
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                            output=str(tmpdir.join('temp_image.png')), file_type='integration')

    extractor.extract_image(extractor.output)
    with open(extractor.output, 'rb') as temp_image:
        image_data = temp_image.read()
        image = base64.b64encode(image_data).decode('utf-8')
        assert image == DEFAULT_IMAGE_BASE64


def test_extract_code(tmpdir):
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                            output=str(tmpdir.join('temp_code.py')), file_type='integration')

    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert 'import demistomock as demisto  #' in file_data
        assert 'from CommonServerPython import *  #' in file_data
        assert file_data[-1] == '\n'
        assert 'register_module_line' not in file_data
    os.remove(extractor.output)

    extractor.common_server = False
    extractor.demisto_mock = False
    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert 'import demistomock as demisto  #' not in file_data
        assert 'from CommonServerPython import *  #' not in file_data
        assert 'register_module_line' not in file_data
        assert file_data[-1] == '\n'


def test_extract_code__with_apimodule(tmpdir):
    """
    Given:
        - A unified YML which ApiModule code is auto-generated there
    When:
        - run YmlSpltter on this code
    Then:
        - Ensure generated code is being deleted, and the import line exists
    """
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml',
                            output=str(tmpdir.join('temp_code.py')), file_type='integration')

    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert '### GENERATED CODE ###' not in file_data
        assert '### END GENERATED CODE ###' not in file_data
        assert 'from NGINXApiModule import *' in file_data
        assert 'def create_nginx_server_conf(file_path: str, port: int, params: Dict):' not in file_data


def test_extract_code_modules_old_format(tmpdir):
    """
    Given:
        - A unified YML which ApiModule code is auto-generated there, but the comments are not up to date
    When:
        - run YmlSpltter on this code
    Then:
        - Make sure that the imported code is still there, and the code runs.
    """
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-EDL_old_generated.yml',
                            output=str(tmpdir.join('temp_code.py')), file_type='integration')

    extractor.extract_code(extractor.output)
    with open(extractor.output, 'rb') as temp_code:
        file_data = temp_code.read().decode('utf-8')
        assert '### GENERATED CODE ###' in file_data
        assert 'def nginx_log_process(nginx_process: subprocess.Popen):' in file_data


def test_extract_code_pwsh(tmpdir):
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml',
                            output=str(tmpdir.join('temp_code')), file_type='integration')

    extractor.extract_code(extractor.output)
    # notice that we passed without an extension. Extractor should be adding .ps1
    with open(extractor.output.with_suffix('.ps1'), 'r', encoding='utf-8') as temp_code:
        file_data = temp_code.read()
        assert '. $PSScriptRoot\\CommonServerPowerShell.ps1\n' in file_data
        assert file_data[-1] == '\n'


def test_get_output_path():
    out = f'{git_path()}/demisto_sdk/tests/Integrations'
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml',
                            file_type='integration',
                            output=out)
    res = extractor.get_output_path()
    assert res == Path(out + "/Zoom")


def test_get_output_path_empty_output():
    input_path = Path(f'{git_path()}/demisto_sdk/tests/test_files/integration-Zoom.yml')
    extractor = YmlSplitter(input=str(input_path),
                            file_type='integration'
                            )
    res = extractor.get_output_path()
    assert res == input_path.parent


def test_extract_to_package_format_pwsh(tmpdir):
    out = tmpdir.join('Integrations')
    extractor = YmlSplitter(input=f'{git_path()}/demisto_sdk/tests/test_files/integration-powershell_ssh_remote.yml',
                            output=str(out), file_type='integration')
    assert extractor.extract_to_package_format() == 0
    # check code
    with open(out.join('PowerShellRemotingOverSSH').join('PowerShellRemotingOverSSH.ps1'), 'r', encoding='utf-8') as f:
        file_data = f.read()
        assert '. $PSScriptRoot\\CommonServerPowerShell.ps1\n' in file_data
        assert file_data[-1] == '\n'
    # check description
    with open(out.join('PowerShellRemotingOverSSH').join('PowerShellRemotingOverSSH_description.md'), 'r') as f:
        file_data = f.read()
        assert 'Username and password are both associated with the user in the target machine' in file_data
    # check readme
    with open(out.join('PowerShellRemotingOverSSH').join('README.md'), 'r') as f:
        file_data = f.read()
        assert 'This is a sample test README' in file_data
    with open(out.join('PowerShellRemotingOverSSH').join('PowerShellRemotingOverSSH.yml'), 'r') as f:
        yaml_obj = yaml.safe_load(f)
        assert yaml_obj['fromversion'] == '5.5.0'
        assert not yaml_obj['script']['script']


def test_extract_to_package_format_py(pack, mocker, tmp_path):
    mocker.patch.object(YmlSplitter, 'extract_image', return_value='12312321')
    mocker.patch(
        'demisto_sdk.commands.split.ymlsplitter.get_python_version',
        return_value='2.7'
    )
    mocker.patch(
        'demisto_sdk.commands.split.ymlsplitter.get_pipenv_dir',
        return_value=os.path.join(git_path(), 'demisto_sdk/tests/test_files/default_python2')
    )
    mocker.patch(
        'demisto_sdk.commands.split.ymlsplitter.get_pip_requirements',
        return_value="""certifi==2017.11.5
chardet==3.0.4
idna==2.6
olefile==0.44
PyYAML==3.12
requests==2.18.4
urllib3==1.22
"""
    )
    integration = pack.create_integration('Sample')
    integration.create_default_integration()
    out = tmp_path / 'TestIntegration'
    non_sorted_imports = 'from CommonServerPython import *\nimport datetime\nimport json'
    integration.yml.update(
        {
            'image': '',
            'script': {
                'type': 'python',
                'script': non_sorted_imports
            }
        }
    )
    extractor = YmlSplitter(input=integration.yml.path,
                            output=str(out), file_type='integration')
    extractor.extract_to_package_format()
    with open(out / 'TestIntegration.py', encoding='utf-8') as f:
        file_data = f.read()
        # check imports are sorted
        assert non_sorted_imports not in file_data
