import csv
import logging
import traceback
from io import StringIO
from pathlib import Path
from typing import List, Tuple

import typer

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    GENERAL_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.logger import setup_rich_logging
from demisto_sdk.commands.common.tools import get_max_version

app = typer.Typer()
logger = logging.getLogger("demisto-sdk")
json = JSON_Handler()
yaml = YAML_Handler()

SCHEMA_TYPE_STRING = "String"
SCHEMA_TYPE_NUMBER = "Number"
SCHEMA_TYPE_BOOLEAN = "Boolean"


@app.command(no_args_is_help=True)
def generate_modeling_rules(
    mapping: Path = typer.Argument(
        ...,
        exists=True,
        resolve_path=True,
        show_default=False,
        help=(
            "The Path to a csv or tsv file containing the mapping for the modeling rules."
        ),
    ),
    raw_event_path: Path = typer.Argument(
        ...,
        exists=True,
        resolve_path=True,
        show_default=False,
        help=("The path to a raw event from the api call in a json format."),
    ),
    one_data_model_path: Path = typer.Argument(
        ...,
        exists=True,
        resolve_path=True,
        show_default=False,
        help=("The path to The one data model schema."),
    ),
    output_path: Path = typer.Argument(
        ...,
        exists=True,
        resolve_path=True,
        show_default=False,
        help=(
            "A path to the pack you want to generate the modeling rules in. Best practice to put the working pack path"
        ),
    ),
    vendor: str = typer.Argument(
        default="test",
        show_default=False,
        help=("The vendor name of the product in snake_case"),
    ),
    product: str = typer.Argument(
        default="test",
        show_default=False,
        help=("The name of the product in snake_case"),
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
        path_prefix = snake_to_camel_case(vendor)
        outputfile_schema = Path(
            output_path, (f"{path_prefix}ModelingRules.json")
        )
        outputfile_xif = Path(output_path, (f"{path_prefix}ModelingRules.xif"))
        outputfile_yml = Path(output_path, (f"{path_prefix}ModelingRules.yml"))
        data_set_name = f"{vendor.lower()}_{product.lower()}_raw"

        name_columen, xdm_one_data_model = read_mapping_file(mapping)

        with open(raw_event_path) as f:
            raw_event = json.load(f)

        xdm_rule_to_dtype, xdm_rule_to_dclass = extract_data_from_all_xdm_schema(
            one_data_model_path
        )

        mapping_list = init_mapping_field_list(
            name_columen,
            xdm_one_data_model,
            raw_event,
            xdm_rule_to_dtype,
            xdm_rule_to_dclass,
        )

        create_scheme_file(mapping_list, data_set_name, outputfile_schema)
        create_xif_file(mapping_list, outputfile_xif, data_set_name)
        create_yml_file(outputfile_yml, vendor, product)

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


def to_string_wrap(s: str) -> str:
    """
    Gets a xql and wraps it with a to_string function
    """
    return f"to_string({s})"


def to_number_wrap(s: str) -> str:
    """
    Gets a xql and wraps it with a to_number function
    """
    return f"to_number({s})"


def json_extract_array_wrap(prefix: str, suffix: str) -> str:
    return f'json_extract_array({prefix}, "$.{suffix}")'


def json_extract_scalar_wrap(prefix: str, suffix: str) -> str:
    return f'json_extract_scalar({prefix}, "$.{suffix}")'


def array_create_wrap(s: str) -> str:
    return f"arraycreate({s})"


def create_xif_header(dataset_name: str) -> str:
    """
    Creates the xif header
    """
    xif_rule = ""
    xif_rule += f"[MODEL: dataset={dataset_name}]\n"
    xif_rule += "| alter\n"
    return xif_rule


def snake_to_camel_case(snake_str) -> str:
    """
    Args:
        snake_str(str): a string in snake_case
    Returns:
        The same string in CameCase
    """
    components = snake_str.split('_')
    return ''.join([name.capitalize() for name in components])


def init_mapping_field_list(
    name_columen: list,
    xdm_one_data_model: list,
    raw_event: dict,
    xdm_rule_to_dtype: dict,
    xdm_rule_to_dclass: dict,
) -> List[MappingField]:
    """
    This function takes all the data gathered and generates the list of MappingFields
    """
    mapping_list = []
    for (field_name, xdm_field_name) in zip(name_columen, xdm_one_data_model):
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
    converting_dict = {
        "string": SCHEMA_TYPE_STRING,
        "int": SCHEMA_TYPE_NUMBER,
        "boolean": SCHEMA_TYPE_BOOLEAN,
    }

    return converting_dict.get(schema_type, SCHEMA_TYPE_STRING)


def convert_to_xdm_type(name: str, xdm_type: str) -> str:
    """
    Wraps the xql with a conversion to fit the xdm schema if the raw response type is incompatible with the schema type
    """
    if xdm_type == "String":
        name = to_string_wrap(name)
    elif xdm_type == "Number":
        name = to_number_wrap(name)

    return name


def read_mapping_file(mapping: Path):
    name_column = []
    xdm_one_data_model = []

    with open(mapping, newline="") as csvfile:
        reader = csv.DictReader(
            csvfile, delimiter="\t" if str(mapping).endswith("tsv") else ","
        )

        for row in reader:
            name_column.append(row["Name"])
            xdm_one_data_model.append(row["XDM Field One Data Model"])

    return (name_column, xdm_one_data_model)


def create_xif_file(
    mapping_list: List[MappingField], outputfile_xif: Path, dataset_name: str
) -> None:
    """
    Created the xif file for the modeling rules
    """
    logger.info("Generating xif file")
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
                name = json_extract_array_wrap(prefix, suffix)
                xif_rule += f"\t{mapping_rule.xdm_rule} = {name},\n"
                continue
            else:
                name = json_extract_scalar_wrap(prefix, suffix)

        if mapping_rule.xdm_field_type != convert_raw_type_to_xdm_type(
            mapping_rule.type_raw
        ):
            # Type casting
            name = convert_to_xdm_type(name, mapping_rule.xdm_field_type)

        if mapping_rule.xdm_class_type == "Array":
            # convert a scalar into an array
            name = array_create_wrap(name)

        xif_rule += f"\t{mapping_rule.xdm_rule} = {name},\n"

    xif_rule = replace_last_char(xif_rule)

    with open(outputfile_xif, "w") as f:
        f.write(xif_rule)

    logger.info("Finished generating xif file\n")


def replace_last_char(s: str) -> str:
    """
    Replaces the second last char of the xif file to be ; instead of ,
    """
    return f"{s[:-2]};{s[-1]}" if s else s


def create_scheme_file(
    mapping_list: List[MappingField], dataset_name, outputfile_schema
) -> None:
    """
    Creates the .json schema file
    """
    logger.info("creating modeling rules schema")
    name_type_dict = {}
    for mapping_rule in mapping_list:
        keys_list = mapping_rule.field_path_raw.split(".")
        name = keys_list[0]
        if name not in name_type_dict:
            name_type_dict[name] = mapping_rule.create_schema_types()
    modeling_rules_json = {dataset_name: name_type_dict}

    with open(outputfile_schema, "w") as f:
        json.dump(modeling_rules_json, f, indent=4)
    logger.info("Finished creating modeling rules schema\n")


def process_yml_name(product: str, vendor: str) -> str:
    """
    Returns the name of the modeling rules capitalized
    """
    name = f"{product} {vendor} Modeling Rule\n"
    name = name.replace("_", " ")
    list_names = name.split()
    capitalized_name_list = [name.capitalize() for name in list_names]
    return " ".join(capitalized_name_list)


def create_yml_file(outputfile_yml: Path, vendor: str, product: str) -> None:
    """
    Creates the yml file of the modeling rules
    """
    logger.info("creating modeing rules yml file")
    max_version = get_max_version(
        [
            GENERAL_DEFAULT_FROMVERSION,
            FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.MODELING_RULE, "6.10.0"),
        ]
    )
    yml_file = {
        "fromversion": f"{max_version}",
        "id": f"{product}_{vendor}_modeling_rule",
        "name": f"{process_yml_name(product, vendor)}",
        "rules": "",
        "schema": "",
        "tags": f"{product}",
    }

    with open(outputfile_yml, "w") as f:
        yaml.dump(yml_file, f)

    logger.info("Finished creating modeing rules yml file\n")


def discover_type(value) -> str:
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
    for key in keys_split[:-1]:
        if isinstance(temp, dict):
            temp = temp.get(key)  # type: ignore[assignment]
        else:
            # for example when we have an array inside of a dict
            logger.info(
                f"{key=} is not of type dict, or was not found in the event you provided. Please check the Raw event"
            )

    discovered = discover_type(temp)
    return ("string", True) if discovered == "array" else (discovered, False)

    # if discovered == 'array':
    # The value is array and we want to check what is the type in the array
    # return 'string', True
    # Security team said in the schema if its array we put type string.
    # if temp:
    #     inner_array_type = discover_type(temp[0])
    #     return inner_array_type, True
    # return discovered, False


def extract_data_from_all_xdm_schema(path: Path) -> Tuple[dict, dict]:
    """
    Extracts from the XDM full schema the columns of the xdm rule, datatype, and data class
    Args:
        path (str): The path to the location of the all xdm rules schema
    Returns:
        Tuple[dict, dict]: {xdf_rule: data_type}, {xdm_rule: data_class}
    """
    with open(path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        columns_to_keep = ["name", "datatype", "dataclass"]
        data = {
            row["name"]: {col: row[col] for col in columns_to_keep if col in row}
            for row in reader
        }
        xdm_rule_to_dtype = {
            k: v["datatype"] for k, v in data.items() if "datatype" in v
        }
        xdm_rule_to_dclass = {
            k: v["dataclass"] for k, v in data.items() if "dataclass" in v
        }

        return xdm_rule_to_dtype, xdm_rule_to_dclass


if __name__ == "__main__":
    app()
