import re


with open('/Users/meichler/dev/demisto/content/Packs/TrendMicroDeepSecurity/ModelingRules/TrendMicroDeepSecurity/TrendMicroDeepSecurity.xif') as f:
    TEXT = f.read()

MODEL_REGEX = re.compile(
    r"(?P<model_header>\[MODEL:[\w\W]*?\])(\s*(^\s*?(?!\s*\[MODEL:[\w\W]*?\])(?!\s*\[RULE:[\w\W]*?\]).*?$))+",
    flags=re.M,
)
RULE_REGEX = re.compile(
    r"(?P<rule_header>\[RULE:\s?(?P<rule_name>[\w\W]*?)\])(\s*(^\s*?(?!\s*\[MODEL:[\w\W]*?\])(?!\s*\[RULE:[\w\W]*?\]).*?$))+",
    flags=re.M,
)
CALL_REGEX = re.compile(
    r"call\s*(?P<rule_name>\w+)",
    flags=re.IGNORECASE,
)
FIELDS_REGEX = re.compile(
    r"XDM\.[\w\.]+(?=\s*?=\s*?\"?\w+)", flags=re.IGNORECASE
)
model_matches = MODEL_REGEX.finditer(TEXT)
rule_matches = RULE_REGEX.finditer(TEXT)
rule_name_list = [rule_match.groupdict().get('rule_name') for rule_match in RULE_REGEX.finditer(TEXT)]
rule_dict = {rule.groupdict().get('rule_name'): rule.group() for rule in RULE_REGEX.finditer(TEXT)}


def get_rule_name_regex(name: str) -> re.compile:
    return re.compile(
        rf"(?P<rule_header>\[RULE:\s?{name}\])(\s*(^\s*?(?!\s*\[MODEL:[\w\W]*?\])(?!\s*\[RULE:[\w\W]*?\]).*?$))+",
        flags=re.M,
    )


def get_rule_text(rule_name: str, modal_text: str) -> str:
    rule_content = rule_dict.get(rule_name)
    for nested_rule_name in re.findall(CALL_REGEX, rule_content):
        rule_content = get_rule_text(nested_rule_name, rule_content)
    return re.sub(rf'call {rule_name}', rule_content, modal_text)


for modal_match in MODEL_REGEX.finditer(TEXT):
    modal_group = modal_match.group()
    for rule_name in re.findall(CALL_REGEX, modal_group):
        modal_group = get_rule_text(rule_name, modal_group)

    print(modal_group)


rule_a = 'rule a: 1'
rule_b = 'rule b: 2'
rule_c = '<rule_b>, rule c: 3'

model_a = '<rule a>: a'
model_b = '<rule c>: bc'
