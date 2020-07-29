from demisto_sdk.commands.common.content import ContentDescriptor


def test_changelog_prefix(datadir):
    obj = ContentDescriptor(datadir['content-descriptor.json'])
    assert obj._normalized_file_name() == 'content-descriptor.json'
