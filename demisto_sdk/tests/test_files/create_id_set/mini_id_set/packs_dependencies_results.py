first_iteration = {
    'ExcludedPack': {
        'packsDependentOnThisPackMandatorily': {
                'PackDependentOnExcludedPack1': {
                    'mandatory': True,
                    'dependent_items': [
                        (
                            ('integration', 'ExcludedPack_integration'),
                            [('playbook', 'dummy_playbook')]
                        )
                    ]
                }
            },
            'path': 'Packs/ExcludedPack',
            'fullPath': 'content/Packs/ExcludedPack'
        }
    }

second_iteration = {
    'PackDependentOnExcludedPack1': {
        'packsDependentOnThisPackMandatorily': {
                'PackDependentOnExcludedPack2': {
                    'mandatory': True,
                    'dependent_items': [
                        (
                            ('playbook', 'dummy_playbook'),
                            [('playbook', 'dummy_playbook1')]
                        )
                    ]
                }
        },
        'path': 'Packs/PackDependentOnExcludedPack2',
        'fullPath': 'content/Packs/PackDependentOnExcludedPack2'
    }
}
