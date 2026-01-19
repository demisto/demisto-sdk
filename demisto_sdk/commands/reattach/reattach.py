from typing import List, Optional

import demisto_client

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.upload.uploader import ItemReattacher


def reattach_content_items(
    ids: List[str],
    item_type: Optional[str],
    insecure: bool = False,
    reattach_all: bool = False,
):
    verify = (not insecure) if insecure else None
    client = demisto_client.configure(verify_ssl=verify)

    reattacher = ItemReattacher(client=client)

    if reattach_all:
        logger.info("<blue>Reattaching all detached items</blue>")
        all_files: dict = reattacher.get_all_detachable_items()
        for item_type_key, item_list in all_files.items():
            for item in item_list:
                detached = item.get("detached", "")
                if detached and detached != "false":
                    if item_id := item.get("id"):
                        reattacher.reattach_item(item_id, item_type_key)
        return

    for item_id in ids:
        reattacher.reattach_item(item_id, item_type)
