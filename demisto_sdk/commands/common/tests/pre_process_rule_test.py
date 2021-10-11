from demisto_sdk.commands.common.hook_validations.pre_process_rule import \
    PreProcessRuleValidator


class TestListsValidator:

    def test_(self):
        """
        Given
        - A context field name
        When
        - The fieldname can be surrounded by ${}
        Then
        - Return the field name itself
        """

        assert 'foo1' == PreProcessRuleValidator.get_field_name('foo1')
        assert 'foo2' == PreProcessRuleValidator.get_field_name('${foo2')
        assert 'foo3' == PreProcessRuleValidator.get_field_name('foo3}')
        assert 'foo4' == PreProcessRuleValidator.get_field_name('${foo4}')
