import json
import os
import shutil
from tempfile import mkdtemp

import pytest
from demisto_sdk.commands.common.constants import (BETA_INTEGRATIONS_DIR,
                                                   CLASSIFIERS_DIR,
                                                   CONNECTIONS_DIR,
                                                   DASHBOARDS_DIR,
                                                   INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR,
                                                   INDICATOR_FIELDS_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, PLAYBOOKS_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   WIDGETS_DIR)
from demisto_sdk.commands.common.tools import get_child_files
from demisto_sdk.commands.download.downloader import Downloader
from mock import patch

CONTENT_BASE_PATH = 'demisto_sdk/commands/download/tests/tests_env/content'
CUSTOM_CONTENT_BASE_PATH = 'demisto_sdk/commands/download/tests/tests_data/custom_content'
PACK_INSTANCE_PATH = f'{CONTENT_BASE_PATH}/Packs/TestPack'

INTEGRATION_INSTANCE_PATH = f'{PACK_INSTANCE_PATH}/Integrations/TestIntegration'
SCRIPT_INSTANCE_PATH = f'{PACK_INSTANCE_PATH}/Scripts/TestScript'
PLAYBOOK_INSTANCE_PATH = f'{PACK_INSTANCE_PATH}/Playbooks/playbook-FormattingPerformance_-_Test.yml'
LAYOUT_INSTANCE_PATH = f'{PACK_INSTANCE_PATH}/Layouts/layout-details-Hello_World_Alert-V2.json'

CUSTOM_CONTENT_SCRIPT_PATH = f'{CUSTOM_CONTENT_BASE_PATH}/automation-TestScript.yml'
CUSTOM_CONTENT_INTEGRATION_PATH = f'{CUSTOM_CONTENT_BASE_PATH}/integration-Test_Integration.yml'
CUSTOM_CONTENT_LAYOUT_PATH = f'{CUSTOM_CONTENT_BASE_PATH}/layout-details-Hello_World_Alert-V2.json'
CUSTOM_CONTENT_PLAYBOOK_PATH = f'{CUSTOM_CONTENT_BASE_PATH}/playbook-FormattingPerformance_-_Test.yml'

INTEGRATION_PACK_OBJECT = {'Test Integration': [
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/TestIntegration.py', 'file_ending': 'py'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/TestIntegration_test.py', 'file_ending': 'py'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/TestIntegration.yml', 'file_ending': 'yml'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/TestIntegration_image.png', 'file_ending': 'png'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/CHANGELOG.md', 'file_ending': 'md'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/TestIntegration_description.md', 'file_ending': 'md'},
    {'name': 'Test Integration', 'id': 'Test Integration',
     'path': f'{INTEGRATION_INSTANCE_PATH}/README.md', 'file_ending': 'md'}
]}
SCRIPT_PACK_OBJECT = {'TestScript': [
    {'name': 'TestScript', 'id': 'TestScript', 'path': f'{SCRIPT_INSTANCE_PATH}/TestScript.py', 'file_ending': 'py'},
    {'name': 'TestScript', 'id': 'TestScript', 'path': f'{SCRIPT_INSTANCE_PATH}/TestScript.yml', 'file_ending': 'yml'},
    {'name': 'TestScript', 'id': 'TestScript', 'path': f'{SCRIPT_INSTANCE_PATH}/CHANGELOG.md', 'file_ending': 'md'},
    {'name': 'TestScript', 'id': 'TestScript', 'path': f'{SCRIPT_INSTANCE_PATH}/README.md', 'file_ending': 'md'}
]}
PLAYBOOK_PACK_OBJECT = {'FormattingPerformance - Test': [
    {'name': 'FormattingPerformance - Test', 'id': 'FormattingPerformance - Test', 'path': PLAYBOOK_INSTANCE_PATH,
     'file_ending': 'yml'}
]}
LAYOUT_PACK_OBJECT = {'Hello World Alert': [
    {'name': 'Hello World Alert', 'id': 'Hello World Alert', 'path': LAYOUT_INSTANCE_PATH,
     'file_ending': 'json'}
]}

PACK_CONTENT = {
    INTEGRATIONS_DIR: [INTEGRATION_PACK_OBJECT],
    SCRIPTS_DIR: [SCRIPT_PACK_OBJECT],
    PLAYBOOKS_DIR: [PLAYBOOK_PACK_OBJECT],
    LAYOUTS_DIR: [LAYOUT_PACK_OBJECT],
    TEST_PLAYBOOKS_DIR: [], REPORTS_DIR: [], DASHBOARDS_DIR: [], WIDGETS_DIR: [], INCIDENT_FIELDS_DIR: [],
    INDICATOR_FIELDS_DIR: [], INCIDENT_TYPES_DIR: [], CLASSIFIERS_DIR: [], CONNECTIONS_DIR: [], BETA_INTEGRATIONS_DIR: []
}

