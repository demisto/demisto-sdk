from demisto_sdk.scripts.sort_yaml import PRIORITY_FIELDS, sort_dict


def test_sort_dict_with_priority_fields():
    """
    Given:
        A dictionary with some keys that are in the PRIORITY_FIELDS list.
    When:
        Calling `sort_dict`
    Then:
        Make sure the dictionary is sorted with the priority fields first, followed by the rest of the keys in alphabetical order.
        Make sure the input is not modified.
    """
    assert len(PRIORITY_FIELDS) >= 2, "Test assumes at least 2 priority fields"
    input_dict = {
        "z": 26,
        "a": 1,
        PRIORITY_FIELDS[1]: "priority2",
        "b": 2,
        PRIORITY_FIELDS[0]: "priority1",
    }
    input_keys_before_sorting = list(
        input_dict.keys()
    )  # to check their order is preserved

    sorted_dict = sort_dict(input_dict)
    assert sorted_dict == input_dict

    assert list(input_dict.keys()) == input_keys_before_sorting

    sorted_keys = list(sorted_dict.keys())
    assert sorted_keys[:2] == list(PRIORITY_FIELDS[:2])  # priority fields come first
    assert sorted_keys[2:] == ["a", "b", "z"]  # rest should be alphabetically sorted
