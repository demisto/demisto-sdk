from demisto_sdk.commands.common.content import Documentation


def test_prefix(datadir):
    obj = Documentation(datadir['doc-howto.json'])
    assert obj._normalized_file_name() == 'doc-howto.json'
