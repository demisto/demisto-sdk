import json
import logging
import traceback
from io import StringIO
from pathlib import Path
from typing import List

import pandas as pd
import typer

from demisto_sdk.commands.common.logger import setup_rich_logging

app = typer.Typer()
logger = logging.getLogger("demisto-sdk")


@app.command(no_args_is_help=True)
def generate_modeling_rules(
    mapping: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=(
            "The Path to a csv or tsv file containing the mapping for the modeling rules."
        ),
    ),
    raw_event_path: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=("The path to a raw event from the api call in a json format."),
    ),
    output_path: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help=(
            "A path to the pack you want to generate the modeling rules in. Best practice to put the working pack path"
        ),
    ),
    vendor: str = typer.Argument(
        default="test",
        show_default=False,
        help=("The vendor name of the product"),
    ),
    product: str = typer.Argument(
        default="test",
        show_default=False,
        help=("The vendor name of the product"),
    ),
    verbosity: int = typer.Option(
        0,
        "-v",
        "--verbose",
        clamp=True,
        max=3,
        show_default=True,
        help="Verbosity level -v / -vv / .. / -vvv",
        rich_help_panel="Logging Configuration",
    ),
    quiet: bool = typer.Option(
        False,
        help="Quiet output - sets verbosity to default.",
        rich_help_panel="Logging Configuration",
    ),
    log_path: Path = typer.Option(
        None,
        "-lp",
        "--log-path",
        resolve_path=True,
        show_default=False,
        help="Path of directory in which you would like to store all levels of logs. If not given, then the "
        '"log_file_name" command line option will be disregarded, and the log output will be to stdout.',
        rich_help_panel="Logging Configuration",
    ),
    log_file_name: str = typer.Option(
        "generate_modeling_rules.log",
        "-ln",
        "--log-name",
        resolve_path=True,
        help="The file name (including extension) where log output should be saved to.",
        rich_help_panel="Logging Configuration",
    ),
):
    errors = False
    try:
        setup_rich_logging(verbosity, quiet, log_path, log_file_name)

        outputfile_schema = output_path.joinpath(
            f"{vendor}_{product}_modeling_rules.json"
        )
        outputfile_xif = output_path.joinpath(f"{vendor}_{product}_modeling_rules.xif")
        outputfile_yml = output_path.joinpath(f"{vendor}_{product}_modeling_rules.yml")
        data_set_name = f"{vendor.lower()}_{product.lower()}_raw"
        sdk_from_version = "6.10.0"  # @TODO: get this from the schema of the xsiam

        if ".tsv" in str(mapping):
            modeling_rules_df = pd.read_csv(mapping, sep="\t")
        else:
            modeling_rules_df = pd.read_csv(mapping)

        with open(raw_event_path) as f:
            raw_event = json.load(f)

        schema_path = "/Users/okarkkatz/dev/demisto/test_folder/Schema.csv"  # @TODO: handle taking this from the Yaron noiman
        xdm_rule_to_dtype, xdm_rule_to_dclass = extract_data_from_all_xdm_schema(
            schema_path
        )

        mapping_list = init_mapping_field_list(
            modeling_rules_df, raw_event, xdm_rule_to_dtype, xdm_rule_to_dclass
        )

        create_scheme_file(mapping_list, data_set_name, outputfile_schema)
        create_xif_file(mapping_list, outputfile_xif, data_set_name)
        create_yml_file(outputfile_yml, vendor, product, sdk_from_version)

    except Exception:
        with StringIO() as sio:
            traceback.print_exc(file=sio)
            logger.error(f"[red]{sio.getvalue()}[/red]", extra={"markup": True})
        errors = True
    if errors:
        raise typer.Exit(1)


class MappingField:
    def __init__(
        self,
        xdm_rule,
        field_path_raw,
        xdm_field_type,
        xdm_class_type,
        is_array_raw,
        type_raw,
    ):
        """
        xdm_rule - The xdm rule
        field_path_raw - the path to the field in the raw event
        field_type - the field type in the schema.
        xdm_class_type - xdm rule type
        is_array_raw - is the raw event of type array.
        type_raw - the type of the raw event field.
        """
        self.xdm_rule = xdm_rule
        self.field_path_raw = field_path_raw
        self.xdm_field_type = xdm_field_type
        self.xdm_class_type = xdm_class_type
        self.is_array_raw = is_array_raw
        self.type_raw = type_raw

    def create_schema_types(self) -> dict:
        return {"type": self.type_raw, "is_array": self.is_array_raw}


