from pathlib import Path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotes(UpdateRN):
    def __init__(self, temp_path: Path, pack: str, pack_files: set, added_files: set, update_type: str = None,
                 pre_release: bool = False):
        super(ReleaseNotes, self).__init__(temp_path, pack, update_type, pack_files, added_files, pre_release)
        self.pack_path = temp_path / pack
        self.metadata_path = self.pack_path / 'pack_metadata.json'

    def execute_update(self):
        super(ReleaseNotes, self).execute_update()