INTEGRATION_CUSTOM_CONTENT_OBJECT = {'id': 'Test Integration', 'name': 'Test Integration',
                                     'path': CUSTOM_CONTENT_INTEGRATION_PATH, 'entity': 'Integrations',
                                     'type': 'integration', 'file_ending': 'yml'}
SCRIPT_CUSTOM_CONTENT_OBJECT = {'id': 'TestScript', 'name': 'TestScript',
                                'path': CUSTOM_CONTENT_SCRIPT_PATH, 'entity': 'Scripts',
                                'type': 'script', 'file_ending': 'yml'}
PLAYBOOK_CUSTOM_CONTENT_OBJECT = {'id': 'FormattingPerformance - Test', 'name': 'FormattingPerformance - Test',
                                  'path': CUSTOM_CONTENT_PLAYBOOK_PATH, 'entity': 'Playbooks',
                                  'type': 'playbook', 'file_ending': 'yml'}
LAYOUT_CUSTOM_CONTENT_OBJECT = {'id': 'Hello World Alert', 'name': 'Hello World Alert',
                                'path': CUSTOM_CONTENT_LAYOUT_PATH, 'entity': 'Layouts',
                                'type': 'layout', 'file_ending': 'json'}
FAKE_CUSTOM_CONTENT_OBJECT = {'id': 'DEMISTO', 'name': 'DEMISTO',
                              'path': f'{CUSTOM_CONTENT_BASE_PATH}/DEMISTO.json', 'entity': 'Layouts',
                              'type': 'layout', 'file_ending': 'json'}


CUSTOM_CONTENT = [
    INTEGRATION_CUSTOM_CONTENT_OBJECT, SCRIPT_CUSTOM_CONTENT_OBJECT, PLAYBOOK_CUSTOM_CONTENT_OBJECT,
    LAYOUT_CUSTOM_CONTENT_OBJECT
]


class TestHelperMethods:
    def test_remove_traces(self):
        downloader = Downloader(output='', input='')
        temp_dir_path = downloader.custom_content_temp_dir
        assert os.path.isdir(temp_dir_path)
        downloader.remove_traces()
        assert not os.path.isdir(temp_dir_path)

    @pytest.mark.parametrize('name, ending, detail, output', [
        ('G S M', 'py', 'python', 'GSM.py'),
        ('G S M', 'yml', 'yaml', 'GSM.yml'),
        ('G S M', 'png', 'image', 'GSM_image.png'),
        ('G S M', 'md', 'description', 'GSM_description.md')
    ])
    def test_get_searched_basename(self, name, ending, detail, output):
        downloader = Downloader(output='', input='')
        assert downloader.get_searched_basename(name, ending, detail) == output

    @pytest.mark.parametrize('ending, output', [
        ('py', 'python'), ('md', 'description'), ('yml', 'yaml'), ('png', 'image'), ('', '')
    ])
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
        downloader = Downloader(output=PACK_INSTANCE_PATH, input='')
        downloader.build_pack_content()
        assert json.dumps(downloader.pack_content, sort_keys=True) == json.dumps(PACK_CONTENT, sort_keys=True)

    @pytest.mark.parametrize('entity, path, output_pack_content_object', [
        (INTEGRATIONS_DIR, INTEGRATION_INSTANCE_PATH, INTEGRATION_PACK_OBJECT),
        (SCRIPTS_DIR, SCRIPT_INSTANCE_PATH, SCRIPT_PACK_OBJECT),
        (PLAYBOOKS_DIR, PLAYBOOK_INSTANCE_PATH, PLAYBOOK_PACK_OBJECT),
        (LAYOUTS_DIR, LAYOUT_INSTANCE_PATH, LAYOUT_PACK_OBJECT),
        (LAYOUTS_DIR, 'demisto_sdk/commands/download/tests/downloader_test.py', {})
    ])
    def test_build_pack_content_object(self, entity, path, output_pack_content_object):
        downloader = Downloader(output='', input='')
        pack_content_object = downloader.build_pack_content_object(entity, path)
        assert json.dumps(pack_content_object, sort_keys=True) == json.dumps(output_pack_content_object, sort_keys=True)

    @pytest.mark.parametrize('entity, path, main_id, main_name', [
        (INTEGRATIONS_DIR, INTEGRATION_INSTANCE_PATH, 'Test Integration', 'Test Integration'),
        (LAYOUTS_DIR, LAYOUT_INSTANCE_PATH, 'Hello World Alert', 'Hello World Alert'),
        (LAYOUTS_DIR, 'demisto_sdk/commands/download/tests/downloader_test.py', '', '')
    ])
    def test_get_main_file_details(self, entity, path, main_id, main_name):
        downloader = Downloader(output='', input='')
        op_id, op_name = downloader.get_main_file_details(entity, os.path.abspath(path))
        assert op_id == main_id
        assert op_name == main_name


