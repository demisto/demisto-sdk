import yaml

schema_path = 'demisto_sdk/commands/common/schemas/incidentfield.yml'
with open(schema_path, 'r') as file_obj:
    schema = yaml.safe_load(file_obj)

fields = []
for key in schema.get('mapping').keys():
    if schema.get('mapping').get(key).get('required'):
        fields.append(key)

print(fields)
