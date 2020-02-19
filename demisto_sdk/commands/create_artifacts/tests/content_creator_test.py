import filecmp
from tempfile import mkdtemp

from demisto_sdk.commands.create_artifacts.content_creator import *
from demisto_sdk.commands.common.git_tools import git_path


class TestContentCreator:
    def setup(self):
        current_dir = f'{git_path()}/demisto_sdk/commands/create_artifacts/tests'
        self.scripts_full_path = os.path.join(current_dir, 'test_files', 'content_repo_example', 'Scripts')
        self._dir = mkdtemp()
        self.content_repo = os.path.join(current_dir, 'test_files', 'content_repo_example')

    def teardown(self):
        # delete all files in the content_bundle
        for filename in os.listdir(self._dir):
            file_path = os.path.join(self._dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as err:
                print('Failed to delete %s. Reason: %s' % (file_path, err))

    def test_copy_dir_files(self):
        """
        Given
        - valid script-<name>.yml file
        When
        - copying the content folder to a content bundle(flatten files)
        Then
        - ensure files are being flatten correctly
        - ensure no !!omap are added(due to ordereddict yaml problems)
        """
        content_creator = ContentCreator(artifacts_path=self.content_repo, content_version='2.5.0',
                                         content_bundle_path=self._dir,
                                         preserve_bundles=False)
        content_creator.copy_dir_files(self.scripts_full_path, content_creator.content_bundle)

        assert filecmp.cmp(f'{self.scripts_full_path}/script-Sleep.yml',
                           f'{self._dir}/script-Sleep.yml')
