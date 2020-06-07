from ruamel import yaml
from TestSuite.file import File


class YAML(File):
    def write(self, tymlk):
        pass

    def write_dict(self, yml: dict):
        super().write(str(yaml.dump(yml)))

    def update(self, update_obj: dict):
        yml_contents = yaml.load(self.read())
        yml_contents.update(update_obj)
        self.write_dict(yml_contents)

    def update_description(self, description: str):
        self.update({'description': description})