def to_string(s: str) -> str:
    """
    Gets a xql and wraps it with a to_string function
    """
    return f"to_string({s})"


def to_number(s: str) -> str:
    """
    Gets a xql and wraps it with a to_number function
    """
    return f"to_number({s})"


def json_extract_array(prefix: str, suffix: str) -> str:
    return f'json_extract_array({prefix}, "$.{suffix}")'


def json_extract_scalar(prefix: str, suffix: str) -> str:
    return f'json_extract_scalar({prefix}, "$.{suffix}")'


def array_create(s: str) -> str:
    return f"arraycreate({s})"


def create_xif_header(dataset_name: str) -> str:
    """
    Creates the xif header
    """
    xif_rule = ""
    xif_rule += f"[MODEL: dataset={dataset_name}]\n"
    xif_rule += "| alter\n"
    return xif_rule


def init_mapping_field_list(
    modeling_rules_df: pd.DataFrame,
    raw_event: dict,
    xdm_rule_to_dtype: dict,
    xdm_rule_to_dclass: dict,
) -> List[MappingField]:
    """
    This function takes all the data gathered and generates the list of MappingFields
    """
    name_columen = modeling_rules_df["Name"]
    xdm_one_data_model = modeling_rules_df["XDM Field One Data Model"]
    names_list = name_columen.to_numpy()
    xdm_one_data_model_list = xdm_one_data_model.to_numpy()

    mapping_list = []
    for (field_name, xdm_field_name) in zip(names_list, xdm_one_data_model_list):
        type_raw, is_array_raw = extract_raw_type_data(raw_event, field_name)
        xdm_field_type = xdm_rule_to_dtype.get(xdm_field_name)
        xdm_class_type = xdm_rule_to_dclass.get(xdm_field_name)

        mapping_list.append(
            MappingField(
                xdm_rule=xdm_field_name,
                field_path_raw=field_name,
                xdm_field_type=xdm_field_type,
                xdm_class_type=xdm_class_type,
                is_array_raw=is_array_raw,
                type_raw=type_raw,
            )
        )

    return mapping_list


def convert_raw_type_to_xdm_type(schema_type: str) -> str:
    """
    returns the xdm type convention
    """
    converting_dict = {"string": "String", "int": "Number", "boolean": "Boolean"}

    return converting_dict.get(schema_type, "String")


def convert_to_xdm_type(name: str, xdm_type: str) -> str:
    """
    Wraps the xql with a conversion to fit the xdm schema if the raw response type is incompatible with the schema type
    """
    if xdm_type == "String":
        name = to_string(name)
    elif xdm_type == "Number":
        name = to_number(name)

    return name


def create_xif_file(
    mapping_list: List[MappingField], outputfile_xif: Path, dataset_name: str
) -> None:
    """
    Created the xif file for the modeling rules
    """
    logger.info("Generating xif file\n")
    xif_rule = create_xif_header(dataset_name)
    for mapping_rule in mapping_list:
        logger.info(
            f'field name: "{mapping_rule.field_path_raw}" - xdm type: {mapping_rule.xdm_field_type} - raw type {mapping_rule.type_raw}'
        )
        name = mapping_rule.field_path_raw

        if "." in mapping_rule.field_path_raw:
            dict_keys = mapping_rule.field_path_raw.split(".")
            prefix = dict_keys[0]
            suffix = ".".join(dict_keys[1:])
            if mapping_rule.xdm_class_type == "Array":
                name = json_extract_array(prefix, suffix)
                xif_rule += f"\t{mapping_rule.xdm_rule} = {name},\n"
                continue
            else:
                name = json_extract_scalar(prefix, suffix)

        if mapping_rule.xdm_field_type != convert_raw_type_to_xdm_type(
            mapping_rule.type_raw
        ):
            # Tpue casting
            name = convert_to_xdm_type(name, mapping_rule.xdm_field_type)

        if mapping_rule.xdm_class_type == "Array":
            # convert a scalar into an array
            name = array_create(name)

        xif_rule += f"\t{mapping_rule.xdm_rule} = {name},\n"

    xif_rule = replace_last_char(xif_rule)

    with open(outputfile_xif, "w") as f:
        f.write(xif_rule)


