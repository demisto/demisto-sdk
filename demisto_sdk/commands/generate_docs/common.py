import os.path
import re
import json
from demisto_sdk.commands.common.tools import print_color, LOG_COLORS
from demisto_sdk.commands.run_cmd.runner import Runner

STRING_TYPES = (str, bytes)  # type: ignore


class HEADER_TYPE:
    H1 = '#'
    H2 = '##'
    H3 = '###'


def save_output(path, file_name, content):
    """
    Creates the output file in path.
    :param path: the output path for saving the file.
    :param file_name: the name of the file.
    :param content: the content of the file.
    """
    output = os.path.join(path, file_name)

    with open(output, "w") as doc_file:
        doc_file.write(content)

    print_color(f'Output file was saved to :\n{output}', LOG_COLORS.GREEN)


def generate_section(title, data=''):
    """
    Generate simple section in markdown format.
    :param title: The section title.
    :param data: The section text.
    :return: array of strings contains the section lines in markdown format.
    """
    section = [
        '## {}'.format(title),
        ''
    ]
    if data:
        section.extend(add_lines(data))
    return section


def generate_list_section(title, data='', horizontal_rule=False, empty_message='', text='', header_type=HEADER_TYPE.H2):
    """
     Generate list section in markdown format.
     :param data: list of strings.
     :param title: The list header.
     :param horizontal_rule: add horizontal rule after title.
     :param empty_message: message to print when the list is empty.
     :param text: message to print after the header.
     :param header_type: markdown header type - H1, H2 or H3, the default is H2.
     :return: array of strings contains the list section in markdown format.
     """
    section = []
    if title:
        section.append(f'{header_type} {title}')

    if horizontal_rule:
        section.append('---')

    if not data:
        section.extend([empty_message, ''])
        return section

    if text:
        section.append(text)
    for item in data:
        section.append(f'* {item}')
    section.append('')
    return section


def generate_table_section(data, title, empty_message='', text='', horizontal_rule=True):
    """
    Generate table in markdown format.
    :param data: list of dicts contains the table data.
    :param title: The table header.
    :param empty_message: message to print when there is no data.
    :param text: message to print after table header.
    :param horizontal_rule: add horizontal rule after title.
    :return: array of strings contains the table in markdown format.
    """
    section = []
    if title:
        section.append(f'## {title}')

    if horizontal_rule:
        section.append('---')

    if not data:
        section.extend([empty_message, ''])
        return section

    section.extend([text, '|', '|'])
    header_index = len(section) - 2
    for key in data[0]:
        section[header_index] += f' **{key}** |'
        section[header_index + 1] += ' --- |'

    for item in data:
        tmp_item = '|'
        for key in item:
            tmp_item += f" {item.get(key,'')} |"
        section.append(tmp_item)

    section.append('')
    return section


def add_lines(line):
    output = re.findall(r'^\d+\..+', line, re.MULTILINE)
    return output if output else [line]


def stringEscapeMD(st, minimal_escaping=False, escape_multiline=False):
    """
       Escape any chars that might break a markdown string

       :type st: ``str``
       :param st: The string to be modified (required)

       :type minimal_escaping: ``bool``
       :param minimal_escaping: Whether replace all special characters or table format only (optional)

       :type escape_multiline: ``bool``
       :param escape_multiline: Whether convert line-ending characters (optional)

       :return: A modified string
       :rtype: ``str``
    """
    if escape_multiline:
        st = st.replace('\r\n', '<br>')  # Windows
        st = st.replace('\r', '<br>')  # old Mac
        st = st.replace('\n', '<br>')  # Unix

    if minimal_escaping:
        for c in '|':
            st = st.replace(c, '\\' + c)
    else:
        st = "".join(["\\" + str(c) if c in r"\`*_{}[]()#+-!" else str(c) for c in st])

    return st


def execute_command(command_example):
    errors = []
    context = {}
    md_example = ''
    cmd = command_example
    try:
        runner = Runner('')
        res, raw_context = runner.execute_command(command_example)
        if not res:
            raise RuntimeError('something went wrong with your command: {}'.format(command_example))

        for entry in res:
            if is_error(entry):
                raise RuntimeError('something went wrong with your command: {}'.format(command_example))

            if raw_context:
                context = {k.split('(')[0]: v for k, v in raw_context.items()}

            if entry.contents:
                content = entry.contents
                if isinstance(content, STRING_TYPES):
                    md_example += content
                else:
                    md_example += json.dumps(content)

    except RuntimeError:
        errors.append('The provided example for cmd {} has failed...'.format(cmd))

    except Exception as e:
        errors.append(
            'Error encountered in the processing of command {}, error was: {}. '.format(cmd, str(e)) +
            '. Please check your command inputs and outputs')

    cmd = cmd.split(' ')[0][1:]
    return cmd, md_example, context, errors


def is_error(execute_command_result):
    """
        Check if the given execute_command_result has an error entry

        :type execute_command_result: ``dict`` or ``list``
        :param execute_command_result: Demisto entry (required) or result of demisto.executeCommand()

        :return: True if the execute_command_result has an error entry, false otherwise
        :rtype: ``bool``
    """
    if not execute_command_result:
        return False

    if isinstance(execute_command_result, list):
        if len(execute_command_result) > 0:
            for entry in execute_command_result:
                if entry.type == entryTypes['error']:
                    return True

    # return type(execute_command_result) == dict and execute_command_result.type == entryTypes['error']
    return execute_command_result.type == entryTypes['error']


def build_example_dict(command_examples):
    """
    gets an array of command examples, run them one by one and return a map of
        {base command -> (example command, markdown, outputs)}
    Note: if a command appears more then once, run all occurrences but stores only the first.
    """
    examples = {}  # type: dict
    errors = []  # type: list
    for example in command_examples:
        cmd, md_example, context_example, cmd_errors = execute_command(example)
        if 'playbookQuery' in context_example:
            del context_example['playbookQuery']

        context_example = json.dumps(context_example, indent=4)
        errors.extend(cmd_errors)

        if not cmd_errors and cmd not in examples:
            examples[cmd] = (example, md_example, context_example)
    return examples, errors


entryTypes = {
    'note': 1,
    'downloadAgent': 2,
    'file': 3,
    'error': 4,
    'pinned': 5,
    'userManagement': 6,
    'image': 7,
    'plagroundError': 8,
    'playgroundError': 8,
    'entryInfoFile': 9,
    'warning': 11,
    'map': 15,
    'widget': 17
}
