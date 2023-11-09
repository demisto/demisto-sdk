from typing import TYPE_CHECKING, Optional

from packaging.version import Version

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.base_content import (
        BaseContent,
    )
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class NotUploadableException(NotImplementedError):
    def __init__(self, item: "BaseContent", description: Optional[str] = None) -> None:
        description_suffix = f" {description}" if description else ""
        super().__init__(
            f"Object ({item.content_type} {item.object_id}) cannot be uploaded{description_suffix}"
        )


class NotIndivitudallyUploadableException(NotUploadableException):
    """
    Some content items must be uploaded as part of a pack.
    """

    def __init__(self, item: "BaseContent"):
        super().__init__(
            item,
            description=" independently. Use the -z flag to upload the whole pack, zipped.",
        )


class IncompatibleUploadVersionException(NotUploadableException):
    def __init__(self, item: "ContentItem", target: Version) -> None:
        self.item = item
        if target > Version(item.toversion):
            message = f"to_version={item.toversion}"
        elif target < Version(item.fromversion):
            message = f"from_version={item.fromversion}"
        else:
            raise RuntimeError(
                f"Invalid version comparison for {item.path} ({item.fromversion=}, {item.toversion=}, {target=})"
            )

        super().__init__(
            item,
            f". Target version {target} mismatch: "
            f"{item.content_type} {item.normalize_name} has {message}",
        )
