from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.abstract_data_objects.general_object import \
    GeneralObject


class TextObject(GeneralObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._text = ""

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self._changed = True

    def _unserialize(self):
        if not self._text:
            try:
                self._text = self.path.read_text()
            except Exception as e:
                raise BaseException(f"Unable to unserialize text from {self.path}, Full error: {e}")

    def _serialize(self, dest: Path):
        try:
            dest.write_text(self._text)
        except Exception as e:
            raise BaseException(f"Unable to serialize text object {self.path}, Full error: {e}")

        return dest
