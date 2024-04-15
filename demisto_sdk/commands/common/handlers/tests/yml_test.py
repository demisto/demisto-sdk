from io import StringIO

from ruamel.yaml import YAML  # noqa: TID251

from demisto_sdk.commands.common.handlers.yaml.ruamel_handler import RUAMEL_Handler


class TestYAMLHandler:
    def test_yaml_handler_without_indent(self, mocker):
        """
        Given:
            - A RUAMEL_Handler object without indent
        When:
            - Running dump method
        Then:
            - Ensure indent is not called
        """
        mocker.patch.object(YAML, "dump")
        mocker.patch.object(YAML, "indent")
        yaml = RUAMEL_Handler()
        yaml.dump({}, StringIO())
        assert yaml.yaml.indent.call_count == 0

    def test_yaml_handler_with_indent(self, mocker):
        """
        Given:
            - A RUAMEL_Handler object with indent
        When:
            - Running dump method
        Then:
            - Ensure indent is called
            - Ensure indent is called with the correct value
        """
        mocker.patch.object(YAML, "dump")
        mocker.patch.object(YAML, "indent")
        yaml_dump = RUAMEL_Handler(indent=4)
        yaml_dump.dump({}, StringIO())

        assert yaml_dump.yaml.indent.call_count == 1
        yaml_dump.yaml.indent.assert_called_with(sequence=4)
