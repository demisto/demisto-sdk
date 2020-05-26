import json

from pathlib import Path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotes:
    """ A class that mocks a release note update in a pack.

    Args:
        repo_path: The path to the root of repository.
        pack_name: The name of the pack.
        metadata_path: The pack's pack_metadata.json full path.
        added_files: A list of the files added in the last update.
        update_type: The update type: 'revision', 'minor' or 'major'.
        pre_release: whether or not the update is a pre-release version.

    Attributes:
        pack_path (Path): The path to the pack's dir.
        update_rn (str): The update type: 'revision', 'minor' or 'major'.
        file_path (str): The release notes file full path.
        metadata_path (Path):  The pack's pack_metadata.json full path.

    """
    def __init__(self, repo_path: str, pack_name: str, metadata_path: str, added_files: set,
                 update_type: str = None, pre_release: bool = False):
        packs_path = Path(repo_path) / 'Packs'
        self.pack_path = packs_path / pack_name
        added_files = [str(f) for f in added_files]
        self.update_rn = UpdateRN(pack_name, update_type, set(), added_files, pre_release)
        self.update_rn.pack_path = self.pack_path
        self.file_path = ''
        self.metadata_path = metadata_path

    def execute_update(self):
        """ Executes the release notes update, and gets its file_path.
        """
        self.update_rn.execute_update()

        # update file_path
        with open(self.metadata_path, 'r') as metadata_file:
            pack_metadata = json.load(metadata_file)
            filename = pack_metadata.get('currentVersion').replace('.', '_') + '.md'
            self.file_path = str(Path(self.pack_path) / 'ReleaseNotes' / filename)

    def fill(self, text='This is a release note.'):
        """ Replaces all appearances of '%%UPDATE_RN%%' in the file, in order to make it valid.

            Args:
                text (str): The string to be replaced with '%%UPDATE_RN%%'.
        """
        with open(self.file_path, 'r+') as rn_file:
            rn_content = rn_file.read()
            rn_file.seek(0)
            rn_file.write(rn_content.replace('%%UPDATE_RN%%', text))
