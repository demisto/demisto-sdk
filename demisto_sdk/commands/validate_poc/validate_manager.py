from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate_poc.validators.base_validator import BaseValidator
import toml
# print (toml.load("data.toml"))

class ValidateManager:
    config: dict
    def should_run(self):
        if self.config["all"]:
            return True
    def run(self):
        # gather all files to run on
        files_to_run = ["/Users/ierukhimovic/dev/demisto/content/Packs/QRadar/Integrations/QRadar_v3/QRadar_v3.py"]
        content_items_to_run = [BaseContent.from_path(file_to_run) for file_to_run in files_to_run]
        results = []
        # gather validator from validate_poc package
        validators = BaseValidator.__subclasses__()
        for validator in validators:
            if validator.error_code not in self.config["select"]:
                continue
            for content_item in content_items_to_run:
                pack = content_item if isinstance(content_item, Pack) else content_item.in_pack
                # if content item name is in pack ignore list, skip
                if validator.should_run(content_item):
                    results.append(validator.is_valid(content_item))