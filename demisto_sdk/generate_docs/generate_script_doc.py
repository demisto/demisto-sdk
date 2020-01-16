from os import path

from demisto_sdk.generate_docs.common import *
from demisto_sdk.common.scripts.update_id_set import get_script_data


def generate_script_doc(input, output, commands, id_set, verbose=False):
    try:
        # output and id_set.json validations
        if not path.isdir(output):
            print_error(f'Error: output directory not found in {output}')
            return

        if not id_set:
            print_error('Error: Missing option "-id" / "--id_set".')
            return

        if not path.exists(id_set):
            print_error(f'Error: id_set.json not found in {id_set}')
            return

        # set script_py and script.yml values
        if path.isdir(input):
            # in case of package folder
            package_folder = os.path.basename(input)
            script_yml = os.path.join(input, f'{package_folder}.yml')
            script_py = os.path.join(input, f'{package_folder}.py')
            if not path.exists(script_yml):
                print_error(f'Error: script yml file not found in {script_yml}')
                return
            if not path.exists(script_py):
                print_error(f'Error: script python file not found in {script_py}')
                return

            with open(script_py) as f:
                script_py = f.read()
        else:
            # in case of unified script file
            script = get_yaml(input)
            script_py = script.get('script', '-')
            if script_py == '-':
                print_error(f'Error: script code not found in {input}')
                return
            script_yml = input

        doc = []
        errors = []
        script = get_yaml(script_yml)

        # get script dependencies
        script_data = get_script_data(script_yml, script_py)
        script_data = script_data[list(script_data.keys())[0]]
        dependencies = script_data.get('script_executions', [])

        # get script data
        secript_info = get_script_info(script_yml)
        script_id = script.get('commonfields')['id']

        used_in = get_used_in(id_set, script_id)

        description = script.get('comment', '')
        deprecated = script_data.get('deprecated', False)
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

        doc.extend(generate_list_with_text_section('Dependencies', dependencies,
                                                   'No dependencies found.',
                                                   'This script uses the following commands and scripts.'))

        doc.extend(generate_table_section(inputs, 'Inputs', 'There are no inputs for this script.'))

        doc.extend(generate_table_section(outputs, 'Outputs', 'There are no outputs for this script.'))

        doc.extend(generate_list_with_text_section('Used In', used_in,
                                                   'This script not used anywhere.',
                                                   'This script is used in the following playbooks and scripts.'))

        doc_text = '\n'.join(doc)

        save_output(output, 'README.md', doc_text)

        if errors:
            print_error('Possible Errors:')
            for error in errors:
                print_error(error)

    except Exception as ex:
        if verbose:
            raise
        else:
            print_error(f'Error: {str(ex)}')
            return


def get_script_info(script_path):
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
            'Description': stringEscapeMD(arg.get('description', '')),
            'Type': ''
        })

    return inputs, errors


def get_outputs(script):
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
            'Type': arg.get('type')
        })

    return outputs, errors


def get_used_in(id_set_path, script_id):
    id_set = get_json(id_set_path)
    used_in_list = []

    for key in list(id_set.keys()):
        items = id_set[key]
        for item in items:
            key = list(item.keys())[0]
            if not item[key].get('file_path', '').startswith('TestPlaybooks'):
                scripts = item[key].get('implementing_scripts', [])
                if scripts and script_id in scripts:
                    used_in_list.append(item[key].get('name', []))
    return list(filter(None, dict.fromkeys(used_in_list)))



