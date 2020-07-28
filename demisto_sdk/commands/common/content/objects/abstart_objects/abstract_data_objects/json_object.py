from abc import ABC
from typing import Union

from wcmatch.pathlib import Path
import ujson

from demisto_sdk.commands.common.content.objects.abstart_objects.abstract_data_objects.dictionary_based_object import DictionaryBasedObject


class JSONObject(DictionaryBasedObject, ABC):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path=self._fix_path(path), file_name_prefix=file_name_prefix)

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        path = Path(path)
        if path.is_dir():
            try:
                path = next(path.glob([f"*.json"]))
            except Exception as e:
                raise BaseException(f"Unable to find json file in path {path}, Full error: {e}")
        elif not (path.is_file() or path.suffix in ["json"]):
            raise BaseException(f"Unable to find json file in path {path}")

        return path

    def _unserialize(self) -> None:
        try:
            self._as_dict = ujson.load(self._path.open())
        except Exception as e:
            raise BaseException(f"{self._path} is not valid json file, Full error: {e}")

    def _serialize(self, dest: Path) -> None:
        try:
            ujson.dump(self._as_dict,
                       dest.open(mode="w"),
                       indent=4,
                       encode_html_chars=True,
                       escape_forward_slashes=False,
                       ensure_ascii=False)
        except Exception as e:
            raise BaseException(f"{self._path} unable to dump json object to {dest_dir}: {e}")

        return dest
