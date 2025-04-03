import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from packaging.version import Version, parse
from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import (
    LANDING_PAGE_SECTIONS_PATH,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_json, is_external_repository
from demisto_sdk.commands.content_graph.common import ContentType, PackTags
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import PackContentItems
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)

MINIMAL_UPLOAD_SUPPORTED_VERSION = Version("6.5.0")
MINIMAL_ALLOWED_SKIP_VALIDATION_VERSION = Version("6.6.0")

json = JSON_Handler()


class PackMetadata(BaseModel):
    name: str
    display_name: str
    description: Optional[str]
    created: Optional[str]
    updated: Optional[str] = Field("")
    legacy: Optional[bool]
    support: str = Field("")
    url: Optional[str]
    email: Optional[str]
    eulaLink: Optional[str]
    author: str = Field("")
    author_image: str = Field("", alias="authorImage")
    certification: str = Field("")
    price: Optional[int]
    hidden: Optional[bool]
    server_min_version: Optional[str] = Field(alias="serverMinVersion")
    current_version: Optional[str] = Field(alias="currentVersion")
    version_info: str = Field("", alias="versionInfo")
    commit: Optional[str]
    downloads: Optional[int]
    tags: List[str] = Field([])
    categories: List[str] = Field([])
    use_cases: List[str] = Field([], alias="useCases")
    keywords: Optional[List[str]]
    search_rank: Optional[int] = Field(alias="searchRank")
    excluded_dependencies: List[str] = Field([], alias="excludedDependencies")
    videos: List[str] = Field([])
    modules: List[str] = Field([])
    integrations: List[str] = Field([])
    hybrid: bool = Field(False, alias="hybrid")
    default_data_source_id: Optional[str] = Field("", alias="defaultDataSource")
    default_data_source_name: Optional[str] = Field("", exclude=True)

    # For private packs
    premium: Optional[bool]
    vendor_id: Optional[str] = Field(None, alias="vendorId")
    partner_id: Optional[str] = Field(None, alias="partnerId")
    partner_name: Optional[str] = Field(None, alias="partnerName")
    preview_only: Optional[bool] = Field(None, alias="previewOnly")
    disable_monthly: Optional[bool] = Field(None, alias="disableMonthly")
    content_commit_hash: Optional[str] = Field(None, alias="contentCommitHash")

    def _enhance_pack_properties(
        self,
        marketplace: MarketplaceVersions,
        pack_id: str,
        content_items: PackContentItems,
    ):
        """
        Enhancing the Pack object properties before dumping into a dictionary.
        - Adding tags considering the pack content items and marketplace.
        - Replacing the `author` property from XSOAR to XSIAM if the prepare is to marketplacev2.
        - Getting into the `version_info` property the pipeline_id variable.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
            pack_id (str): The pack ID.
            content_items (PackContentItems): The pack content items object.
        """
        if not self.hybrid:
            self._set_default_data_source(content_items)
        self.tags = self._get_pack_tags(marketplace, pack_id, content_items)
        self.author = self._get_author(self.author, marketplace)
        # We want to add the pipeline_id only if this is called within our repo.
        self.version_info = (
            "" if is_external_repository() else os.environ.get("CI_PIPELINE_ID", "")
        )

    def _format_metadata(
        self,
        marketplace: MarketplaceVersions,
        content_items: PackContentItems,
        dependencies: List[RelationshipData],
    ) -> dict:
        """
        Enhancing the pack metadata properties after dumping into a dictionary. (properties that can't be calculating before)
        - Adding the pack's content items and calculating their from/to version before.
        - Adding the content items display names.
        - Gathering the pack dependencies and adding the metadata.
        - Unifying the `url` and `email` into the `support_details` property.
        - Adding the default data source if exists.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
            content_items (PackContentItems): The pack content items object.
            dependencies (list[RelationshipData]): List of the pack dependencies.

        Returns:
            dict: The update metadata dictionary.
        """
        _metadata: dict = {}

        (
            collected_content_items,
            content_displays,
        ) = self._get_content_items_and_displays_metadata(marketplace, content_items)

        default_data_source_value = (
            {
                "name": self.default_data_source_name,
                "id": self.default_data_source_id,
            }
            if self.default_data_source_name
            and self.default_data_source_id
            and marketplace
            in [MarketplaceVersions.MarketplaceV2, MarketplaceVersions.PLATFORM]
            and not self.hybrid
            else None  # if the pack is multiple marketplace, override the initially set str default_data_source_id
        )

        _metadata.update(
            {
                "contentItems": collected_content_items,
                "contentDisplays": content_displays,
                "dependencies": self._enhance_dependencies(marketplace, dependencies),
                "supportDetails": self._get_support_details(),
                "defaultDataSource": default_data_source_value,
            }
        )

        return _metadata

    @staticmethod
    def _place_data_source_integration_first(
        integration_list: List[Dict],
        data_source_id: str,
    ):
        integration_metadata_object = [
            integration
            for integration in integration_list
            if integration.get("id") == data_source_id
        ]

        if not integration_metadata_object:
            logger.error(
                f"Integration metadata object was not found for {data_source_id=} in {integration_list=}."
            )
        logger.info(f"Placing {data_source_id=} first in the integration_list.")
        integration_list.remove(integration_metadata_object[0])
        integration_list.insert(0, integration_metadata_object[0])

    def _get_content_items_and_displays_metadata(
        self, marketplace: MarketplaceVersions, content_items: PackContentItems
    ) -> Tuple[Dict, Dict]:
        """
        Gets the pack content items and display names to add into the pack's metadata dictionary.
        For each content item the function generates its `summary` and calculating the from/to version
        on whether to add this item to the content items list.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
            content_items (PackContentItems): The pack content items object.

        Returns:
            Tuple[Dict, Dict]: The content items and display names dictionaries to add to the pack metadata.
        """
        collected_content_items: dict = {}
        content_displays: dict = {}
        for content_item in content_items:
            if should_ignore_item_in_metadata(content_item, marketplace):
                continue
            self._add_item_to_metadata_list(
                collected_content_items=collected_content_items,
                content_item=content_item,
                marketplace=marketplace,
            )

            content_displays[content_item.content_type.metadata_name] = (
                content_item.content_type.metadata_display_name
            )

        content_displays = {
            content_type: (
                content_type_display
                if (
                    collected_content_items[content_type]
                    and len(collected_content_items[content_type]) == 1
                )
                else f"{content_type_display}s"
            )
            for content_type, content_type_display in content_displays.items()
        }
        if (
            self.default_data_source_id
            and self.default_data_source_name
            and collected_content_items
            and marketplace == MarketplaceVersions.MarketplaceV2
            and not self.hybrid
        ):
            # order collected_content_items integration list so that the defaultDataSource will be first
            self._place_data_source_integration_first(
                collected_content_items[ContentType.INTEGRATION.metadata_name],
                self.default_data_source_id,
            )
        return collected_content_items, content_displays

    def _enhance_dependencies(
        self, marketplace: MarketplaceVersions, dependencies: List[RelationshipData]
    ):
        """
        Gathers the first level pack's dependencies details to a list to add to the pack's metadata.
        For each dependency it adds the following pack's properties:
        `mandatory`, `minVersion`, `author`, `name`, `certification`

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.

        Returns:
            dict: The dependencies of the pack.
        """
        return {
            r.content_item_to.object_id: {
                "mandatory": r.mandatorily,
                # Get the minVersion either from the pack_metadata if exists, or from graph calculation
                "minVersion": r.target_min_version or r.content_item_to.current_version,  # type:ignore[attr-defined]
                "author": self._get_author(
                    r.content_item_to.author,  # type:ignore[attr-defined]
                    marketplace,
                ),
                "name": r.content_item_to.name,  # type:ignore[attr-defined]
                "certification": r.content_item_to.certification  # type:ignore[attr-defined]
                or "",
            }
            for r in dependencies
            if r.is_direct
            and r.content_item_to.object_id not in self.excluded_dependencies
            and not r.content_item_to.hidden  # type: ignore
        }

    def _get_pack_tags(
        self,
        marketplace: MarketplaceVersions,
        pack_id: str,
        content_items: PackContentItems,
    ) -> list:
        """
        Gets the pack's tags considering the pack content item's properties.
        For example, if the pack has a script which is a transformer or a filter,
        then the pack will have the tags "Transformer" or "Filter" accordingly.

        Args:
            marketplace (MarketplaceVersions): The marketplace to which the pack should belong to.
            pack_id (str): The pack ID.
            content_items (PackContentItems): The pack content items object.

        Returns:
            list: The list of tags to add to the pack's metadata.
        """
        tags = self._get_tags_by_marketplace(marketplace)
        tags |= self._get_tags_from_landing_page(pack_id)
        tags |= (
            {PackTags.TIM}
            if any([integration.is_feed for integration in content_items.integration])
            or any(
                [
                    playbook.name.startswith("TIM ")
                    for playbook in content_items.playbook
                    if not playbook.is_test
                ]
            )
            else set()
        )
        tags |= {PackTags.USE_CASE} if self.use_cases else set()
        tags |= (
            {PackTags.TRANSFORMER}
            if any(
                [
                    "transformer" in script.tags
                    for script in content_items.script
                    if not script.is_test
                ]
            )
            else set()
        )
        tags |= (
            {PackTags.FILTER}
            if any(
                [
                    "filter" in script.tags
                    for script in content_items.script
                    if not script.is_test
                ]
            )
            else set()
        )
        tags |= (
            {PackTags.COLLECTION}
            if any(
                [
                    integration.is_fetch_events
                    for integration in content_items.integration
                ]
            )
            or any(
                [
                    content_items.parsing_rule,
                    content_items.modeling_rule,
                    content_items.correlation_rule,
                    content_items.xdrc_template,
                ]
            )
            else set()
        )
        tags |= (
            {PackTags.DATA_SOURCE}
            if self.is_data_source(content_items)
            and marketplace == MarketplaceVersions.MarketplaceV2
            else set()
        )

        if self.created:
            days_since_creation = (
                datetime.utcnow()
                - datetime.strptime(self.created, "%Y-%m-%dT%H:%M:%SZ")
            ).days
            if days_since_creation <= 30:
                tags |= {PackTags.NEW}
            else:
                tags -= {PackTags.NEW}

        return list(tags)

    def _get_tags_by_marketplace(self, marketplace: str):
        """Returns tags in according to the current marketplace"""
        tags: set = set()

        if not self.tags:
            return tags

        for tag in self.tags:
            if ":" in tag:
                tag_data = tag.split(":")
                if marketplace in tag_data[0].split(","):
                    tags.update({tag_data[1]})
            else:
                tags.update({tag})

        return tags

    def is_data_source(self, content_items: PackContentItems) -> bool:
        """Returns a boolean result on whether the pack should be considered as a "Data Source" pack."""
        if self.hybrid:
            # hybrid packs have a builtin data source
            return False
        if self.default_data_source_id and self.default_data_source_name:
            return True
        return any(self.get_valid_data_source_integrations(content_items))

    def _set_default_data_source(self, content_items: PackContentItems) -> None:
        """If there is more than one data source in the pack, return the default data source."""
        data_sources: List[Dict[str, str]] = self.get_valid_data_source_integrations(  # type: ignore[assignment]
            content_items, self.support, include_name=True
        )

        if self.default_data_source_id and self.default_data_source_id in [
            data_source.get("id") for data_source in data_sources
        ]:
            # the provided default_data_source_id is of a valid integration, keep it
            self.default_data_source_name = [
                data_source.get("name")
                for data_source in data_sources
                if data_source.get("id") == self.default_data_source_id
            ][0]
            logger.info(
                f"Keeping the provided {self.default_data_source_id=} with {self.default_data_source_name=}"
            )
            return

        if not data_sources:
            return

        logger.info(
            f"No defaultDataSource provided ({self.default_data_source_id}) or it is not a valid data source,"
            f" choosing default from {data_sources=}"
        )
        if len(data_sources) > 1:
            # should not happen because of validation PA131
            logger.info(
                f"{self.name} has multiple data sources. Setting a default value."
            )

        # setting a value to the defaultDataSource in case there is a data source
        self.default_data_source_name = (
            data_sources[0].get("name") if data_sources else None
        )
        self.default_data_source_id = (
            data_sources[0].get("id") if data_sources else None
        )

    @staticmethod
    def get_valid_data_source_integrations(
        content_items: PackContentItems,
        support_level: str = None,
        include_name: bool = False,
    ) -> List[Union[Dict[str, str], str]]:
        """
        Find fetching integrations in XSIAM, not deprecated.
        When a support level is provided, the returned display names are without the contribution suffix.
        """
        return [
            (
                {
                    "name": IntegrationScriptUnifier.remove_support_from_display_name(
                        integration.display_name, support_level
                    ),
                    "id": integration.object_id,  # same as integration.name
                }
                if include_name
                else integration.object_id
            )
            for integration in content_items.integration
            if integration.is_data_source()
        ]

    def _get_tags_from_landing_page(self, pack_id: str) -> set:
        """
        Build the pack's tag list according to the landingPage sections file.

        Args:
            pack_id (str): The pack ID.

        Returns:
            set: Pack's tags.
        """
        tags: set = set()

        try:
            landing_page_sections = get_json(LANDING_PAGE_SECTIONS_PATH)
        except FileNotFoundError as e:
            logger.warning(
                f"Couldn't find the landing_page file in path {LANDING_PAGE_SECTIONS_PATH}. Skipping collecting tags by landing page sections.\n{e}"
            )
            return tags

        sections = landing_page_sections.get("sections") or []

        for section in sections:
            if pack_id in landing_page_sections.get(section, []):
                tags.add(section)

        return tags

    def _get_support_details(self) -> dict:
        """Gets the support details object for the metadata.

        Returns:
            dict: The support details object.
        """
        support_details = {}
        if self.url:
            support_details["url"] = self.url
        if self.email:
            support_details["email"] = self.email
        return support_details

    @staticmethod
    def _get_author(author, marketplace):
        if marketplace in [
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.XPANSE,
            MarketplaceVersions.XSOAR_ON_PREM,
            MarketplaceVersions.XSOAR_SAAS,
        ]:
            return author
        elif marketplace == MarketplaceVersions.MarketplaceV2:
            return author.replace("Cortex XSOAR", "Cortex XSIAM")
        elif marketplace == MarketplaceVersions.PLATFORM:
            return author.replace("Cortex XSOAR", "Cortex")
        raise ValueError(f"Unknown marketplace version for author: {marketplace}")

    def _add_item_to_metadata_list(
        self,
        collected_content_items: dict,
        content_item: ContentItem,
        marketplace: MarketplaceVersions,
        incident_to_alert: bool = False,
    ):
        """
        Adds the given content item to the metadata content items list.
        - Checks if the given content item was already added to the metadata content items list
        and replaces the object if its `toversion` is higher than the existing metadata object's `toversion`.
        - If the content item name should be replaced from incident to alert, then the function will be called recursively
        to replace also the item that its name was replaced from incident to alert.

        Args:
            collected_content_items (dict): The content items metadata list that were already collected.
            content_item (ContentItem): The current content item to check.
            marketplace (MarketplaceVersions): The marketplace to prepare the pack to upload.
            incident_to_alert (bool, optional): Whether should replace incident to alert. Defaults to False.
        """
        collected_content_items.setdefault(content_item.content_type.metadata_name, [])
        content_item_summary = content_item.summary(
            marketplace, incident_to_alert=incident_to_alert
        )

        if content_item_metadata := self._search_content_item_metadata_object(
            collected_content_items=collected_content_items,
            item_id=content_item_summary["id"],
            item_name=content_item_summary["name"],
            item_type_key=content_item.content_type.metadata_name,
        ):
            logger.debug(
                f'Found content item with name "{content_item.name}" that was already appended to the list'
            )

            self._replace_item_if_has_higher_toversion(
                content_item,
                content_item_metadata,
                content_item_summary,
                marketplace,
                incident_to_alert,
            )

        else:
            logger.debug(
                f'Didn\'t find content item with name "{content_item.name}" in the list, appending.'
            )
            self._set_empty_toversion_if_default(content_item_summary)
            collected_content_items[content_item.content_type.metadata_name].append(
                content_item_summary
            )

        # If incident_to_alert is True then stop recursive
        if not incident_to_alert and content_item.is_incident_to_alert(marketplace):
            logger.debug(
                f'Replacing incident to alert in content item with ID "{content_item.object_id}" and appending to metadata'
            )
            self._add_item_to_metadata_list(
                collected_content_items,
                content_item,
                marketplace,
                incident_to_alert=True,
            )

    def _replace_item_if_has_higher_toversion(
        self,
        content_item: ContentItem,
        content_item_metadata: dict,
        content_item_summary: dict,
        marketplace: MarketplaceVersions,
        incident_to_alert: bool = False,
    ):
        """
        Replaces the content item metadata object in the content items metadata list
        if the given content item's `toversion` is higher than the existing item's metadata `toversion`.

        Args:
            content_item (ContentItem): The current content item to check.
            content_item_metadata (dict): The existing content item metadata object in the list.
            content_item_summary (dict): The current content item summary to update if needed.
            marketplace (MarketplaceVersions): The marketplace to prepare the pack to upload.
            incident_to_alert (bool): Whether the content item's incident_to_alert is set to True or not.
        """
        if marketplace == MarketplaceVersions.XSOAR:
            if parse(content_item.fromversion) > Version("7.9.9"):
                logger.debug(
                    f"Content_item: {content_item.name} has a fromversion {content_item.fromversion} higher than applicable for XSOAR6 marketplace. Skipping metadata update."
                )
                return
            if parse(content_item_metadata["fromversion"]) >= Version("8.0.0"):
                logger.debug(
                    f'Content item:{content_item_metadata["name"]} fromversion: {content_item_metadata["fromversion"]} is not compatible with XSOAR6 marketplace. Replacing'
                )
                content_item_metadata.update(content_item_summary)
                self._set_empty_toversion_if_default(content_item_metadata)
        if parse(content_item.toversion) > parse(
            content_item_metadata["toversion"] or DEFAULT_CONTENT_ITEM_TO_VERSION
        ):
            logger.debug(
                f'Current content item with name "{content_item.name}" has higher `toversion` than the existing object, '
                "updating its metadata."
            )
            content_item_metadata.update(content_item_summary)
            self._set_empty_toversion_if_default(content_item_metadata)
        if (
            content_item.content_type == ContentType.PLAYBOOK
            and content_item.description != content_item_summary["description"]
            and incident_to_alert
        ):
            content_item_metadata["description"] = content_item_summary["description"]

    @staticmethod
    def _set_empty_toversion_if_default(content_item_dict: dict):
        """
        Sets the content item's `toversion` value to empty if it's the default value.

        Args:
            content_item_dict (dict): The content item object to set.
        """
        content_item_dict["toversion"] = (
            content_item_dict["toversion"]
            if content_item_dict["toversion"] != DEFAULT_CONTENT_ITEM_TO_VERSION
            else ""
        )

    @staticmethod
    def _search_content_item_metadata_object(
        collected_content_items: dict,
        item_id: Optional[str],
        item_name: Optional[str],
        item_type_key: Optional[str],
    ) -> Optional[dict]:
        """
        Search a content item object in the content items metadata list by its ID and name.

        Args:
            collected_content_items (dict): The content items metadata list that were already collected.
            item_id (Optional[str]): The content item ID to search.
            item_type_key (Optional[str]): The content item type key to search in its list value that exists in the collected_content_items dict.

        Returns:
            Optional[dict]: The object of the found content item.
        """
        filtered_content_items = [
            content_item
            for content_item in collected_content_items[item_type_key]
            if content_item.get("id") == item_id
            or (
                content_item.get("name") == item_name
                and item_type_key == ContentType.MODELING_RULE.metadata_name
            )  # to avoid duplicate modeling rules with different versions and ids
        ]
        return filtered_content_items[0] if filtered_content_items else None


def should_ignore_item_in_metadata(content_item, marketplace: MarketplaceVersions):
    """
    Checks whether content item should be ignored from metadata
    """
    if content_item.is_test:
        logger.debug(
            f"Skipping {content_item.name} in metadata creation: item is test playbook/script."
        )
    elif content_item.is_silent:
        logger.debug(
            f"Skipping {content_item.name} in metadata creation: item is silent playbook/trigger."
        )
    elif marketplace not in content_item.marketplaces:
        logger.debug(
            f"Skipping {content_item.name} in metadata creation: item is not supported in {marketplace=}."
        )
    else:
        return False
    return True
