def fake_command_dict():
    return {
        'deprecated': False,
        'description': 'This is an example command with a simple, mandatory string argument.',
        'name': 'fake-command', 'arguments':
            [
                {
                    'name': 'fake_argument', 'isArray': False, 'description': 'This is a fake argument',
                    'required': True, 'secret': False, 'default': False
                }
            ],
        'outputs': [
            {
                'contextPath': 'Example.example_attr', 'type': 'Unknown',
                'description': 'An Example output attribute'
            }
        ]
    }


def fake_command_optional_argument_dict():
    return {
        "deprecated": False,
        "description": "This is an example command with a simple, optional argument with a default value.",
        "name": "fake-command-optional-argument",
        "arguments": [
            {
                "name": "fake_optional_argument",
                "isArray": False,
                "description": "This is a fake argument",
                "required": False,
                "secret": False,
                "default": False,
                "defaultValue": "default_value"
            }
        ],
        "outputs": None
    }


def fake_command_enum_argument_dict():
    return {
        "deprecated": False,
        "description": "This is an example command with a mandatory argument with predefined values.",
        "name": "fake-command-enum-argument",
        "arguments": [
            {
                "name": "fake_enum_argument",
                "isArray": False,
                "description": "This is a fake argument",
                "required": True,
                "secret": False,
                "default": False,
                "predefined": [
                    "FirstOption",
                    "SecondOption"
                ],
                "auto": "PREDEFINED"
            }
        ],
        "outputs": None
    }


def fake_command_list_argument_dict():
    return {
        "deprecated": False,
        "description": "This is an example command with a list argument.",
        "name": "fake-command-list-argument",
        "arguments": [
            {
                "name": "fake_list_argument",
                "isArray": True,
                "description": "This is a fake argument",
                "required": True,
                "secret": False,
                "default": False
            }
        ],
        "outputs": None
    }
