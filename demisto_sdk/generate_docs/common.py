from demisto_sdk.common.tools import *
import subprocess


def save_output(path, file_name, content):
    output = os.path.join(path, file_name)

    doc_file = open(output, "w")
    doc_file.write(content)
    doc_file.close()

    subprocess.run(['open', output], check=True)
    print_color(f'Output file was saved to :\n{output}', LOG_COLORS.GREEN)


def generate_section(title, data):
    section = [
        '## {}'.format(title),
        '---',
        '',
    ]
    if data is not None:
        section.extend(add_lines(data))
    return section


def generate_list_section(title, data, empty_message=''):
    section = []
    if title:
        section.append(f'## {title}')

    if not data:
        section.extend([empty_message, ''])
        return section

    data.sort()
    for item in data:
        section.append(f'* {item}')
    section.append('')
    return section


def generate_list_with_text_section(title, data, empty_message='', text=''):
    section = []
    if title:
        section.extend([f'## {title}', '---'])

    if not data:
        section.extend([empty_message, ''])
        return section

    section.append(text)
    data.sort()
    for item in data:
        section.append(f'* {item}')
    section.append('')
    return section


def generate_table_section(data, title, empty_message='', text=''):
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
            tmp_item += f' {item.get(key)} |'
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
