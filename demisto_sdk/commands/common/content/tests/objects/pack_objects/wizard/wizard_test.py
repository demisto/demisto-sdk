from demisto_sdk.commands.common.content.objects.pack_objects.wizard.wizard import (
    Wizard,
)
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object

sample_wizard_name = "sample-wizard"
sample_file_path = f"Wizards/{sample_wizard_name}.json"


class TestWizard:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir[sample_file_path])
        assert isinstance(obj, Wizard)

    def test_prefix(self, datadir):
        """
        Test that wizards created from files whose name does not start with `wizard-` are normalized correctly.
        """
        obj = Wizard(datadir[sample_file_path])
        assert obj.normalize_file_name() == f"wizard-{sample_wizard_name}.json"