def replace_last_char(s: str) -> str:
    """
    Replaces the last char of the xif file to be ;
    """
    s = s[:-2]
    s += ";\n"
    return s


def create_scheme_file(
    mapping_list: List[MappingField], dataset_name, outputfile_schema
):
    """
    Creates the .json schema file
    """
    logger.info("creating modeling rules schema\n")
    name_type_dict = {}
    for mapping_rule in mapping_list:
        keys_list = mapping_rule.field_path_raw.split(".")
        name = keys_list[0]
        if name not in name_type_dict:
            name_type_dict[name] = mapping_rule.create_schema_types()
    modeling_rules_json = {dataset_name: name_type_dict}

    with open(outputfile_schema, "w") as f:
        res = json.dumps(modeling_rules_json, indent=4)
        f.write(res)


def process_yml_name(product: str, vendor: str):
    """
    Returns the name of the modeling rules capitalized
    """
    name = f"{product} {vendor} Modeling Rule\n"
    name = name.replace("_", " ")
    list_names = name.split()
    capitalized_name_list = [name.capitalize() for name in list_names]
    return " ".join(capitalized_name_list)


def create_yml_file(outputfile_yml: Path, vendor: str, product: str, sdk_from_version):
    """
    Creates the yml file of the modeling rules
    """
    logger.info("creating modeing rules yml file\n")
    yml_file = (
        f"fromversion: {sdk_from_version}\n"
        f"id: {product}_{vendor}_modeling_rule\n"
        f"name: {process_yml_name(product, vendor)}\n"
        "rules: ''\n"
        "schema: ''\n"
        f"tags: {product}\n"
    )

    with open(outputfile_yml, "w") as f:
        f.write(yml_file)


def discoverType(value) -> str:
    """
    discovers the type of the event fiels and return a type compatible with the modeling rules schema
    """
    if isinstance(value, list):
        return "array"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    return "string"


def extract_raw_type_data(event: dict, path_to_dict_field: str) -> tuple:
    """
    Extract the type of the field in the dict event
    Args:
        event (dict): A single raw event
        path_to_dict_field (str): The path to the field in the raw event.
    Returns:
        (tuple): (type of the value - (str): is field of array type - (boolean))
    """
    if not event:
        raise ValueError("The evnet provided is empty")
    if not isinstance(event, dict):
        raise ValueError("The array provided is not of type dict")

    keys_split = path_to_dict_field.split(".")
    temp: dict = event
    for key in keys_split:
        if isinstance(temp, dict):
            temp = temp.get(key)  # type: ignore
        else:
            # for example when we have an array inside of a dict
            logger.info(
                f"{key=} is not of type dict, or was not found in the event you provided"
            )

    discovered = discoverType(temp)
    return ("string", True) if discovered == "array" else (discovered, False)

    # if discovered == 'array':
    # The value is array and we want to check what is the type in the array
    # return 'string', True
    # Security team said in the schema if its array we put type string.
    # if temp:
    #     inner_array_type = discoverType(temp[0])
    #     return inner_array_type, True
    # return discovered, False


def extract_data_from_all_xdm_schema(path: str) -> tuple:
    """
    Extracts for the XDM full schema the columns of the xdm rule, datatype, and data class
    Args:
        path (str): The path to the location of the all xdm rules schema
    Returns:
        (tuple): {xdf_rule: data_type}, {xdm_rule: data_class}
    """
    schema_all_dict = pd.read_csv(path)

    columns_to_keep = ["name", "datatype", "dataclass"]
    df_dict = schema_all_dict[columns_to_keep].set_index("name")
    data_from_xdm_full_schema = df_dict.to_dict()

    data_from_xdm_full_schema = df_dict.to_dict()
    xdm_rule_to_dtype = data_from_xdm_full_schema.get("datatype")
    xdm_rule_to_dclass = data_from_xdm_full_schema.get("dataclass")

    return xdm_rule_to_dtype, xdm_rule_to_dclass


if __name__ == "__main__":
    app()
