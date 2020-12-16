from datetime import datetime
from typing import Dict, List, Optional, Union

from demisto_sdk.commands.common.content.objects.abstract_objects import \
    JSONObject
from packaging.version import Version, parse
from wcmatch.pathlib import Path

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%sZ'


class PackMetaData(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._name: str = ''
        self._id: str = ''
        self._description: str = ''
        self._created: datetime = datetime.now()
        self._updated: datetime = datetime.now()
        self._legacy: bool = False
        self._support: str = ''
        self._supportDetails: Dict = {}
        self._eulaLink: str = ''
        self._author: str = ''
        self._certification: str = ''
        self._price: int = 0
        self._hidden: bool = False
        self._serverMinVersion: Version = parse('0.0.0')
        self._currentVersion: Version = parse('0.0.0')
        self._versionInfo: int = 0
        self._tags: List = []
        self._categories: List = []
        self._contentItems: Dict[str, List] = {}
        self._useCases: List = []
        self._keywords: List = []
        self._dependencies: Dict[str, Dict] = {}

    @property
    def name(self) -> str:
        """Object name attribute.

        Returns:
            str: pack name.
        """
        return self._name

    @name.setter
    def name(self, new_pack_name: str):
        """Setter for the name attribute"""
        self._name = new_pack_name

    @property
    def id(self) -> str:
        """Object id attribute.

        Returns:
            str: pack id.
        """
        return self._id

    @id.setter
    def id(self, new_pack_id: str):
        """Setter for the id attribute"""
        self._id = new_pack_id

    @property
    def description(self) -> str:
        """Object description attribute.

        Returns:
            str: pack description.
        """
        return self._description

    @description.setter
    def description(self, new_pack_description: str):
        """Setter for the description attribute"""
        self._description = new_pack_description

    @property
    def created(self) -> datetime:
        """Object created attribute.

        Returns:
            datetime: pack created date.
        """
        return self._created

    @created.setter
    def created(self, new_pack_created_date: Union[str, datetime]):
        """Setter for the created attribute"""
        if isinstance(new_pack_created_date, str):
            try:
                self._created = datetime.strptime(new_pack_created_date, DATETIME_FORMAT)
            except ValueError:
                return
        else:
            self._created = new_pack_created_date

    @property
    def legacy(self) -> bool:
        """Object legacy attribute.

        Returns:
            bool: is legacy.
        """
        return self._legacy

    @legacy.setter
    def legacy(self, is_legacy: bool):
        """Setter for the legacy attribute"""
        self._legacy = is_legacy

    @property
    def support(self) -> str:
        """Object support attribute.

        Returns:
            str: pack supporter.
        """
        return self._support

    @support.setter
    def support(self, new_pack_support: str):
        """Setter for the support attribute"""
        self._support = new_pack_support

    @property
    def support_details(self) -> dict:
        """Object supportDetails attribute.

        Returns:
            dict: pack support details.
        """
        return self._supportDetails

    @support_details.setter
    def support_details(self, new_pack_support_details: dict):
        """Setter for the supportDetails attribute"""
        self._supportDetails = new_pack_support_details

    @property
    def eula_link(self) -> str:
        """Object eulaLink attribute.

        Returns:
            str: pack eula link.
        """
        return self._eulaLink

    @eula_link.setter
    def eula_link(self, new_pack_eula_link: str):
        """Setter for the eulaLink attribute"""
        self._eulaLink = new_pack_eula_link

    @property
    def author(self) -> str:
        """Object author attribute.

        Returns:
            str: pack author.
        """
        return self._author

    @author.setter
    def author(self, new_pack_author: str):
        """Setter for the author attribute"""
        self._author = new_pack_author

    @property
    def certification(self) -> str:
        """Object certification attribute.

        Returns:
            str: pack certification.
        """
        return self._certification

    @certification.setter
    def certification(self, new_pack_certification: str):
        """Setter for the certification attribute"""
        self._certification = new_pack_certification

    @property
    def price(self) -> int:
        """Object price attribute.

        Returns:
            int: pack price.
        """
        return self._price

    @price.setter
    def price(self, new_pack_price: int):
        """Setter for the price attribute"""
        self._price = new_pack_price

    @property
    def hidden(self) -> bool:
        """Object hidden attribute.
        Returns:
            bool: pack hidden.
        """
        return self._hidden

    @hidden.setter
    def hidden(self, is_hidden: bool):
        """Setter for the hidden attribute"""
        self._hidden = is_hidden

    @property
    def server_min_version(self) -> Version:
        """Object serverMinVersion attribute.

        Returns:
            str: pack server_min_version.
        """
        return self._serverMinVersion

    @server_min_version.setter
    def server_min_version(self, new_pack_server_min_version: Version):
        """Setter for the serverMinVersion attribute"""
        self._serverMinVersion = new_pack_server_min_version

    @property
    def current_version(self) -> Version:
        """Object currentVersion attribute.

        Returns:
            str: pack current_version.
        """
        return self._currentVersion

    @current_version.setter
    def current_version(self, new_pack_current_version: Version):
        """Setter for the currentVersion attribute"""
        self._currentVersion = new_pack_current_version

    @property
    def version_info(self) -> int:
        """Object versionInfo attribute.

        Returns:
            int: pack version_info.
        """
        return self._versionInfo

    @version_info.setter
    def version_info(self, new_pack_version_info: int):
        """Setter for the versionInfo attribute"""
        self._versionInfo = new_pack_version_info

    @property
    def tags(self) -> List:
        """Object tags attribute.

        Returns:
            List: pack tags.
        """
        return self._tags

    @tags.setter
    def tags(self, new_pack_tags: List):
        """Setter for the tags attribute"""
        self._tags = new_pack_tags

    @property
    def categories(self) -> List:
        """Object categories attribute.

        Returns:
            List: pack categories.
        """
        return self._categories

    @categories.setter
    def categories(self, new_pack_categories: List):
        """Setter for the categories attribute"""
        self._categories = new_pack_categories

    @property
    def content_items(self) -> Dict[str, List]:
        """Object contentItems attribute.

        Returns:
            Dict[str, List]: pack content_items.
        """
        return self._contentItems

    @content_items.setter
    def content_items(self, new_pack_content_items: Dict[str, List]):
        """Setter for the contentItems attribute"""
        self._contentItems = new_pack_content_items

    @property
    def use_cases(self) -> List:
        """Object useCases attribute.

        Returns:
            List: pack use_cases.
        """
        return self._useCases

    @use_cases.setter
    def use_cases(self, new_pack_use_cases: List):
        """Setter for the useCases attribute"""
        self._useCases = new_pack_use_cases

    @property
    def keywords(self) -> List:
        """Object keywords attribute.

        Returns:
            List: pack keywords.
        """
        return self._keywords

    @keywords.setter
    def keywords(self, new_pack_keywords: List):
        """Setter for the keywords attribute"""
        self._keywords = new_pack_keywords

    @property
    def dependencies(self) -> Dict[str, Dict]:
        """Object dependencies attribute.

        Returns:
            Dict[str, Dict]: pack dependencies.
        """
        return self._dependencies

    @dependencies.setter
    def dependencies(self, new_pack_dependencies: Dict[str, Dict]):
        """Setter for the dependencies attribute"""
        self._dependencies = new_pack_dependencies

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        pass
