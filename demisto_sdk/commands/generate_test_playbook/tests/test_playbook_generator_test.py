import shutil
from pathlib import Path

import pytest

from demisto_sdk.commands.common.tools import run_command
from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import \
    PlaybookTestsGenerator


def git_path() -> str:
    return run_command('git rev-parse --show-toplevel').replace('\n', '')


class TestGenerateTestPlaybook:
    TEMP_DIR = 'temp'
    TEST_FILE_PATH = Path(git_path()) / 'demisto_sdk' / 'tests' / 'test_files'
    DUMMY_INTEGRATION_YML_PATH = TEST_FILE_PATH / 'fake_integration.yml'
    CREATED_DIRS = list()  # type: list

    @classmethod
    def setup_class(cls):
        print("Setups TestGenerateTestPlaybook class")
        Path(TestGenerateTestPlaybook.TEMP_DIR).mkdir(exist_ok=True)

    @classmethod
    def teardown_class(cls):
        print("Tearing down TestGenerateTestPlaybook class")
        if Path(TestGenerateTestPlaybook.TEMP_DIR).exists():
            shutil.rmtree(TestGenerateTestPlaybook.TEMP_DIR, ignore_errors=False, onerror=None)

    @pytest.mark.parametrize("use_all_brands,expected_yml",
                             [(False, 'fake_integration_expected_test_playbook.yml'),
                              (True, 'fake_integration_expected_test_playbook__all_brands.yml')])
    def test_generate_test_playbook(self, use_all_brands, expected_yml):
        """
        Given:  An integration yml file
        When:   Calling generate_test_playbook with any value of use_all_brands
        Then:   Ensure output is in the expected format
        """
        generator = PlaybookTestsGenerator(
            input=TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH,
            file_type='integration',
            output=TestGenerateTestPlaybook.TEMP_DIR,
            name='TestPlaybook',
            use_all_brands=use_all_brands
        )

        generator.run()
        expected_test_playbook_yml = (TestGenerateTestPlaybook.TEST_FILE_PATH / expected_yml).read_text()
        actual_test_playbook_yml = (Path(TestGenerateTestPlaybook.TEMP_DIR) /
                                    'playbook-TestPlaybook_Test.yml').read_text()

        assert expected_test_playbook_yml == actual_test_playbook_yml

    def test_generate_test_playbook__integration_under_packs(self, tmpdir):
        """
        Given:  An integration, inside the standard Content folder structure
        When:   Called `generate_test_playbook` without a blank `output` field
        Then:   Make sure the generated test playbook is correct, and saved in the standard location
                (.../Packs/<Pack name>/TestPlayBooks/playbook-<integration_name>_Test.yml)
        """
        pack_folder = Path(tmpdir) / 'Packs' / 'DummyPack'

        integration_folder = pack_folder / 'DummyIntegration'
        integration_folder.mkdir(parents=True)

        integration_path = integration_folder / 'DummyIntegration.yml'
        shutil.copy(str(TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH), str(integration_path))

        generator = PlaybookTestsGenerator(
            input=integration_path,
            file_type='integration',
            output="",
            name='TestPlaybook',
            use_all_brands=False
        )

        generator.run()

        expected_test_playbook_yml = (TestGenerateTestPlaybook.TEST_FILE_PATH /
                                      'fake_integration_expected_test_playbook.yml').read_text()
        actual_test_playbook_yml = (pack_folder / 'TestPlaybooks' / 'playbook-TestPlaybook_Test.yml').read_text()

        assert expected_test_playbook_yml == actual_test_playbook_yml

    def test_generate_test_playbook__integration_not_under_packs(self, tmpdir):
        """
        Given: an integration, NOT inside the standard Content folder structure.
        When: called `generate_test_playbook`
        Then: Make sure the generated test playbook is correct, and saved in the folder from which SDK was called.
        """

        generator = PlaybookTestsGenerator(
            input=TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH,
            file_type='integration',
            output="",
            name='TestPlaybook',
            use_all_brands=False
        )

        generator.run()

        expected_test_playbook_yml = Path(TestGenerateTestPlaybook.TEST_FILE_PATH /
                                          'fake_integration_expected_test_playbook.yml').read_text()
        actual_test_playbook_yml = Path('playbook-TestPlaybook_Test.yml').read_text()

        assert expected_test_playbook_yml == actual_test_playbook_yml

    def test_generate_test_playbook__specified_output_folder(self, tmpdir):
        """
        Given: an integration yaml, and a specified output folder
        When: called `generate_test_playbook`
        Then: Make sure the generated test playbook is correct, and saved in the relevant location.
        """
        tmpdir.mkdir("some_folder")
        output = tmpdir.join("some_folder")
        generator = PlaybookTestsGenerator(
            input=TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH,
            file_type='integration',
            output=output,
            name='TestPlaybook',
            use_all_brands=False
        )

        generator.run()

        expected_test_playbook_yml = Path(TestGenerateTestPlaybook.TEST_FILE_PATH /
                                          'fake_integration_expected_test_playbook.yml').read_text()
        actual_test_playbook_yml = output.join('playbook-TestPlaybook_Test.yml').read_text('utf8')

        assert expected_test_playbook_yml == actual_test_playbook_yml

    def test_generate_test_playbook__specified_output_file(self, tmpdir):
        """
        Given: an integration yaml, and a specified output file
        When: called `generate_test_playbook`
        Then: Make sure the generated test playbook is correct, and saved in the relevant location.
        """
        tmpdir.mkdir("some_folder")
        output = tmpdir.join("some_folder").join("dest_file.yml")

        generator = PlaybookTestsGenerator(
            input=TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH,
            file_type='integration',
            output=output,
            name='TestPlaybook',
            use_all_brands=False
        )

        generator.run()

        expected_test_playbook_yml = Path(TestGenerateTestPlaybook.TEST_FILE_PATH /
                                          'fake_integration_expected_test_playbook.yml').read_text()
        actual_test_playbook_yml = output.read_text('utf8')

        assert expected_test_playbook_yml == actual_test_playbook_yml

    def test_generate_test_playbook__specified_non_yml_output_file(self, tmpdir):
        """
        Given: an integration yaml, and a specified output file that is NOT a yml file
        When: called `generate_test_playbook`
        Then: Make sure a relevant message is shown to user.
        """
        tmpdir.mkdir("some_folder")
        output = tmpdir.join("some_folder").join("dest_file.not_yml")

        with pytest.raises(PlaybookTestsGenerator.InvalidOutputPathError):
            generator = PlaybookTestsGenerator(
                input=TestGenerateTestPlaybook.DUMMY_INTEGRATION_YML_PATH,
                file_type='integration',
                output=output,
                name='TestPlaybook',
                use_all_brands=False
            )
            generator.run()
