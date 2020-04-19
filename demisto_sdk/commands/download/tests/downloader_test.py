from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, LAYOUTS_DIR, PLAYBOOKS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.tools import get_child_files
from tempfile import mkdtemp
import pytest
import json
import os
import shutil

CONTENT_BASE_PATH = 'demisto_sdk/commands/download/tests/tests_env/content'
CUSTOM_CONTENT_BASE_PATH = 'demisto_sdk/commands/download/tests/tests_data/custom_content'

INTEGRATION_PACK_OBJECT = {'Test Integration': [{'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/TestIntegration.py', 'file_ending': 'py'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/TestIntegration_test.py', 'file_ending': 'py'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/TestIntegration.yml', 'file_ending': 'yml'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/TestIntegration_image.png', 'file_ending': 'png'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/CHANGELOG.md', 'file_ending': 'md'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/TestIntegration_description.md', 'file_ending': 'md'}, {'name': 'Test Integration', 'id': 'Test Integration', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration/README.md', 'file_ending': 'md'}]}
SCRIPT_PACK_OBJECT = {'TestScript': [{'name': 'TestScript', 'id': 'TestScript', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Scripts/TestScript/TestScript.py', 'file_ending': 'py'}, {'name': 'TestScript', 'id': 'TestScript', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Scripts/TestScript/TestScript.yml', 'file_ending': 'yml'}, {'name': 'TestScript', 'id': 'TestScript', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Scripts/TestScript/CHANGELOG.md', 'file_ending': 'md'}, {'name': 'TestScript', 'id': 'TestScript', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Scripts/TestScript/README.md', 'file_ending': 'md'}]}
PLAYBOOK_PACK_OBJECT = {'FormattingPerformance - Test': [{'name': 'FormattingPerformance - Test', 'id': 'FormattingPerformance - Test', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Playbooks/playbook-FormattingPerformance_-_Test.yml', 'file_ending': 'yml'}]}
LAYOUT_PACK_OBJECT = {'Hello World Alert': [{'name': 'Hello World Alert', 'id': 'Hello World Alert', 'path': f'{CONTENT_BASE_PATH}/Packs/TestPack/Layouts/layout-details-Hello_World_Alert-V2.json', 'file_ending': 'json'}]}

INTEGRATION_CUSTOM_CONTENT_OBJECT = {'id': 'Test Integration', 'name': 'Test Integration', 'path': f'{CUSTOM_CONTENT_BASE_PATH}/integration-Test_Integration.yml', 'entity': 'Integrations', 'type': 'integration', 'file_ending': 'yml'}
SCRIPT_CUSTOM_CONTENT_OBJECT = {'id': 'TestScript', 'name': 'TestScript', 'path': f'{CUSTOM_CONTENT_BASE_PATH}/automation-TestScript.yml', 'entity': 'Scripts', 'type': 'script', 'file_ending': 'yml'}
PLAYBOOK_CUSTOM_CONTENT_OBJECT = {'id': 'FormattingPerformance - Test', 'name': 'FormattingPerformance - Test', 'path': f'{CUSTOM_CONTENT_BASE_PATH}/playbook-FormattingPerformance_-_Test.yml', 'entity': 'Playbooks', 'type': 'playbook', 'file_ending': 'yml'}
LAYOUT_CUSTOM_CONTENT_OBJECT = {'id': 'Hello World Alert', 'name': 'Hello World Alert', 'path': f'{CUSTOM_CONTENT_BASE_PATH}/layout-details-Hello_World_Alert-V2.json', 'entity': 'Layouts', 'type': 'layout', 'file_ending': 'json'}


class TestHelperMethods:
    def test_remove_traces(self):
        downloader = Downloader(output='', input='')
        temp_dir_path = downloader.custom_content_temp_dir
        assert os.path.isdir(temp_dir_path)
        downloader.remove_traces()
        assert not os.path.isdir(temp_dir_path)

    @pytest.mark.parametrize('name, ending, detail, output', [('G S M', 'py', 'python', 'GSM.py'),
                                                              ('G S M', 'yml', 'yaml', 'GSM.yml'),
                                                              ('G S M', 'png', 'image', 'GSM_image.png'),
                                                              ('G S M', 'md', 'description', 'GSM_description.md')])
    def test_get_searched_basename(self, name, ending, detail, output):
        downloader = Downloader(output='', input='')
        assert downloader.get_searched_basename(name, ending, detail) == output

    @pytest.mark.parametrize('ending, output', [('py', 'python'), ('md', 'description'), ('yml', 'yaml'), ('png', 'image'),
                                                ('', '')])
    def test_get_extracted_file_detail(self, ending, output):
        downloader = Downloader(output='', input='')
        assert downloader.get_extracted_file_detail(ending) == output

    @pytest.mark.parametrize('name, output', [('automation-demisto', 'script-demisto'), ('wow', 'wow')])
    def test_update_file_prefix(self, name, output):
        downloader = Downloader(output='', input='')
        assert downloader.update_file_prefix(name) == output

    @pytest.mark.parametrize('name', ['GSM', 'G S M', 'G_S_M', 'G-S-M', 'G S_M', 'G_S-M'])
    def test_create_dir_name(self, name):
        downloader = Downloader(output='', input='')
        assert downloader.create_dir_name(name) == 'GSM'


class TestBuildPackContent:
    def test_build_pack_content(self):
        pass

    @pytest.mark.parametrize('entity, path, output_pack_content_object', [
        (INTEGRATIONS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration', INTEGRATION_PACK_OBJECT),
        (SCRIPTS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Scripts/TestScript', SCRIPT_PACK_OBJECT),
        (PLAYBOOKS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Playbooks/playbook-FormattingPerformance_-_Test.yml', PLAYBOOK_PACK_OBJECT),
        (LAYOUTS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Layouts/layout-details-Hello_World_Alert-V2.json', LAYOUT_PACK_OBJECT),
        (LAYOUTS_DIR, 'demisto_sdk/commands/download/tests/downloader_test.py', {})])
    def test_build_pack_content_object(self, entity, path, output_pack_content_object):
        downloader = Downloader(output='', input='')
        pack_content_object = downloader.build_pack_content_object(entity, path)
        assert json.dumps(pack_content_object, sort_keys=True) == json.dumps(output_pack_content_object, sort_keys=True)

    @pytest.mark.parametrize('entity, path, main_id, main_name', [
        (INTEGRATIONS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Integrations/TestIntegration',
         'Test Integration', 'Test Integration'),
        (LAYOUTS_DIR, f'{CONTENT_BASE_PATH}/Packs/TestPack/Layouts/layout-details-Hello_World_Alert-V2.json',
         'Hello World Alert', 'Hello World Alert'),
        (LAYOUTS_DIR, 'demisto_sdk/commands/download/tests/downloader_test.py', '', '')])
    def test_get_main_file_details(self, entity, path, main_id, main_name):
        downloader = Downloader(output='', input='')
        op_id, op_name = downloader.get_main_file_details(entity, os.path.abspath(path))
        assert op_id == main_id
        assert op_name == main_name


class TestBuildCustomContent:
    def test_build_custom_content(self):
        pass

    @pytest.mark.parametrize('path, output_custom_content_object', [
        (f'{CUSTOM_CONTENT_BASE_PATH}/automation-TestScript.yml', SCRIPT_CUSTOM_CONTENT_OBJECT),
        (f'{CUSTOM_CONTENT_BASE_PATH}/integration-Test_Integration.yml', INTEGRATION_CUSTOM_CONTENT_OBJECT),
        (f'{CUSTOM_CONTENT_BASE_PATH}/layout-details-Hello_World_Alert-V2.json', LAYOUT_CUSTOM_CONTENT_OBJECT),
        (f'{CUSTOM_CONTENT_BASE_PATH}/playbook-FormattingPerformance_-_Test.yml', PLAYBOOK_CUSTOM_CONTENT_OBJECT)
    ])
    def test_build_custom_content_object(self, path, output_custom_content_object):
        downloader = Downloader(output='', input='')
        assert downloader.build_custom_content_object(path) == output_custom_content_object


class TestPackHierarchy:
    def test_update_pack_hierarchy(self):
        pass


class TestMergeOldFile:
    def test_merge_and_extract_old_file(self):
        pass

    def test_merge_old_file(self):
        pass

    def test_get_corresponding_pack_content_object(self):
        pass

    def test_get_corresponding_pack_file_object(self):
        pass

    def test_update_data(self):
        pass


class TestMergeNewFile:
    def test_merge_and_extract_new_integration(self):
        temp_dir = mkdtemp()
        entity = INTEGRATION_CUSTOM_CONTENT_OBJECT['entity']
        basename = INTEGRATION_CUSTOM_CONTENT_OBJECT['name'].replace(' ', '')
        output_entity_dir_path = f'{temp_dir}/{entity}'
        os.mkdir(output_entity_dir_path)
        output_dir_path = f'{output_entity_dir_path}/{basename}'
        os.mkdir(output_dir_path)
        downloader = Downloader(output=temp_dir, input='')
        files = [f'{output_dir_path}/{basename}.py', f'{output_dir_path}/{basename}.yml',
                 f'{output_dir_path}/{basename}_image.png', f'{output_dir_path}/{basename}_description.md',
                 f'{output_dir_path}/README.md', f'{output_dir_path}/CHANGELOG.md']

        downloader.merge_and_extract_new_file(INTEGRATION_CUSTOM_CONTENT_OBJECT)
        output_files = get_child_files(output_dir_path)
        assert sorted(output_files) == sorted(files)

        shutil.rmtree(temp_dir)

    def test_merge_and_extract_new_script(self):
        temp_dir = mkdtemp()
        entity = SCRIPT_CUSTOM_CONTENT_OBJECT['entity']
        basename = SCRIPT_CUSTOM_CONTENT_OBJECT['name'].replace(' ', '')
        output_entity_dir_path = f'{temp_dir}/{entity}'
        os.mkdir(output_entity_dir_path)
        output_dir_path = f'{output_entity_dir_path}/{basename}'
        os.mkdir(output_dir_path)
        downloader = Downloader(output=temp_dir, input='')
        files = [f'{output_dir_path}/{basename}.py', f'{output_dir_path}/{basename}.yml',
                 f'{output_dir_path}/README.md', f'{output_dir_path}/CHANGELOG.md']

        downloader.merge_and_extract_new_file(SCRIPT_CUSTOM_CONTENT_OBJECT)
        output_files = get_child_files(output_dir_path)
        assert sorted(output_files) == sorted(files)

        shutil.rmtree(temp_dir)

    @pytest.mark.parametrize('custom_content_object', [PLAYBOOK_CUSTOM_CONTENT_OBJECT, LAYOUT_CUSTOM_CONTENT_OBJECT])
    def test_merge_new_file(self, custom_content_object):
        temp_dir = mkdtemp()
        entity = custom_content_object['entity']
        os.mkdir(f'{temp_dir}/{entity}')
        downloader = Downloader(output=temp_dir, input='')
        old_file_path = custom_content_object['path']
        new_file_path = f'{temp_dir}/{entity}/{os.path.basename(old_file_path)}'

        downloader.merge_new_file(custom_content_object)
        assert os.path.isfile(new_file_path)

        shutil.move(src=new_file_path, dst=old_file_path)
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestFilesNotDownloaded:
    def test_log_files_not_downloaded(self):
        pass


class TestVerifyPackPath:
    @pytest.mark.parametrize('output_path, valid_ans', [('Integrations', False), ('Packs/TestPack/', True),
                             ('Demisto', False), ('Packs', False), ('Packs/TestPack', True)])
    def test_verify_path_is_pack(self, output_path, valid_ans):
        downloader = Downloader(output=f'{CONTENT_BASE_PATH}/{output_path}', input='')
        assert downloader.verify_path_is_pack() is valid_ans
