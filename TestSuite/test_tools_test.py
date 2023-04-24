from TestSuite.test_tools import str_in_call_args_list


def test_str_in_call_args_list():
    calls_1 = [
        ((("item 1",), ("item 2",), ("item 3",))),
    ]
    assert str_in_call_args_list(
        calls_1,
        "item 1",
    )
    assert not str_in_call_args_list(
        calls_1,
        "item 3",
    )
