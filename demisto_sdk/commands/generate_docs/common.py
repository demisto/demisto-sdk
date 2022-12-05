import html
import os.path
import re
from typing import Dict, List, Tuple

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import LOG_COLORS, print_color, print_warning, run_command
from demisto_sdk.commands.run_cmd.runner import Runner

json = JSON_Handler()


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

    with open(output, mode="w", encoding="utf8") as doc_file:
        doc_file.write(content)
    add_file_to_git(output)
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


def generate_numbered_section(title: str, data: str = ''):
    """
    Generate numbered section in markdown format.
    :param title: The section title.
    :param data: The section text.
    :return: array of strings contains the section lines in markdown format.
    """
    section = [
        '## {}'.format(title)
    ]

    list_data = data.split('* ')
    if list_data:
        for i, item in enumerate(list_data):
            if item:
                section.append(f'{i}. {item.rstrip()}')

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


def generate_table_section(data: list, title: str, empty_message: str = '', text: str = '',
                           horizontal_rule: bool = True, numbered_section: bool = False):
    """
    Generate table in markdown format.
    :param data: list of dicts contains the table data.
    :param title: The table header.
    :param empty_message: message to print when there is no data.
    :param text: message to print after table header.
    :param horizontal_rule: add horizontal rule after title.
    :param numbered_section: is the table part of numbered sections.
    :return: array of strings contains the table in markdown format.
    """
    section = []
    if title:
        section.append(f'## {title}')

    if horizontal_rule:
        section.append('---')

    if not data:
        if empty_message:
            section.extend([empty_message, ''])
        else:
            section = ['']
        return section

    section.extend([text, '    |', '    |']) if numbered_section else section.extend([text, '|', '|'])
    header_index = len(section) - 2
    for key in data[0]:
        section[header_index] += f' **{key}** |'
        section[header_index + 1] += ' --- |'

    for item in data:
        tmp_item = '    |' if numbered_section else '|'
        escape_less_greater_signs = 'First fetch time' in item  # instead of html escaping
        for key in item:
            escaped_string = string_escape_md(str(item.get(key, '')), minimal_escaping=True, escape_multiline=True,
                                              escape_less_greater_signs=escape_less_greater_signs)
            tmp_item += f" {escaped_string} |"
        section.append(tmp_item)

    section.append('')
    return section


def add_lines(line):
    output = re.findall(r'^\d+\..+', line, re.MULTILINE)
    return output if output else [line]


def string_escape_md(st, minimal_escaping=False, escape_multiline=False, escape_html=True,
                     escape_less_greater_signs=False):
    """
       Escape any chars that might break a markdown string

       :type st: ``str``
       :param st: The string to be modified (required)

       :type minimal_escaping: ``bool``
       :param minimal_escaping: Whether replace all special characters or table format only (optional)

       :type escape_multiline: ``bool``
       :param escape_multiline: Whether convert line-ending characters (optional)

       :type escape_html: ``bool``
       :param escape_html: Whether to escape html (<,>,&) (default: True). Set to false if the string contains
            html tags. Otherwise this should be true to support MDX complaint docs.

       :type escape_less_greater_signs: ``bool``
       :param escape_less_greater_signs: Whether to escape (<,>) (default: False) with (`<,>`).
            Set to true for first fetch time param. called instead of the escape_html.

       :return: A modified string
       :rtype: ``str``
    """

    if escape_less_greater_signs:
        st = st.replace('<', '`<')
        st = st.replace('>', '>`')
        st = st.replace('&', '`&`')
    elif escape_html:
        st = html.escape(st, quote=False)

    if escape_multiline:
        st = st.replace('\r\n', '<br/>')  # Windows
        st = st.replace('\r', '<br/>')  # old Mac
        st = st.replace('\n', '<br/>')  # Unix

    if minimal_escaping:
        for c in '|':
            st = st.replace(c, '\\' + c)
    else:
        st = "".join(f'\\{str(c)}' if c in r"\`*{}[]()#+!" else str(c) for c in st)

        # The following code adds an escape character for '-' and '_' following cases:
        # 1. The string begins with a dash. e.g: - This input specifies the entry id
        # 2. The string has a word which wrapped with an underscore in it. e.g: This input _specifies_ the entry id
        # in the underscore case we use a for loop because of a problem with concatenate backslash with a subgroup.
        st = re.sub(r'(\A-)', '\\-', st)

        added_char_count = 1
        for match in re.finditer(r'([\s.,()])(_\S*)(_[\s.,()])', st):
            # In case there is more than one match, the next word index get changed because of the added escape chars.
            st = st[:match.regs[0][0] + added_char_count] + '\\' + st[match.regs[0][0] + added_char_count:]
            st = st[:match.regs[3][0] + added_char_count] + '\\' + st[match.regs[3][0] + added_char_count:]
            added_char_count += 2

    return st


def execute_command(command_example, insecure: bool):
    errors = []
    context = {}
    md_example: str = ''
    cmd = command_example
    try:
        runner = Runner('', insecure=insecure)
        res, raw_context = runner.execute_command(command_example)
        if not res:
            raise RuntimeError('something went wrong with your command: {}'.format(command_example))

        for entry in res:
            if is_error(entry):
                raise RuntimeError('something went wrong with your command: {}'.format(command_example))

            if raw_context:
                context = {k.split('(')[0]: v for k, v in raw_context.items()}

            if entry.contents:
                content: str = entry.contents
                if isinstance(content, STRING_TYPES):
                    md_example = format_md(content)
                else:
                    md_example = f'```\n{json.dumps(content, sort_keys=True, indent=4)}\n```'

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


def build_example_dict(command_examples: list, insecure: bool) -> Tuple[Dict[str, List[Tuple[str, str, str]]], List[str]]:
    """
    gets an array of command examples, run them one by one and return a map of
        {base command -> [(example command, markdown, outputs), ...]}.
    """
    examples = {}  # type: dict
    errors = []  # type: list
    for example in command_examples:
        name, md_example, context_example, cmd_errors = execute_command(example, insecure)
        if 'playbookQuery' in context_example:
            del context_example['playbookQuery']

        context_example = json.dumps(context_example, indent=4)
        errors.extend(cmd_errors)

        if not cmd_errors:
            if name not in examples:
                examples[name] = []
            examples[name].append((example, md_example, context_example))
    return examples, errors


def format_md(md: str) -> str:
    """
    Formats a given md string by replacing <br> and <hr> tags with <br/> or <hr/>
    Will also remove style tags such as: style="background:#eeeeee; border:1px solid #cccccc; padding:5px" which cause mdx to fail
    :param
        md (str): String representing mark down.
    :return:
        str. Formatted string representing mark down.
    """
    replace_tuples = [
        (r'<br>(</br>)?', '<br/>'),
        (r'<hr>(</hr>)?', '<hr/>'),
        (r'style="[a-zA-Z0-9:;#\.\s\(\)\-\,]*?"', ''),
    ]
    if md:
        for old, new in replace_tuples:
            md = re.sub(old, new, md, flags=re.IGNORECASE)
    return md


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


def add_file_to_git(file_path: str):
    try:
        run_command(f'git add {file_path}', exit_on_error=False)
    except RuntimeError:
        print_warning(f'Could not add the following file to git: {file_path}')
