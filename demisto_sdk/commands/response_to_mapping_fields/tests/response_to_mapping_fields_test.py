from demisto_sdk.commands.response_to_mapping_fields.response_to_mapping_fields import \
    ResponseToMappingFields

response_to_scheme = ResponseToMappingFields()


class TestCreateScheme:
    def test_one_layer_dict(self):
        dct = {'input': 'output'}
        assert {'input': 'str'} == response_to_scheme._create_scheme(dct)

    def test_layered_dict(self):
        dct = {'input': {'input': 2}}
        assert {'input': {'input': 'int'}} == response_to_scheme._create_scheme(dct)

    def test_int(self):
        dct = 8
        assert 'int' == response_to_scheme._create_scheme(dct)

    def test_dict_including_list(self):
        dct = {'input': [8]}
        assert {'input': 'int'} == response_to_scheme._create_scheme(dct)

    def test_dict_including_list_of_dicts(self):
        dct = {'input': [{'input': ''}, {'input': ''}]}
        assert {'input': {'input': 'str'}} == response_to_scheme._create_scheme(dct)

    def test_empty_list(self):
        assert 'list' == response_to_scheme._create_scheme([])

    def test_different_types_list(self):
        dct = {'input': [1, '']}
        assert response_to_scheme._create_scheme(dct)['input']

    def test_different_dicts_value_list(self):
        dct = [{'input': 0}, {'input': ''}]
        assert response_to_scheme._create_scheme(dct)['input']

    def test_none(self, capsys):
        assert 'NoneType' == response_to_scheme._create_scheme(None)