class TestBuildCustomContent:
    @pytest.mark.parametrize('custom_content_object, exist_in_pack', [
        (INTEGRATION_CUSTOM_CONTENT_OBJECT, True),
        (SCRIPT_CUSTOM_CONTENT_OBJECT, True),
        (PLAYBOOK_CUSTOM_CONTENT_OBJECT, True),
        (LAYOUT_CUSTOM_CONTENT_OBJECT, True),
        (FAKE_CUSTOM_CONTENT_OBJECT, False)
    ])
    def test_exist_in_pack_content(self, custom_content_object, exist_in_pack):
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader('', '')
            downloader.pack_content = PACK_CONTENT
            assert downloader.exist_in_pack_content(custom_content_object) is exist_in_pack

    @pytest.mark.parametrize('path, output_custom_content_object', [
        (CUSTOM_CONTENT_SCRIPT_PATH, SCRIPT_CUSTOM_CONTENT_OBJECT),
        (CUSTOM_CONTENT_INTEGRATION_PATH, INTEGRATION_CUSTOM_CONTENT_OBJECT),
        (CUSTOM_CONTENT_LAYOUT_PATH, LAYOUT_CUSTOM_CONTENT_OBJECT),
        (CUSTOM_CONTENT_PLAYBOOK_PATH, PLAYBOOK_CUSTOM_CONTENT_OBJECT)
    ])
    def test_build_custom_content_object(self, path, output_custom_content_object):
        downloader = Downloader(output='', input='')
        assert downloader.build_custom_content_object(path) == output_custom_content_object


class TestPackHierarchy:
    @staticmethod
    def prepare_env():
        integration_instance_temp_path = f'{INTEGRATION_INSTANCE_PATH}_temp'
        shutil.copytree(INTEGRATION_INSTANCE_PATH, integration_instance_temp_path)
        script_dir_path = os.path.dirname(SCRIPT_INSTANCE_PATH)
        script_dir_temp_path = f'{os.path.dirname(SCRIPT_INSTANCE_PATH)}_temp'
        shutil.copytree(script_dir_path, script_dir_temp_path)
        shutil.rmtree(INTEGRATION_INSTANCE_PATH)
        shutil.rmtree(script_dir_path)
        return integration_instance_temp_path, script_dir_temp_path, script_dir_path

    @staticmethod
    def restore_env(integration_instance_temp_path, script_dir_temp_path, script_dir_path):
        shutil.rmtree(SCRIPT_INSTANCE_PATH)
        os.rename(integration_instance_temp_path, INTEGRATION_INSTANCE_PATH)
        os.rename(script_dir_temp_path, script_dir_path)

    def test_update_pack_hierarchy(self):
        integration_instance_temp_path, script_dir_temp_path, script_dir_path = self.prepare_env()
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader('', '')
            downloader.output_pack_path = PACK_INSTANCE_PATH
            downloader.custom_content = CUSTOM_CONTENT
            downloader.update_pack_hierarchy()
            assert os.path.isdir(INTEGRATION_INSTANCE_PATH)
            assert os.path.isdir(SCRIPT_INSTANCE_PATH)
        self.restore_env(integration_instance_temp_path, script_dir_temp_path, script_dir_path)


