import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Union

from demisto_sdk.commands.common.constants import (PACKS_PACK_META_FILE_NAME,
                                                   XSOAR_AUTHOR, XSOAR_SUPPORT,
                                                   XSOAR_SUPPORT_URL,
                                                   ContentItems)
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    JSONObject
from demisto_sdk.commands.common.tools import get_core_pack_list
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from packaging.version import Version, parse
from wcmatch.pathlib import Path

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
PARTNER_SUPPORT = 'partner'
XSOAR_CERTIFIED = 'certified'
XSOAR_EULA_URL = 'https://github.com/demisto/content/blob/master/LICENSE'

CORE_PACKS_LIST = get_core_pack_list()


class PackMetaData(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._name: str = ''
        self._id: str = ''
        self._description: str = ''
        self._created: datetime = datetime.utcnow()
        self._updated: datetime = datetime.utcnow()
        self._legacy: bool = True
        self._support: str = ''
        self._eulaLink: str = 'https://github.com/demisto/content/blob/master/LICENSE'
        self._email: str = ''
        self._url: str = ''
        self._author: str = ''
        self._certification: str = ''
        self._price: int = 0
        self._premium: bool = False
        self._vendorId: str = ''
        self._vendorName: str = ''
        self._hidden: bool = False
        self._previewOnly: bool = False
        self._serverMinVersion: Version = parse('0.0.0')
        self._currentVersion: Version = parse('0.0.0')
        self._versionInfo: int = 0
        self._tags: List[str] = []
        self._categories: List[str] = []
        self._contentItems: Dict[ContentItems, List] = {}
        self._useCases: List[str] = []
        self._keywords: List[str] = []
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
        if not new_pack_created_date:
            return

        if isinstance(new_pack_created_date, str):
            try:
                self._created = datetime.strptime(new_pack_created_date, DATETIME_FORMAT)
            except ValueError:
                return
        else:
            self._created = new_pack_created_date

    @property
    def updated(self) -> datetime:
        """Object updated attribute.

        Returns:
            datetime: pack updated date.
        """
        return self._updated

    @updated.setter
    def updated(self, new_pack_updated_date: Union[str, datetime]):
        """Setter for the updated attribute"""
        if isinstance(new_pack_updated_date, str):
            try:
                self._updated = datetime.strptime(new_pack_updated_date, DATETIME_FORMAT)
            except ValueError:
                return
        else:
            self._updated = new_pack_updated_date

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
        support_details = {}

        if self.url:  # set support url from user input
            support_details['url'] = self.url
        elif self.support == XSOAR_SUPPORT:  # in case support type is xsoar, set default xsoar support url
            support_details['url'] = XSOAR_SUPPORT_URL
        # add support email if defined
        if self.email:
            support_details['email'] = self.email

        return support_details

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
    def email(self) -> str:
        """Object email attribute.

        Returns:
            str: pack author email.
        """
        return self._email

    @email.setter
    def email(self, new_pack_email: str):
        """Setter for the email attribute"""
        self._email = new_pack_email

    @property
    def url(self) -> str:
        """Object url attribute.

        Returns:
            str: pack url.
        """
        return self._url

    @url.setter
    def url(self, new_pack_url: str):
        """Setter for the url attribute"""
        self._url = new_pack_url

    @property
    def author(self) -> str:
        """Object author attribute.

        Returns:
            str: pack author.
        """
        if self.support == XSOAR_SUPPORT:
            if not self._author:
                return XSOAR_AUTHOR
            elif self._author != XSOAR_AUTHOR:
                logging.warning(f'{self._author} author doest not match {XSOAR_AUTHOR} default value')
                return self._author
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
        if self.support in [XSOAR_SUPPORT, PARTNER_SUPPORT]:
            return XSOAR_CERTIFIED
        else:
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
    def price(self, new_pack_price: Union[int, str]):
        """Setter for the price attribute"""
        try:
            self._price = int(new_pack_price)
        except ValueError:
            self._price = 0

    @property
    def premium(self) -> bool:
        """Object premium attribute.

        Returns:
            bool: pack premium.
        """
        return self._premium

    @premium.setter
    def premium(self, is_premium: bool):
        """Setter for the premium attribute"""
        self._premium = is_premium

    @property
    def vendor_id(self) -> str:
        """Object vendorId attribute.

        Returns:
            str: pack vendor_id.
        """
        return self._vendorId

    @vendor_id.setter
    def vendor_id(self, new_pack_vendor_id: str):
        """Setter for the vendorId attribute"""
        self._vendorId = new_pack_vendor_id

    @property
    def vendor_name(self) -> str:
        """Object vendorName attribute.

        Returns:
            str: pack vendor_name.
        """
        return self._vendorName

    @vendor_name.setter
    def vendor_name(self, new_pack_vendor_name: str):
        """Setter for the vendorName attribute"""
        self._vendorName = new_pack_vendor_name

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
    def preview_only(self) -> bool:
        """Object previewOnly attribute.
        Returns:
            bool: pack preview_only.
        """
        return self._previewOnly

    @preview_only.setter
    def preview_only(self, is_preview_only: bool):
        """Setter for the previewOnly attribute"""
        self._previewOnly = is_preview_only

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
    def tags(self) -> List[str]:
        """Object tags attribute.

        Returns:
            List[str]: pack tags.
        """
        return self._tags

    @tags.setter
    def tags(self, new_pack_tags: List[str]):
        """Setter for the tags attribute"""
        self._tags = new_pack_tags

    @property
    def categories(self) -> List[str]:
        """Object categories attribute.

        Returns:
            List[str]: pack categories.
        """
        return self._categories

    @categories.setter
    def categories(self, new_pack_categories: List[str]):
        """Setter for the categories attribute"""
        self._categories = [category.title() for category in new_pack_categories]

    @property
    def content_items(self) -> Dict[str, List]:
        """Object contentItems attribute.

        Returns:
            Dict[str, List]: pack content_items.
        """
        return {content_entity.value: content_items for content_entity, content_items in self._contentItems.items()}

    @content_items.setter
    def content_items(self, new_pack_content_items: Dict[ContentItems, List]):
        """Setter for the contentItems attribute"""
        self._contentItems = new_pack_content_items

    @property
    def use_cases(self) -> List[str]:
        """Object useCases attribute.

        Returns:
            List[str]: pack use_cases.
        """
        return [use_case.title() for use_case in self._useCases]

    @use_cases.setter
    def use_cases(self, new_pack_use_cases: List[str]):
        """Setter for the useCases attribute"""
        self._useCases = new_pack_use_cases

    @property
    def keywords(self) -> List[str]:
        """Object keywords attribute.

        Returns:
            List[str]: pack keywords.
        """
        return self._keywords

    @keywords.setter
    def keywords(self, new_pack_keywords: List[str]):
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

    def dump_metadata_file(self, dest_dir: Union[Path, str] = '') -> List[Path]:
        file_content = {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'created': self.created.strftime(DATETIME_FORMAT),
            'updated': self.updated.strftime(DATETIME_FORMAT),
            'legacy': self.legacy,
            'support': self.support,
            'supportDetails': self.support_details,
            'eulaLink': self.eula_link,
            'author': self.author,
            'certification': self.certification,
            'price': self.price,
            'serverMinVersion': str(self.server_min_version),
            'currentVersion': str(self.current_version),
            'tags': self.tags,
            'categories': self.categories,
            'contentItems': self.content_items,
            'useCases': self.use_cases,
            'keywords': self.keywords,
            'dependencies': self.dependencies
        }

        if self.price > 0:
            file_content['premium'] = self.premium
            file_content['vendorId'] = self.vendor_id
            file_content['vendorName'] = self.vendor_name
            if self.preview_only:
                file_content['previewOnly'] = True

        new_metadata_path = os.path.join(dest_dir, 'metadata.json')
        with open(new_metadata_path, 'w') as metadata_file:
            json.dump(file_content, metadata_file, indent=4)

        return [Path(new_metadata_path)]

    def load_user_metadata(self, pack_id: str, pack_name: str, pack_path: Path, logger: logging.Logger) -> None:
        """Loads user defined metadata and stores part of it's data in defined properties fields.

        Args:
            pack_id (str): The pack's id.
            pack_name (str): The pack's name.
            pack_path (Path): The pack's path.
            logger (logging.Logger): System logger already initialized.

        """
        user_metadata_path = os.path.join(pack_path, PACKS_PACK_META_FILE_NAME)  # user metadata path before parsing

        if not os.path.exists(user_metadata_path):
            logger.error(f'{pack_name} pack is missing {PACKS_PACK_META_FILE_NAME} file.')
            return None

        try:
            with open(user_metadata_path, "r") as user_metadata_file:
                user_metadata = json.load(user_metadata_file)  # loading user metadata
                # part of old packs are initialized with empty list
                if isinstance(user_metadata, list):
                    user_metadata = {}

            self.id = pack_id
            self.name = user_metadata.get('name', '')
            self.description = user_metadata.get('description', '')
            self.created = user_metadata.get('created')
            try:
                self.price = int(user_metadata.get('price', 0))
            except Exception:
                logger.error(f'{self.name} pack price is not valid. The price was set to 0.')
            self.support = user_metadata.get('support', '')
            self.url = user_metadata.get('url', '')
            self.email = user_metadata.get('email', '')
            self.certification = user_metadata.get('certification', '')
            self.current_version = parse(user_metadata.get('currentVersion', '0.0.0'))
            self.author = user_metadata.get('author', '')
            self.hidden = user_metadata.get('hidden', False)
            self.tags = user_metadata.get('tags', [])
            self.keywords = user_metadata.get('keywords', [])
            self.categories = user_metadata.get('categories', [])
            self.use_cases = user_metadata.get('useCases', [])
            self.dependencies = user_metadata.get('dependencies', {})

            if self.price > 0:
                self.premium = True
                self.vendor_id = user_metadata.get('vendorId', '')
                self.vendor_name = user_metadata.get('vendorName', '')
                self.preview_only = user_metadata.get('previewOnly', False)
            if self.use_cases and 'Use Case' not in self.tags:
                self.tags.append('Use Case')

        except Exception:
            logger.error(f'Failed loading {pack_name} user metadata.')

    def handle_dependencies(self, pack_name: str, id_set_path: str, logger: logging.Logger) -> None:
        """Updates pack's dependencies using the find_dependencies command.

        Args:
            pack_name (str): The pack's name.
            id_set_path (str): the id_set file path.
            logger (logging.Logger): System logger already initialized.
        """
        calculated_dependencies = PackDependencies.find_dependencies(pack_name,
                                                                     id_set_path=id_set_path,
                                                                     update_pack_metadata=False,
                                                                     silent_mode=True,
                                                                     complete_data=True)

        # If it is a core pack, check that no new mandatory packs (that are not core packs) were added
        # They can be overridden in the user metadata to be not mandatory so we need to check there as well
        if pack_name in CORE_PACKS_LIST:
            mandatory_dependencies = [k for k, v in calculated_dependencies.items()
                                      if v.get('mandatory', False) is True and
                                      k not in CORE_PACKS_LIST and
                                      k not in self.dependencies.keys()]
            if mandatory_dependencies:
                logger.error(f'New mandatory dependencies {mandatory_dependencies} were '
                             f'found in the core pack {pack_name}')

        self.dependencies.update(calculated_dependencies)
