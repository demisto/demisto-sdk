from os import path
from demisto_sdk.commands.generate_docs.common import *
from demisto_sdk.commands.common.update_id_set import get_depends_on


def generate_script_doc(input, output, examples, id_set='', verbose=False):
    try:
        doc = []
        errors = []
        used_in = []
        example_section = []

        if examples:
            if not examples.startswith('!'):
                examples = f'!{examples}'

            example_dict, build_errors = build_example_dict([examples])
            script_name = examples.split(' ')[0][1:]
            example_section, example_errors = generate_script_example(script_name, example_dict)
            errors.extend(build_errors)
            errors.extend(example_errors)
        else:
            errors.append(f'Script example is missing.')

        script = get_yaml(input)

        # get script data
        secript_info = get_script_info(input)
        script_id = script.get('commonfields')['id']

        # get script dependencies
        dependencies, _ = get_depends_on(script)

        if not id_set:
            errors.append(f'id_set.json file is missing')
        elif not path.exists(id_set):
            errors.append(f'id_set.json file {id_set} was not found')
        else:
            used_in = get_used_in(id_set, script_id)

        description = script.get('comment', '')
        deprecated = script.get('deprecated', False)
        # get inputs/outputs
        inputs, inputs_errors = get_inputs(script)
        outputs, outputs_errors = get_outputs(script)

        errors.extend(inputs_errors)
        errors.extend(outputs_errors)

        if not description:
            errors.append('Error! You are missing description for the playbook')

        if deprecated:
            doc.append('`Deprecated`')

        doc.append(description)
        doc.extend(generate_list_section('',
                                         ['Script Data', 'Dependencies', 'Used In', 'Inputs', 'Outputs']))

        doc.extend(generate_table_section(secript_info, 'Script Data', text='This is the metadata of the script.'))

        if dependencies:
            doc.extend(generate_list_section('Dependencies', dependencies, True,
                                             text='This script uses the following commands and scripts.'))

        if used_in:
            doc.extend(generate_list_section('Used In', used_in, True,
                                             text='This script is used in the following playbooks and scripts.'))

        doc.extend(generate_table_section(inputs, 'Inputs', 'There are no inputs for this script.'))

        doc.extend(generate_table_section(outputs, 'Outputs', 'There are no outputs for this script.'))

        if example_section:
            doc.extend(example_section)

        doc_text = '\n'.join(doc)

        save_output(output, 'README.md', doc_text)

        if errors:
            print_warning('Possible Errors:')
            for error in errors:
                print_warning(error)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return


def get_script_info(script_path):
    """
    Gets script information(type, tags, docker image and demisto version).
    :param script_path: the script yml file path.
    :return: list of dicts contains the script information.
    """
    script = get_yaml(script_path)
    script_type = script.get('subtype')
    if not script_type:
        script_type = script.get('type')

    tags = script.get('tags')
    tags = ', '.join(map(str, tags))

    docker_images = get_docker_images(script)
    docker_images = ', '.join(map(str, docker_images))
    from_version = get_from_version(script_path)

    return [{'Name': 'Script Type', 'Description': script_type},
            {'Name': 'Tags', 'Description': tags},
            {'Name': 'Docker Image', 'Description': docker_images},
            {'Name': 'Demisto Version', 'Description': from_version}]


def get_inputs(script):
    """
    Gets script inputs.
    :param script: the script object.
    :return: list of inputs and list of errors.
    """
    errors = []
    inputs = []

    if not script.get('args'):
        return {}, []

    for arg in script.get('args'):
        if not arg.get('description'):
            errors.append(
                'Error! You are missing description in script input {}'.format(arg.get('name')))

        inputs.append({
            'Argument Name': arg.get('name'),
            'Description': stringEscapeMD(arg.get('description', ''))
        })

    return inputs, errors


def get_outputs(script):
    """
    Gets script outputs.
    :param script: the script object.
    :return: list of outputs and list of errors.
    """
    errors = []
    outputs = []

    if not script.get('outputs'):
        return {}, []

    for arg in script.get('outputs'):
        if not arg.get('description'):
            errors.append(
                'Error! You are missing description in script output {}'.format(arg.get('contextPath')))

        outputs.append({
            'Path': arg.get('contextPath'),
            'Description': stringEscapeMD(arg.get('description', '')),
            'Type': arg.get('type', 'Unknown')
        })

    return outputs, errors


def get_used_in(id_set_path, script_id):
    """
    Gets the integrations, scripts and playbooks that used the input script, without test playbooks.
    :param id_set_path: updated id_set.json file path.
    :param script_id: the script id.
    :return: list of integrations, scripts and playbooks that used the input script
    """
    id_set = get_json(id_set_path)
    used_in_list = set()

    id_set_sections = list(id_set.keys())
    id_set_sections.remove('TestPlaybooks')

    for key in id_set_sections:
        items = id_set[key]
        for item in items:
            key = list(item.keys())[0]
            scripts = item[key].get('implementing_scripts', [])
            if scripts and script_id in scripts:
                used_in_list.add(item[key].get('name', []))
    used_in_list = list(used_in_list)
    used_in_list.sort()
    return used_in_list


def generate_script_example(script_name, example=None):
    errors = []
    context_example = None
    md_example = ''
    if example is not None:
        script_example = example[script_name][0]
        md_example = example[script_name][1]
        context_example = example[script_name][2]
    else:
        errors.append(f'did not get any example for {script_name}. please add it manually.')

    example = [
        '',
        '## Script Example',
        '```{}```'.format(script_example),
        '',
    ]
    if context_example:
        example.extend([
            '## Context Example',
            '```',
            '{}'.format(context_example),
            '```',
            '',
        ])

        if md_example:
            example.extend([
                '## Human Readable Output',
                '{}'.format(md_example),
                '',
            ])

    return example, errors
