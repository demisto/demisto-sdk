import os

from demisto_sdk.commands.common.tools import (get_from_version, get_yaml,
                                               print_error, print_warning)
from demisto_sdk.commands.common.update_id_set import get_depends_on
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.generate_docs.common import (
    build_example_dict, generate_list_section, generate_numbered_section,
    generate_section, generate_table_section, save_output, string_escape_md)


def generate_script_doc(input, examples, output: str = None, permissions: str = None,
                        limitations: str = None, insecure: bool = False, verbose: bool = False):
    try:
        doc: list = []
        errors: list = []
        example_section: list = []

        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input))

        if examples:
            if not examples.startswith('!'):
                examples = f'!{examples}'

            example_dict, build_errors = build_example_dict([examples], insecure)
            script_name = examples.split(' ')[0][1:]
            example_section, example_errors = generate_script_example(script_name, example_dict)
            errors.extend(build_errors)
            errors.extend(example_errors)
        else:
            errors.append('Note: Script example was not provided. For a more complete documentation,run with the -e '
                          'option with an example command. For example: -e "!ConvertFile entry_id=<entry_id>".')

        script = get_yaml(input)

        # get script data
        secript_info = get_script_info(input)
        script_id = script.get('commonfields')['id']

        # get script dependencies
        dependencies, _ = get_depends_on(script)

        # get the script usages by the id set
        id_set_creator = IDSetCreator()
        id_set = id_set_creator.create_id_set()
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

        doc.extend(generate_table_section(secript_info, 'Script Data'))

        if dependencies:
            doc.extend(generate_list_section('Dependencies', dependencies, True,
                                             text='This script uses the following commands and scripts.'))

        # Script global permissions
        if permissions == 'general':
            doc.extend(generate_section('Permissions', ''))

        if used_in:
            doc.extend(generate_list_section('Used In', used_in, True,
                                             text='This script is used in the following playbooks and scripts.'))

        doc.extend(generate_table_section(inputs, 'Inputs', 'There are no inputs for this script.'))

        doc.extend(generate_table_section(outputs, 'Outputs', 'There are no outputs for this script.'))

        if example_section:
            doc.extend(example_section)

        # Known limitations
        if limitations:
            doc.extend(generate_numbered_section('Known Limitations', limitations))

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

    tags = script.get('tags', [])
    tags = ', '.join(map(str, tags))

    from_version = get_from_version(script_path)

    return [{'Name': 'Script Type', 'Description': script_type},
            {'Name': 'Tags', 'Description': tags},
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
            'Description': string_escape_md(arg.get('description', ''))
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
            'Description': string_escape_md(arg.get('description', '')),
            'Type': arg.get('type', 'Unknown')
        })

    return outputs, errors


def get_used_in(id_set, script_id):
    """
    Gets the integrations, scripts and playbooks that used the input script, without test playbooks.
    :param id_set: updated id_set object.
    :param script_id: the script id.
    :return: list of integrations, scripts and playbooks that used the input script
    """
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
    if example:
        script_example = example[script_name][0]
        md_example = example[script_name][1]
        context_example = example[script_name][2]
    else:
        return '', [f'did not get any example for {script_name}. please add it manually.']

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