class TestMergeOldFile:
    def test_merge_and_extract_existing_file(self):
        pass

    def test_merge_existing_file(self):
        pass

    @pytest.mark.parametrize('custom_content_object, pack_content_object', [
        (INTEGRATION_CUSTOM_CONTENT_OBJECT, INTEGRATION_PACK_OBJECT),
        (SCRIPT_CUSTOM_CONTENT_OBJECT, SCRIPT_PACK_OBJECT),
        (PLAYBOOK_CUSTOM_CONTENT_OBJECT, PLAYBOOK_PACK_OBJECT),
        (LAYOUT_CUSTOM_CONTENT_OBJECT, LAYOUT_PACK_OBJECT),
        (FAKE_CUSTOM_CONTENT_OBJECT, {})
    ])
    def test_get_corresponding_pack_content_object(self, custom_content_object, pack_content_object):
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader('', '')
            downloader.pack_content = PACK_CONTENT
            corr_obj = downloader.get_corresponding_pack_content_object(custom_content_object)
            corresponding_pack_content_object = json.dumps(corr_obj, sort_keys=True)
            assert corresponding_pack_content_object == json.dumps(pack_content_object, sort_keys=True)

    @pytest.mark.parametrize('file_name, ex_file_ending, ex_file_detail, corr_pack_object, pack_file_object', [
        ('Test Integration', 'yml', 'yaml', INTEGRATION_PACK_OBJECT, INTEGRATION_PACK_OBJECT['Test Integration'][2]),
        ('Test Integration', 'py', 'python', INTEGRATION_PACK_OBJECT, INTEGRATION_PACK_OBJECT['Test Integration'][0]),
        ('Test Integration', 'png', 'image', INTEGRATION_PACK_OBJECT, INTEGRATION_PACK_OBJECT['Test Integration'][3]),
        ('Test Integration', 'md', 'description', INTEGRATION_PACK_OBJECT, INTEGRATION_PACK_OBJECT['Test Integration']
            [5]),
        ('TestScript', 'yml', 'yaml', SCRIPT_PACK_OBJECT, SCRIPT_PACK_OBJECT['TestScript'][1]),
        ('TestScript', 'py', 'python', SCRIPT_PACK_OBJECT, SCRIPT_PACK_OBJECT['TestScript'][0]),
        ('Fake Name', 'py', 'python', SCRIPT_PACK_OBJECT, {})
    ])
    def test_get_corresponding_pack_file_object(self, file_name, ex_file_ending, ex_file_detail, corr_pack_object,
                                                pack_file_object):
        with patch.object(Downloader, "__init__", lambda a, b, c: None):
            downloader = Downloader('', '')
            downloader.pack_content = PACK_CONTENT
            searched_basename = downloader.get_searched_basename(file_name, ex_file_ending, ex_file_detail)
            corr_file = downloader.get_corresponding_pack_file_object(searched_basename, corr_pack_object)
            corresponding_pack_file_object = json.dumps(corr_file, sort_keys=True)
            assert corresponding_pack_file_object == json.dumps(pack_file_object, sort_keys=True)

    def test_update_data(self):
        pass


class TestMergeNewFile:
    @pytest.mark.parametrize('custom_content_object, raw_files', [
        (INTEGRATION_CUSTOM_CONTENT_OBJECT, ['odp/bn.py', 'odp/bn.yml', 'odp/bn_image.png', 'odp/bn_description.md',
                                             'odp/README.md', 'odp/CHANGELOG.md']),
        (SCRIPT_CUSTOM_CONTENT_OBJECT, ['odp/bn.py', 'odp/bn.yml', 'odp/README.md', 'odp/CHANGELOG.md'])
    ])
    def test_merge_and_extract_new_file(self, custom_content_object, raw_files):
        temp_dir = mkdtemp()
        entity = custom_content_object['entity']
        downloader = Downloader(output=temp_dir, input='')
        basename = downloader.create_dir_name(custom_content_object['name'])
        output_entity_dir_path = f'{temp_dir}/{entity}'
        os.mkdir(output_entity_dir_path)
        output_dir_path = f'{output_entity_dir_path}/{basename}'
        os.mkdir(output_dir_path)
        files = [file.replace('odp', output_dir_path).replace('bn', basename) for file in raw_files]

        downloader.merge_and_extract_new_file(custom_content_object)
        output_files = get_child_files(output_dir_path)
        assert sorted(output_files) == sorted(files)

        shutil.rmtree(temp_dir)

    @pytest.mark.parametrize('custom_content_object', [PLAYBOOK_CUSTOM_CONTENT_OBJECT, LAYOUT_CUSTOM_CONTENT_OBJECT])
    def test_merge_new_file(self, custom_content_object):
        temp_dir = mkdtemp()
        entity = custom_content_object['entity']
        output_dir_path = f'{temp_dir}/{entity}'
        os.mkdir(output_dir_path)
        downloader = Downloader(output=temp_dir, input='')
        old_file_path = custom_content_object['path']
        new_file_path = f'{output_dir_path}/{os.path.basename(old_file_path)}'

        downloader.merge_new_file(custom_content_object)
        assert os.path.isfile(new_file_path)

        shutil.move(src=new_file_path, dst=old_file_path)
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestVerifyPackPath:
    @pytest.mark.parametrize('output_path, valid_ans', [
        ('Integrations', False), ('Packs/TestPack/', True),
        ('Demisto', False), ('Packs', False), ('Packs/TestPack', True)
    ])
    def test_verify_path_is_pack(self, output_path, valid_ans):
        downloader = Downloader(output=f'{CONTENT_BASE_PATH}/{output_path}', input='')
        assert downloader.verify_path_is_pack() is valid_ans
