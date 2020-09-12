from content import Content

content = Content.from_cwd()
x = content.packs['Akamai_WAF']
for integration in x.integrations:
    print(integration.code_path)
