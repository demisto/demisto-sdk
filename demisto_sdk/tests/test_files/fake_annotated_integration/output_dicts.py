def fake_command_dict():
    return {
        'deprecated': False,
        'description': 'This is an example command.',
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
        "description": "This is an example command.",
        "name": "fake-command-optional-argument",
        "arguments": [
            {
                "name": "fake_optional_argument",
                "isArray": False,
                "description": "This is a fake argument",
                "required": False,
                "secret": False,
                "default": False,
                "defaultValue": ""
            }
        ],
        "outputs": None
    }
