from demisto_sdk.common.tools import *


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


def generate_section(title, data):
    """
    Generate simple section in markdown format.
    :param title: The section title.
    :param data: The section text.
    :return: array of strings contains the section lines in markdown format.
    """
    section = [
        '## {}'.format(title),
        '---',
        '',
    ]
    if data:
        section.extend(add_lines(data))
    return section


def generate_list_section(title, data, horizontal_rule=False, empty_message='', text='', header_type=HEADER_TYPE.H2):
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


def generate_table_section(data, title, empty_message='', text=''):
    """
    Generate table in markdown format.
    :param data: list of dicts contains the table data.
    :param title: The table header.
    :param empty_message: message to print when there is no data.
    :param text: message to print after table header.
    :return: array of strings contains the table in markdown format.
    """
    section = [f'## {title}', '---']

    if not data:
        section.extend([empty_message, ''])
        return section

    section.extend([text, '|', '|'])
    for key in data[0]:
        section[3] += f' **{key}** |'
        section[4] += ' --- |'

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
