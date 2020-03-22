import os
import shutil
from tempfile import mkdtemp

from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.common.git_tools import git_path


class TestIDSetCreator:
    def setup(self):
        tests_dir = f'{git_path()}/demisto_sdk/tests'
        self.id_set_full_path = os.path.join(tests_dir, 'test_files', 'content_repo_example', 'id_set.json')
        self._test_dir = mkdtemp()
        self.file_path = os.path.join(self._test_dir, 'id_set.json')

    def teardown(self):
        # delete the id set file
        try:
            if os.path.isfile(self.file_path) or os.path.islink(self.file_path):
                os.unlink(self.file_path)
            elif os.path.isdir(self.file_path):
                shutil.rmtree(self.file_path)
        except Exception as err:
            print(f'Failed to delete {self.file_path}. Reason: {err}')

    def test_create_id_set_output(self):
        id_set_creator = IDSetCreator(self.file_path)

        id_set_creator.create_id_set()
        assert os.path.exists(self.file_path)

    def test_create_id_set_no_output(self):
        id_set_creator = IDSetCreator()

        id_set_creator.create_id_set()
        assert not os.path.exists(self.file_path)
