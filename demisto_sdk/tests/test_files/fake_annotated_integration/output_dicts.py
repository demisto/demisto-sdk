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


def grid_field_result():
    return [
        {
            "associatedToAll": True,
            "caseInsensitive": True,
            "version": -1,
            "sla": 0,
            "shouldCommit": True,
            "threshold": 72,
            "propagationLabels": [
                "all"
            ],
            "name": "This is some example data",
            "isReadOnly": False,
            "editForm": True,
            "commitMessage": "Field edited",
            "type": "grid",
            "defaultRows": [
                {}
            ],
            "unsearchable": False,
            "breachScript": "",
            "shouldPublish": True,
            "description": "Auto Generated",
            "columns": [
                {
                    "displayName": "example_attr",
                    "isReadOnly": False,
                    "required": False,
                    "isDefault": True,
                    "type": "shortText",
                    "width": 150,
                    "script": "",
                    "fieldCalcScript": "",
                    "key": "exampleattr"
                }
            ],
            "group": 0,
            "required": False
        }
    ]


def integration_params_result():
    return [
        {
            "name": "example_integration_param",
            "type": 0,
            "display": "Example Param"
        },
        {
            "name": "credentials",
            "type": 9
        }
    ]


def full_fake_integration_result_dict():
    return {
        "category": "Authentication",
        "description": "",
        "commonfields": {
            "id": "fake_annotated_integration",
            "version": -1
        },
        "name": "fake_annotated_integration",
        "display": "fake annotated integration",
        "configuration": [
            {
                "name": "example_integration_param",
                "type": 0,
                "display": "Example Param"
            },
            {
                "name": "credentials",
                "type": 9
            }
        ],
        "script": {
            "commands": [
                {
                    "deprecated": False,
                    "description": "This is an example command with a simple, mandatory string argument.",
                    "name": "fake-command",
                    "arguments": [
                        {
                            "name": "fake_argument",
                            "isArray": False,
                            "description": "This is a fake argument",
                            "required": True,
                            "secret": False,
                            "default": False
                        }
                    ],
                    "outputs": [
                        {
                            "contextPath": "Example.example_attr",
                            "type": "Unknown",
                            "description": "An Example output attribute"
                        }
                    ]
                },
                {
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
                },
                {
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
                },
                {
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
            ],
            "script": "-",
            "type": "python",
            "subtype": "python3",
            "dockerimage": "demisto/python3:latest",
            "feed": False,
            "fetch": False,
            "runonce": False
        }
    }

def example_merge_integration_dict():
    return {
        "script": {
            "commands": [
                {
                    "name": "old_command_name",
                    "description": "old"
                }
            ]

        }
    }


def example_new_integration_dict():
    return {
        "script": {
            "commands": [
                {
                    "name": "old_command_name",
                    "description": "updated"
                },
                {
                    "name": "new_command_name",
                    "description": "new"
                },
            ]

        }
    }