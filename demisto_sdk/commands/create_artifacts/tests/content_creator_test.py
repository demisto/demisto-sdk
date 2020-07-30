import filecmp
from tempfile import mkdtemp

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.create_artifacts.content_creator import *
from TestSuite.test_tools import ChangeCWD


class TestContentCreator:
    def setup(self):
        tests_dir = f'{git_path()}/demisto_sdk/tests'
        self.scripts_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Scripts')
        self.integrations_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Integrations')
        self.indicator_types_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'IndicatorTypes')
        self.indicator_fields_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example',
                                                       'IndicatorFields')
        self.tools_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Tools')
        self.unified_integrations_path = os.path.join(tests_dir, 'test_files', 'UnifiedIntegrations')
        self.TestPlaybooks_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'TestPlaybooks')
        self.Packs_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'Packs')
        self._bundle_dir = mkdtemp()
        self._test_dir = mkdtemp()
        self.content_repo = os.path.join(tests_dir, 'test_files', 'content_repo_example')
        self._files_to_artifacts_dir = os.path.join(tests_dir, 'test_files', 'FilesToArtifacts')

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

    def test_copy_dir_files(self, mocker):
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
        # not checking fromversion
        mocker.patch.object(ContentCreator, 'add_from_version_to_yml', return_value='')

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

    def test_indicator_types_and_fields(self, mocker):
        """
        Given
        - Content dir with indicator types and fields
        When
        - copying the content folder to a content bundle
        Then
        - ensure files are being copied correctly
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._bundle_dir,
                                         test_bundle_path=self._test_dir,
                                         preserve_bundles=False)

        # not checking fromversion
        mocker.patch.object(ContentCreator, 'add_from_version_to_json', return_value='')

        content_creator.copy_dir_files(self.indicator_fields_full_path, content_creator.content_bundle)
        assert filecmp.cmp(f'{self.indicator_fields_full_path}/field.json',
                           f'{self._bundle_dir}/incidentfield-indicatorfield-field.json')
        assert filecmp.cmp(f'{self.indicator_fields_full_path}/incidentfield-valid.json',
                           f'{self._bundle_dir}/incidentfield-indicatorfield-valid.json')

        content_creator.copy_dir_files(self.indicator_types_full_path, content_creator.content_bundle)
        assert filecmp.cmp(f'{self.indicator_types_full_path}/cidr.json',
                           f'{self._bundle_dir}/reputation-cidr.json')
        assert filecmp.cmp(f'{self.indicator_types_full_path}/reputation-cve.json',
                           f'{self._bundle_dir}/reputation-cve.json')
        assert filecmp.cmp(f'{self.indicator_types_full_path}/reputations.json',
                           f'{self._bundle_dir}/reputations.json')

    def test_tools(self):
        """
        Given
        - Content dir with tools
        When
        - copying the content folder to a content bundle
        Then
        - ensure files are being copied correctly
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._bundle_dir,
                                         test_bundle_path=self._test_dir,
                                         preserve_bundles=False)

        content_creator.copy_dir_files(self.tools_full_path, content_creator.content_bundle)
        assert os.path.isfile(f'{self._bundle_dir}/tools-test.zip')

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

    def test_copy_packs_content_to_packs_bundle(self, mocker):
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
        # not checking fromversion
        mocker.patch.object(ContentCreator, 'add_from_version_to_yml', return_value='')

        content_creator.copy_packs_to_content_bundles([f'{self.Packs_full_path}/FeedAzure'])

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

    def test_copy_file_to_artifacts(self):
        """
        Given
        - Content dir with tools
        When
        - copying files to the content artifacts
        Then
        - ensure files are being copied correctly
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        filename = 'test_file.md'
        file_path = os.path.join(self._files_to_artifacts_dir, filename)
        content_creator.copy_file_to_artifacts(file_path)
        assert filecmp.cmp(file_path, os.path.join(self.content_repo, filename))

    def test_content_legacy_with_no_md(self, repo):
        """
        Given
        - valid content dir
        When
        - copying the content folder to a content bundle(flatten files)
        Then
        - Ensure no md files were copied to content bundle
        - Ensure md files were copied to packs bundle.
        """
        pack = repo.create_pack('Test')
        integration = pack.create_integration('Test')
        integration_old = pack.create_integration('OldIntegration')
        integration_old.write_yml({'script': '', 'type': 'python', 'deprecated': True})
        integration_old.write_changelog('this is a test')
        integration.create_default_integration()
        pack.create_release_notes('1_0_1')
        pack.create_incident_field('incidentfield-city', release_notes=True)
        temp = pack.repo_path
        bundle_packs = os.path.join(temp, 'bundle_packs')
        bundle_content = os.path.join(temp, 'bundle_content')
        repo.content_descriptor.write_json({
            "installDate": "0001-01-01T00:00:00Z",
            "assetId": "REPLACE_THIS_WITH_CI_BUILD_NUM",
            "releaseNotes": "## Demisto Content Release Notes for version 2.5.0",
            "modified": "REPLACE_THIS_WITH_RELEASE_DATE",
            "ignoreGit": False,
            "releaseDate": "REPLACE_THIS_WITH_RELEASE_DATE",
            "version": -1,
            "release": "2.5.0",
            "id": ""
        })
        repo.id_set.write_json({})
        content_creator = ContentCreator(artifacts_path=temp, content_version='2.5.0',
                                         preserve_bundles=True, no_update_commonserver=True)
        with ChangeCWD(pack.repo_path):
            content_creator.create_content()

            assert filecmp.cmp(f'{temp}/Packs/Test/ReleaseNotes/1_0_1.md',
                               f'{bundle_packs}/Test/ReleaseNotes/1_0_1.md')
            assert not os.path.isfile(f'{bundle_content}/incidentfield-city_README.md')
            assert not os.path.isfile(f'{bundle_content}/integration-OldIntegration_CHANGELOG.md')

    def test_add_from_version_to_yml__no_fromversion_in_yml(self, repo):
        """
        Given
        - An integration yml path with no fromversion in it
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml has fromversion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        content_creator = ContentCreator(artifacts_path=self.content_repo)

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_yml__lower_fromversion_in_yml(self, repo):
        """
        Given
        - An integration yml path with a fromversion which is lower than LATEST_SUPPORTED_VERSION
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml has fromversion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        integration.write_yml({"fromversion": "1.0.0"})
        content_creator = ContentCreator(artifacts_path=self.content_repo)

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_yml__higher_fromversion_in_yml(self, repo):
        """
        Given
        - An integration yml path with a fromversion which is higher than LATEST_SUPPORTED_VERSION
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml's fromversion is unchanged
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        integration.write_yml({"fromversion": higher_version})

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') == higher_version

    def test_add_from_version_to_yml__lower_toversion_in_yml(self, repo):
        """
        Given
        - An integration yml path with a toversion which is lower than LATEST_SUPPORTED_VERSION and no fromversion
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml does not have fromversion key
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration.write_yml({"toversion": "1.0.0"})

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') is None

    def test_add_from_version_to_yml__higher_toversion_in_yml__no_fromversion(self, repo):
        """
        Given
        - An integration yml path with a toversion which is higher than LATEST_SUPPORTED_VERSION and no fromversion
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml has fromversion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        integration.write_yml({"toversion": higher_version})

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_yml__higher_toversion_in_yml__with_fromversion(self, repo):
        """
        Given
        - An integration yml path with a toversion which is higher than LATEST_SUPPORTED_VERSION and lower fromversion
        When
        - running add_from_version_to_yml method
        Then
        - the resulting yml has fromversion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        integration.write_yml({"toversion": higher_version, "fromversion": "1.0.0"})

        with ChangeCWD(repo.path):
            unified_yml = content_creator.add_from_version_to_yml(file_path=integration.yml_path)
            assert unified_yml.get('fromversion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_json__no_fromversion_in_json(self, repo):
        """
        Given
        - An json path with no fromVersion
        When
        - running add_from_version_to_json method
        Then
        - the resulting json has fromVersion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        json_path = pack.create_dashboard("some_json", content={}).path
        content_creator = ContentCreator(artifacts_path=self.content_repo)

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_json__with__lower_fromversion_in_json(self, repo):
        """
        Given
        - An json path with a fromVersion which is lower than LATEST_SUPPORTED_VERSION
        When
        - running add_from_version_to_json method
        Then
        - the resulting json has fromVersion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        json_path = pack.create_dashboard("some_json", content={"fromVersion": "1.0.0"}).path
        content_creator = ContentCreator(artifacts_path=self.content_repo)

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_json__with__higher_fromversion_in_json(self, repo):
        """
        Given
        - An json path with a fromVersion which is higher than LATEST_SUPPORTED_VERSION
        When
        - running add_from_version_to_json method
        Then
        - the resulting json's fromVersion is unchanged
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        json_path = pack.create_dashboard("some_json", content={"fromVersion": higher_version}).path

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') == higher_version

    def test_add_from_version_to_json__with__lower_toversion_in_json(self, repo):
        """
        Given
        - An json path with a toVersion which is lower than LATEST_SUPPORTED_VERSION
        When
        - running add_from_version_to_json method
        Then
        - the resulting json has no fromVersion
        """
        pack = repo.create_pack('pack')
        json_path = pack.create_dashboard("some_json", content={"toVersion": "1.0.0"}).path
        content_creator = ContentCreator(artifacts_path=self.content_repo)

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') is None

    def test_add_from_version_to_json__with__higher_toversion_in_json(self, repo):
        """
        Given
        - An json path with a toVersion which is higher than LATEST_SUPPORTED_VERSION and no fromVersion
        When
        - running add_from_version_to_json method
        Then
        - the resulting json has fromVersion of LATEST_SUPPORTED_VERSION
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        json_path = pack.create_dashboard("some_json", content={"toVersion": higher_version}).path

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') == LATEST_SUPPORTED_VERSION

    def test_add_from_version_to_json__with__higher_toversion_in_json_and_lower_fromversion(self, repo):
        """
        Given
        - An json path with a toVersion which is higher than LATEST_SUPPORTED_VERSION and lower fromVersion
        When
        - running add_from_version_to_json method
        Then
        - the resulting json's fromVersion is unchanged
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        higher_version = LATEST_SUPPORTED_VERSION.split('.')
        higher_version[0] = str(int(higher_version[0]) + 1)
        higher_version = '.'.join(higher_version)
        json_path = pack.create_dashboard("some_json", content={"toVersion": higher_version,
                                                                "fromVersion": "1.0.0"}).path

        with ChangeCWD(repo.path):
            json_content = content_creator.add_from_version_to_json(file_path=json_path)
            assert json_content.get('fromVersion') == LATEST_SUPPORTED_VERSION

    def test_should_process_file_to_bundle__yml_low_fromvesrion_content_bundle(self, repo):
        """
        Given
        - A yml path with a fromversion lower than 6.0.0
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        integration.write_yml({"fromversion": "1.0.0"})
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(integration.yml_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__yml_no_fromvesrion_content_bundle(self, repo):
        """
        Given
        - An yml path with no fromversion
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(integration.yml_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__yml_high_fromvesrion_content_bundle(self, repo):
        """
        Given
        - An yml path with a fromversion higher than 6.0.0
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return False
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        integration.write_yml({"fromversion": "6.0.0"})
        with ChangeCWD(repo.path):
            assert not content_creator.should_process_file_to_bundle(integration.yml_path,
                                                                     content_creator.content_bundle)

    def test_should_process_file_to_bundle__json_high_fromvesrion_content_bundle(self, repo):
        """
        Given
        - An json path with a fromVersion higher than 6.0.0
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return False
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={"fromVersion": "6.0.0"}).path
        with ChangeCWD(repo.path):
            assert not content_creator.should_process_file_to_bundle(json_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__json_low_fromvesrion_content_bundle(self, repo):
        """
        Given
        - An json path with a fromVersion lower than 6.0.0
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={"fromVersion": "1.0.0"}).path
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(json_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__json_no_fromvesrion_content_bundle(self, repo):
        """
        Given
        - An json path with no fromVersion
        - creating content bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={}).path
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(json_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__yml_low_tovesrion_packs_bundle(self, repo):
        """
        Given
        - A yml path with a toversion lower than 6.0.0
        - creating packs bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        integration.write_yml({"fromversion": "1.0.0"})
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(integration.yml_path, content_creator.packs_bundle)

    def test_should_process_file_to_bundle__yml_no_tovesrion_packs_bundle(self, repo):
        """
        Given
        - A yml path with no toversion
        - creating packs bundle
        When
        - running check_from_version method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(integration.yml_path, content_creator.packs_bundle)

    def test_should_process_file_to_bundle__yml_high_fromvesrion_packs_bundle(self, repo):
        """
        Given
        - A yml path with a fromversion higher than 6.0.0
        - creating packs bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        integration = pack.create_integration('integration')
        integration.write_yml({"fromversion": "6.0.0"})
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(integration.yml_path, content_creator.packs_bundle)

    def test_should_process_file_to_bundle__json_high_fromvesrion_packs_bundle(self, repo):
        """
        Given
        - A json path with a fromVersion higher than 6.0.0
        - creating packs bundle
        When
        - running check_from_version method
        Then
        - return False
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={"fromVersion": "6.0.0"}).path
        with ChangeCWD(repo.path):
            assert not content_creator.should_process_file_to_bundle(json_path, content_creator.content_bundle)

    def test_should_process_file_to_bundle__json_low_tovesrion_packs_bundle(self, repo):
        """
        Given
        - A json path with a toVersion lower than 6.0.0
        - creating packs bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return False
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={"toVersion": "1.0.0"}).path
        with ChangeCWD(repo.path):
            assert not content_creator.should_process_file_to_bundle(json_path, content_creator.packs_bundle)

    def test_should_process_file_to_bundle__json_no_tovesrion_packs_bundle(self, repo):
        """
        Given
        - A json path with no toVersion
        - creating packs bundle
        When
        - running should_process_file_to_bundle method
        Then
        - return True
        """
        pack = repo.create_pack('pack')
        content_creator = ContentCreator(artifacts_path=self.content_repo)
        json_path = pack.create_dashboard("some_json", content={}).path
        with ChangeCWD(repo.path):
            assert content_creator.should_process_file_to_bundle(json_path, content_creator.packs_bundle)

    def test_add_suffix_to_file_path(self):
        """
        Given
        - A file path
        - content creator - with suffix and without
        When
        - running add_suffix_to_file_path method
        Then
        - if the suffix exists - add it to the file name
        - if no suffix exists - leave the file name unchanged
        """
        content_creator = ContentCreator(artifacts_path='.', suffix='_suffix')
        file_path = "some/path/to/file.yml"
        file_path_with_suffix = "some/path/to/file_suffix.yml"
        assert file_path_with_suffix == content_creator.add_suffix_to_file_path(file_path)

        content_creator = ContentCreator(artifacts_path='.')
        assert file_path == content_creator.add_suffix_to_file_path(file_path)
