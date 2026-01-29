from typing import List, Optional

import demisto_client

from demisto_sdk.commands.upload.uploader import ItemReattacher


def reattach_content_items(
    ids: List[str],
    item_type: str,
    insecure: bool = False,
):
    verify = (not insecure) if insecure else None
    client = demisto_client.configure(verify_ssl=verify)

    reattacher = ItemReattacher(client=client)

    for item_id in ids:
        reattacher.reattach_item(item_id, item_type)
