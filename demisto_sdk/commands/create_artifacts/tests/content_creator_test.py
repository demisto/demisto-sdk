import filecmp
from tempfile import mkdtemp

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.create_artifacts.content_creator import *


class TestContentCreator:
    def setup(self):
        tests_dir = f'{git_path()}/demisto_sdk/tests'
        self.scripts_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Scripts')
        self.integrations_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Integrations')
        self.unified_integrations_path = os.path.join(tests_dir, 'test_files', 'UnifiedIntegrations')
        self.TestPlaybooks_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'TestPlaybooks')
        self.Packs_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Packs')
        self._bundle_dir = mkdtemp()
        self._test_dir = mkdtemp()
        self.content_repo = os.path.join(tests_dir, 'test_files', 'content_repo_example')

    def teardown(self):
        # delete all files in the content_bundle
        directories = [self._bundle_dir, self._test_dir]
        for directory in directories:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as err:
                    print('Failed to delete {}. Reason: {}'.format(file_path, err))

    def test_copy_dir_files(self):
        """
        Given
        - valid content dir, including Scripts, Integrations and TestPlaybooks sub-dirs
        When
        - copying the content folder to a content bundle(flatten files)
        Then
        - ensure files are being flatten correctly
        - ensure no !!omap are added(due to ordereddict yaml problems)
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._bundle_dir,
                                         test_bundle_path=self._test_dir,
                                         preserve_bundles=False)

        # test Scripts repo copy
        content_creator.copy_dir_files(self.scripts_full_path, content_creator.content_bundle)
        assert filecmp.cmp(f'{self.scripts_full_path}/script-Sleep.yml',
                           f'{self._bundle_dir}/script-Sleep.yml')

        # test Integrations repo copy
        content_creator.copy_dir_files(f'{self.integrations_full_path}/Securonix', content_creator.content_bundle)
        assert filecmp.cmp(f'{self.integrations_full_path}/Securonix/Securonix_unified.yml',
                           f'{self._bundle_dir}/Securonix_unified.yml')

        # test TestPlaybooks repo copy
        content_creator.copy_dir_files(self.TestPlaybooks_full_path, content_creator.test_bundle)
        assert filecmp.cmp(f'{self.TestPlaybooks_full_path}/script-Sleep-for-testplaybook.yml',
                           f'{self._test_dir}/script-Sleep-for-testplaybook.yml')

    def test_unified_integrations_copy(self):
        from ruamel.yaml import YAML
        """
        Given
        - content dir with unified YML
        When
        - copying the content folder to a content bundle
        Then
        - ensure files are being copied correctly
        - ensure files with dockerimage45 are split into 2 files
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._bundle_dir,
                                         test_bundle_path=self._test_dir,
                                         preserve_bundles=False)

        content_creator.copy_dir_files(f'{self.unified_integrations_path}/Integrations', content_creator.content_bundle)
        with io.open(f'{self._bundle_dir}/integration-Symantec_Messaging_Gateway.yml', mode='r',
                     encoding='utf-8') as file_:
            copied_file_50 = file_.read()
        with io.open(f'{self._bundle_dir}/integration-Symantec_Messaging_Gateway_45.yml', mode='r',
                     encoding='utf-8') as file_:
            copied_file_45 = file_.read()
        ryaml = YAML()
        ryaml.preserve_quotes = True
        ryaml.width = 50000  # make sure long lines will not break (relevant for code section)
        yml_data50 = ryaml.load(copied_file_50)
        yml_data45 = ryaml.load(copied_file_45)
        assert yml_data50['script']['dockerimage'] == 'demisto/bs4:1.0.0.6538'
        assert yml_data45['script']['dockerimage'] == 'demisto/bs4'

    def test_copy_packs_content_to_packs_bundle(self):
        """
        Given
        - valid content dir, including Packs sub-dir
        When
        - copying the content folder to a content bundle(flatten files)
        Then
        - ensure files are being flatten correctly
        - ensure no !!omap are added(due to ordereddict yaml problems)
        - ensure TestPlaybooks without the playbook-* prefix are valid
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._bundle_dir,
                                         test_bundle_path=self._test_dir,
                                         preserve_bundles=False)
        content_creator.copy_packs_content_to_old_bundles([f'{self.Packs_full_path}/FeedAzure'])

        # test Packs repo, TestPlaybooks repo copy without playbook- prefix
        assert filecmp.cmp(f'{self.Packs_full_path}/FeedAzure/TestPlaybooks/FeedAzure_test.yml',
                           f'{self._test_dir}/playbook-FeedAzure_test.yml')
        assert filecmp.cmp(f'{self.Packs_full_path}/FeedAzure/TestPlaybooks/playbook-FeedAzure_test_copy_no_prefix.yml',
                           f'{self._test_dir}/playbook-FeedAzure_test_copy_no_prefix.yml')

        # test Packs repo, TestPlaybooks repo copy scripts and do not add them the playbook- prefix
        assert filecmp.cmp(f'{self.Packs_full_path}/FeedAzure/TestPlaybooks/just_a_test_script.yml',
                           f'{self._test_dir}/script-just_a_test_script.yml')
        assert filecmp.cmp(f'{self.Packs_full_path}/FeedAzure/TestPlaybooks/script-prefixed_automation.yml',
                           f'{self._test_dir}/script-prefixed_automation.yml')
