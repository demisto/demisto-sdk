from pathlib import Path

from demisto_sdk.commands.common.content import YAMLConentObject


def test_from_version_no_to_version(datadir):
    from packaging.version import parse
    directory = Path(datadir['sample.yaml']).parent
    obj = YAMLConentObject(directory, "sample")
    assert obj.from_version == parse("3.0.0")
    assert obj.to_version == parse("99.99.99")


def test_to_version_no_from_version(datadir):
    from packaging.version import parse
    directory = Path(datadir['sample.yaml']).parent
    obj = YAMLConentObject(directory, "sample")
    assert obj.from_version == parse("0.0.0")
    assert obj.to_version == parse("3.0.0")


class TestFileWithStem:
    def test_with_readme_change_log(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is not None
        assert obj.changelog is not None

    def test_with_readme_without_changelog(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is not None
        assert obj.changelog is None

    def test_without_readme_changelog(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is None
        assert obj.changelog is None

    def test_dump(self, datadir):
        from filecmp import dircmp
        from shutil import rmtree
        directory = Path(datadir['sample.yaml']).parent
        dump_directory = directory / 'temp'
        obj = YAMLConentObject(directory, "sample")
        obj.dump(directory / 'temp')

        diff = dircmp(directory, dump_directory)
        assert diff.common == [obj.changelog.path.name, obj.readme.path.name]
        assert diff.right_only == ["sample-sample.yaml"]
        # Temp dir in their so ignore it
        left_only = diff.left_only
        left_only.remove(dump_directory.name)
        assert left_only == ["sample.yaml"]

        rmtree(dump_directory)


class TestFileWithoutStem:
    def test_with_readme_change_log(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is not None
        assert obj.changelog is not None

    def test_with_readme_without_changelog(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is not None
        assert obj.changelog is None

    def test_without_readme_changelog(self, datadir):
        directory = Path(datadir['sample.yaml']).parent
        obj = YAMLConentObject(directory, "sample")

        assert obj.readme is None
        assert obj.changelog is None

    def test_dump(self, datadir):
        from filecmp import dircmp
        from shutil import rmtree
        directory = Path(datadir['sample.yaml']).parent
        dump_directory = directory / 'temp'
        obj = YAMLConentObject(directory, "sample")
        obj.dump(directory / 'temp')

        diff = dircmp(directory, dump_directory)
        assert diff.common == [obj.changelog.path.name, obj.readme.path.name]
        assert diff.right_only == ["sample-sample.yaml"]
        # Temp dir in their so ignore it
        left_only = diff.left_only
        left_only.remove(dump_directory.name)
        assert left_only == ["sample.yaml"]

        rmtree(dump_directory)
