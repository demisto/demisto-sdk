import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.update_xsoar_config_file.update_xsoar_config_file import (
    XSOARConfigFileUpdater,
)


@logging_setup_decorator
def xsoar_config_file_update(
    ctx: typer.Context,
    pack_id: str = typer.Option(
        None, help="The Pack ID to add to XSOAR Configuration File"
    ),
    pack_data: str = typer.Option(
        None,
        help="The Pack Data to add to XSOAR Configuration File - Pack URL for Custom Pack and Pack Version for OOTB Pack",
    ),
    add_marketplace_pack: bool = typer.Option(
        False,
        help="Add a Pack to the MarketPlace Packs section in the Configuration File",
    ),
    add_custom_pack: bool = typer.Option(
        False, help="Add the Pack to the Custom Packs section in the Configuration File"
    ),
    add_all_marketplace_packs: bool = typer.Option(
        False,
        help="Add all the installed MarketPlace Packs to the marketplace_packs in XSOAR Configuration File",
    ),
    insecure: bool = typer.Option(False, help="Skip certificate validation"),
    file_path: str = typer.Option(
        None,
        help="XSOAR Configuration File path, the default value is in the repo level",
    ),
):
    """
    Handle your XSOAR Configuration File.
    Add automatically all the installed MarketPlace Packs to the marketplace_packs section in XSOAR Configuration File.
    Add a Pack to both marketplace_packs and custom_packs sections in the Configuration File.
    """
    file_updater = XSOARConfigFileUpdater(
        pack_id=pack_id,
        pack_data=pack_data,
        add_marketplace_pack=add_marketplace_pack,
        add_custom_pack=add_custom_pack,
        add_all_marketplace_packs=add_all_marketplace_packs,
        insecure=insecure,
        file_path=file_path,
    )
    return file_updater.update()
