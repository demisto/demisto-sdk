from typing import List

import demisto_client
import typer

from demisto_sdk.commands.common.constants import DETACH_ITEM_TYPE_TO_ENDPOINT
from demisto_sdk.commands.common.logger import logger


def detach_content_items(
    ids: List[str],
    item_type: str,
    insecure: bool = False,
):
    verify = (not insecure) if insecure else None
    client = demisto_client.configure(verify_ssl=verify)

    endpoint: str = DETACH_ITEM_TYPE_TO_ENDPOINT.get(item_type, "")
    if not endpoint:
        logger.error(f"<red>Invalid item type: {item_type}</red>")
        raise typer.Exit(code=1)
    logger.info(f"<blue>Detaching {len(ids)} {item_type} items...</blue>")
    for item_id in ids:
        logger.info(f"Processing {item_type} item: {item_id}")
        curr_endpoint = endpoint.replace(":id", item_id)
        try:
            client.generic_request(curr_endpoint, "POST")
            logger.info(f"<green>Item: {item_id} ({item_type}) was detached</green>")
        except Exception as e:
            logger.error(f"<red>Failed to detach {item_id}: {e}</red>")
