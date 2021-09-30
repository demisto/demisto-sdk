import io
import json
import os
import shutil

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.secrets.secrets import SecretsValidator


def create_whitelist_secrets_file(file_path, urls=None, ips=None, files=None, generic_strings=None):
    if files is None:
        files = []
    if urls is None:
        urls = []
    if ips is None:
        ips = []
    if generic_strings is None:
        generic_strings = []
    with io.open(file_path, 'w') as f:
        secrets_content = dict(
            files=files,
            iocs=dict(
                ips=ips,
                urls=urls
            ),
            generic_strings=generic_strings
        )
        f.write(json.dumps(secrets_content, indent=4))


def create_empty_whitelist_secrets_file(file_path):
    create_whitelist_secrets_file(file_path)


class TestSecrets:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    TEST_BASE_PATH = os.path.join(FILES_PATH, 'fake_integration/')
    TEST_YML_FILE = TEST_BASE_PATH + 'fake_integration.yml'
    TEST_PY_FILE = TEST_BASE_PATH + 'fake_integration.py'
    TEST_WHITELIST_FILE_PACKS = TEST_BASE_PATH + 'fake.secrets-ignore'
    TEST_WHITELIST_FILE = TEST_BASE_PATH + 'fake_secrets_white_list.json'
    TEST_BASE_64_STRING = 'OCSn7JGqKehoyIyMCm7gPFjKXpawXvh2M32' * 20 + ' sade'
    WHITE_LIST_FILE_NAME = 'secrets_white_list.json'
    FILE_HASH_LIST = ['123c8fc6532ba547d7ef598', '456c8fc6532ba547d7bb5e880a', '789c8fc6532ba57ef5985bb5e']
    MAIL_LIST = ['test1@gmail.com', 'test2@gmail.com', 'test3@gmail.com']
    IP_LIST = ['ip-172-31-15-237', '1.1.1.1', '12.25.12.14']

    TEMP_DIR = os.path.join(FILES_PATH, 'temp')
    TEST_FILE_WITH_SECRETS = os.path.join(TEMP_DIR, 'file_with_secrets_in_it.yml')

    validator = SecretsValidator(is_circle=True, white_list_path=os.path.join(FILES_PATH, WHITE_LIST_FILE_NAME))

    @classmethod
    def setup_class(cls):
        print("Setups TestSecrets class")
        if not os.path.exists(TestSecrets.TEMP_DIR):
            os.mkdir(TestSecrets.TEMP_DIR)

    @classmethod
    def teardown_class(cls):
        print("Tearing down TestSecrets class")
        if os.path.exists(TestSecrets.TEMP_DIR):
            shutil.rmtree(TestSecrets.TEMP_DIR, ignore_errors=False, onerror=None)

    def test_get_diff_text_files(self):
        changed_files = '''A\tIntegrations/Recorded_Future/Recorded_Future.yml\n
        D\tIntegrations/integration-Recorded_Future.yml'''
        get_diff = self.validator.get_diff_text_files(changed_files)
        assert 'Integrations/Recorded_Future/Recorded_Future.yml' in get_diff

    def test_is_text_file(self):
        changed_files = 'Integrations/Recorded_Future/Recorded_Future.yml'
        is_txt = self.validator.is_text_file(changed_files)
        assert is_txt is True

    def test_search_potential_secrets__no_secrets_found(self):
        secret_to_location = self.validator.search_potential_secrets([self.TEST_YML_FILE])
        assert not secret_to_location

    def test_search_potential_secrets__secrets_found(self, repo):
        create_empty_whitelist_secrets_file(os.path.join(TestSecrets.TEMP_DIR, TestSecrets.WHITE_LIST_FILE_NAME))

        validator = SecretsValidator(is_circle=True, white_list_path=os.path.join(TestSecrets.TEMP_DIR,
                                                                                  TestSecrets.WHITE_LIST_FILE_NAME))

        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        integration.yml.write_dict({'deprecated': "print('This is our dummy code') a = 100 b = 300 c = a + b "
                                                  "API_KEY = OIifdsnsjkgnj3254nkdfsjKNJD0345 # this is our secret "
                                                  "some_dict = { 'some_foo': 100docker  print(some_dict.some_foo)"})

        secrets_found = validator.search_potential_secrets([integration.yml.path])
        assert secrets_found[integration.yml.path][2] == ['OIifdsnsjkgnj3254nkdfsjKNJD0345']

    def test_ignore_entropy(self, repo):
        """
        - no items in the whitelist
        - file contains 2 secrets:
            - email
            - password
        - run validate secrets with --ignore-entropy=True
        - ensure email found
        - ensure entropy code was not executed - no secrets have found
        """
        create_empty_whitelist_secrets_file(os.path.join(TestSecrets.TEMP_DIR, TestSecrets.WHITE_LIST_FILE_NAME))

        validator = SecretsValidator(is_circle=True,
                                     ignore_entropy=True,
                                     white_list_path=os.path.join(TestSecrets.TEMP_DIR,
                                                                  TestSecrets.WHITE_LIST_FILE_NAME))

        pack = repo.create_pack('pack')
        integration = pack.create_integration('integration')
        integration.yml.write_dict({'deprecated': "print('This is our dummy code') my_email = 'fooo@someorg.com' "
                                                  "API_KEY = OIifdsnsjkgnj3254nkdfsjKNJD0345 # this is our secret "
                                                  "some_dict = { 'some_foo': 100 }"})

        secrets_found = validator.search_potential_secrets([integration.yml.path], True)
        assert secrets_found[integration.yml.path][1] == ['fooo@someorg.com']

    def test_two_files_with_same_name(self):
        """
        - no items in the whitelist
        - file contains 1 secret:
            - email
        - run validate secrets with --ignore-entropy=True
        - ensure secret is found in two files from different directories with the same base name
        """
        create_empty_whitelist_secrets_file(os.path.join(TestSecrets.TEMP_DIR, TestSecrets.WHITE_LIST_FILE_NAME))
        dir1_path = os.path.join(TestSecrets.TEMP_DIR, "dir1")
        dir2_path = os.path.join(TestSecrets.TEMP_DIR, "dir2")
        os.mkdir(dir1_path)
        os.mkdir(dir2_path)
        validator = SecretsValidator(is_circle=True,
                                     ignore_entropy=True,
                                     white_list_path=os.path.join(TestSecrets.TEMP_DIR,
                                                                  TestSecrets.WHITE_LIST_FILE_NAME))

        file_name = 'README.md'
        file1_path = os.path.join(dir1_path, file_name)
        file2_path = os.path.join(dir2_path, file_name)
        for file_path in [file1_path, file2_path]:
            with io.open(file_path, 'w') as f:
                f.write('''
print('This is our dummy code')
my_email = "fooo@someorg.com"
''')
        secrets_found = validator.search_potential_secrets([file1_path, file2_path], True)
        assert secrets_found[os.path.join(dir1_path, file_name)] == {4: ['fooo@someorg.com']}
        assert secrets_found[os.path.join(dir2_path, file_name)] == {4: ['fooo@someorg.com']}

    def test_remove_white_list_regex(self):
        white_list = '155.165.45.232'
        file_contents = '''
        boop
        shmoop
        155.165.45.232
        '''
        file_contents = self.validator.remove_whitelisted_items_from_file(file_contents, {white_list})
        assert white_list not in file_contents

    def test_remove_whitelisted_items_from_file_escaped_whitelist(self):
        """
        Given
        - White list with a term that can be regex (***.).
        - String with no content
        When
        - Removing terms containing that regex
        Then
        - Ensure secrets that the secret isn't in the output.
        - Ensure no error raised
        """
        white_list = '***.url'
        file_contents = '''
        Random and unmeaningful file content
        a string containing ***.url
        '''
        file_contents = self.validator.remove_whitelisted_items_from_file(file_contents, {white_list})
        assert white_list not in file_contents

    def test_remove_whitelisted_items_from_file_substring(self):
        white_list = 'url.com'
        file_contents = '''
        url.com
        boop
        cool@url.com
        shmoop
        https://url.com
        '''
        assert white_list not in self.validator.remove_whitelisted_items_from_file(file_contents, {white_list})

    def test_temp_white_list(self):
        file_contents = self.validator.get_file_contents(self.TEST_YML_FILE, '.yml')
        temp_white_list = self.validator.create_temp_white_list(file_contents)
        assert 'sha256' in temp_white_list

    def test_get_related_yml_contents(self):
        yml_file_contents = self.validator.retrieve_related_yml(os.path.dirname(self.TEST_PY_FILE))
        assert 'Use the Zoom integration manage your Zoom users and meetings' in yml_file_contents

    def test_regex_for_secrets(self):
        line = 'dockerimage: demisto/duoadmin:1.0.0.147 199.199.178.199 123e4567-e89b-12d3-a456-426655440000'
        secrets, false_positives = self.validator.regex_for_secrets(line)
        assert '1.0.0.147' in false_positives
        assert '123e4567-e89b-12d3-a456-426655440000' in false_positives
        assert '199.199.178.199' in secrets

    def test_calculate_shannon_entropy(self):
        test_string = 'SADE'
        entropy = self.validator.calculate_shannon_entropy(test_string)
        assert entropy == 2.0

    def test_get_packs_white_list(self):
        final_white_list, ioc_white_list, files_while_list = \
            self.validator.get_packs_white_list(self.TEST_WHITELIST_FILE_PACKS)
        assert ioc_white_list == []
        assert files_while_list == []
        assert final_white_list == ['boop', 'sade', 'sade.txt', 'sade@sade.sade', '']

    def test_get_generic_white_list(self):
        final_white_list, ioc_white_list, files_while_list = \
            self.validator.get_generic_white_list(self.TEST_WHITELIST_FILE)
        assert ioc_white_list == ['sade@sade.sade']
        assert files_while_list == ['sade.txt']
        assert final_white_list == ['sade@sade.sade', 'aboop', 'asade']

    def test_remove_false_positives(self):
        line = '[I AM MISTER MEESEEKS LOOK AT ME] sade'
        line = self.validator.remove_false_positives(line)
        assert line == ' sade'

    def test_is_secrets_disabled(self):
        line1 = 'disable-secrets-detection'
        skip_secrets = {'skip_once': False, 'skip_multi': False}
        skip_secrets = self.validator.is_secrets_disabled(line1, skip_secrets)
        assert skip_secrets['skip_once'] and not skip_secrets['skip_multi']
        skip_secrets['skip_once'] = False
        line2 = 'disable-secrets-detection-start'
        skip_secrets = self.validator.is_secrets_disabled(line2, skip_secrets)
        assert not skip_secrets['skip_once'] and skip_secrets['skip_multi']
        line3 = 'disable-secrets-detection-end'
        skip_secrets = self.validator.is_secrets_disabled(line3, skip_secrets)
        assert not skip_secrets['skip_once'] and not skip_secrets['skip_multi']

    def test_ignore_base64(self):
        file_contents = self.TEST_BASE_64_STRING
        file_contents = self.validator.ignore_base64(file_contents)
        assert file_contents.lstrip() == 'sade'

    def test_get_white_listed_items_not_pack(self):
        final_white_list, ioc_white_list, files_white_list = self.validator.get_white_listed_items(False, None)
        assert final_white_list == {'https://api.zoom.us', 'PaloAltoNetworksXDR', 'ip-172-31-15-237'}
        assert ioc_white_list == {'https://api.zoom.us'}
        assert files_white_list == set()

    def test_get_white_listed_items_pack(self, monkeypatch):
        monkeypatch.setattr('demisto_sdk.commands.secrets.secrets.PACKS_DIR', self.FILES_PATH)
        final_white_list, ioc_white_list, files_white_list = self.validator.get_white_listed_items(True, 'fake_pack')
        assert final_white_list == {'https://www.demisto.com', 'https://api.zoom.us', 'PaloAltoNetworksXDR',
                                    'ip-172-31-15-237'}
        assert ioc_white_list == {'https://api.zoom.us'}
        assert files_white_list == set()

    def test_reformat_secrets_output(self):
        secrets_output = self.validator.reformat_secrets_output(self.FILE_HASH_LIST)
        assert secrets_output == '123c8fc6532ba547d7ef598\n456c8fc6532ba547d7bb5e880a\n789c8fc6532ba57ef5985bb5e'

        secrets_output = self.validator.reformat_secrets_output(self.MAIL_LIST)
        assert secrets_output == 'test1@gmail.com\ntest2@gmail.com\ntest3@gmail.com'

        secrets_output = self.validator.reformat_secrets_output(self.IP_LIST)
        assert secrets_output == 'ip-172-31-15-237\n1.1.1.1\n12.25.12.14'

        secrets_output = self.validator.reformat_secrets_output([])
        assert secrets_output == ''

    def test_get_all_diff_text_files(self, mocker):
        mocker.patch('demisto_sdk.commands.secrets.secrets.run_command',
                     return_value='m\tPacks/Integrations/integration/testing.py\n')
        validator = SecretsValidator(is_circle=True, white_list_path=os.path.join(TestSecrets.TEMP_DIR,
                                                                                  TestSecrets.WHITE_LIST_FILE_NAME))

        assert validator.get_all_diff_text_files('master', True) == ['Packs/Integrations/integration/testing.py']
        assert validator.get_all_diff_text_files('master', False) == ['Packs/Integrations/integration/testing.py']

        validator.prev_ver = 'Testing_branch'
        assert validator.get_all_diff_text_files('master', True) == ['Packs/Integrations/integration/testing.py']
        assert validator.get_all_diff_text_files('master', False) == ['Packs/Integrations/integration/testing.py']

    def test_remove_secrets_disabled_line(self):
        """
        Given
            1. String with a line containing "disable-secrets-detection"
            1. String with a lines containing "disable-secrets-detection-start" & "disable-secrets-detection-end"
        When
            Removing content that belongs to ignored lines
        Then
            Ensure secrets that are in these lines aren't in the output.
        """
        file_contents = '''
        import
        8.8.8.8 # disable-secrets-detection
        end
        '''
        file_contents = self.validator.remove_secrets_disabled_line(file_contents)
        assert "8.8.8.8" not in file_contents

        file_contents1 = '''
        import
        8.8.8.8 # disable-secrets-detection-start
        4.4.4.4
        end # disable-secrets-detection-end
        8.8.8.4
        '''
        file_contents1 = self.validator.remove_secrets_disabled_line(file_contents1)
        assert "8.8.8.8" not in file_contents1
        assert "4.4.4.4" not in file_contents1
        assert "8.8.8.4" in file_contents1

    def test_find_secrets(self, mocker):
        """
        Given
            Working on a forked branch
        When
            Find_secrets is running
        Then
            Ensure we are looking for secrets in this branch
        """
        mocker.patch("demisto_sdk.commands.secrets.secrets.SecretsValidator.get_branch_name", return_value='pull/123')
        mocker.patch("demisto_sdk.commands.secrets.secrets.SecretsValidator.get_secrets", return_value=True)
        result = self.validator.find_secrets()
        assert result
