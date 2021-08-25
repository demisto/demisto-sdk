from demisto_sdk.commands.common.content.objects.pack_objects import \
    ReleaseNoteConfig
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


class TestReleaseNoteConfig:
    def test_objects_factory(self, pack):
        """
        Given:
        - RN config path.

        When:
        - Converting path to pack object.

        Then:
        - Ensure ReleaseNotesConfig object is returned.
        """
        rn_config = pack.create_release_notes_config('1.0.1', {'breakingChanges': True})
        assert isinstance(path_to_pack_object(str(rn_config.path)), ReleaseNoteConfig)

    def test_prefix(self, pack):
        """
        Given:
        - RN config path.

        When:
        - Checking object corresponding to path file name.

        Then:
        - Ensure expected name is returned.
        """
        rn_config = pack.create_release_notes_config('1.0.1', {'breakingChanges': True})
        obj = ReleaseNoteConfig(str(rn_config.path))
        assert obj.normalize_file_name() == rn_config.name
