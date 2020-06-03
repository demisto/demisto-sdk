from ruamel import yaml
from TestSuite.file import File


class YAML(File):

    def write(self, yml: dict):
        super().write(yaml.dump(yml))

    def update(self, update_obj: dict):
        yml_contents = yaml.load(self.read())
        yml_contents.update(update_obj)
        self.write(yml_contents)

    def update_description(self, description: str):
        self.update({'description': description})
