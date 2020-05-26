import json

from pathlib import Path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotes(UpdateRN):

    def __init__(self, repo_path: str, pack_name: str, metadata_path: str, added_files: set,
                 update_type: str = None, pre_release: bool = False):
        packs_path = Path(repo_path) / 'Packs'
        added_files = [str(f) for f in added_files]
        super(ReleaseNotes, self).__init__(pack_name, update_type, set(), added_files, pre_release)
        self.pack_path = str(packs_path / pack_name)
        self.file_path = ''
        self.metadata_path = metadata_path

    def execute_update(self):
        super(ReleaseNotes, self).execute_update()

        # update file_path
        with open(self.metadata_path, 'r') as metadata_file:
            pack_metadata = json.load(metadata_file)
            filename = pack_metadata.get('currentVersion').replace('.', '_') + '.md'
            self.file_path = str(Path(self.pack_path) / 'ReleaseNotes' / filename)

    def fill(self, text):
        with open(self.file_path, 'r+') as rn_file:
            rn_content = rn_file.read()
            rn_file.seek(0)
            rn_file.write(rn_content.replace('%%UPDATE_RN%%', text))
