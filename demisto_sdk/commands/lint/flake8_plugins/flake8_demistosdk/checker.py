import re

D100 = 'D100 Direct Dict key access'


def direct_dict_key_access(physical_line, tokens):
    for token_type, text, start, _, _ in tokens:
        if re.search(r'[\w\d_]+\[[\'"].*[\'"]\]', physical_line):
            # look for string with pattern of direct dict key access (['*'] or ["*"])
            if not re.search(r'(^\s*[\w\d_]+\[([\'\"]).*?\2\])', physical_line):
                # make sure the pattern is not on the left side of a `=` sign
                return start[1], D100


direct_dict_key_access.name = 'direct_dict_key_access'
direct_dict_key_access.version = '0.1.0'
