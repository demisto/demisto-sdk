
def test_build_rn_template():
    expected_result = "<details>\n<summary>HelloWorld</summary>\n\n#### Integrations\n- __test_integration__\n%%UPDATE_RN%%\n</details>"
    from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
    update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
    changed_items = {"test_integration": "Integration"}
    release_notes = update_rn.build_rn_template(changed_items)
    assert expected_result == release_notes


def test_format_filename():
    expected_result = "sample test"
    from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
    update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
    filepath = 'sample_test.md'
    filename = update_rn.format_filename(filepath)
    assert expected_result == filename
