import csv
import traceback
from io import StringIO
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    GENERAL_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import (
    handle_deprecated_args,
    logger,
    logging_setup,
    logging_setup_decorator,
)
from demisto_sdk.commands.common.tools import get_max_version

app = typer.Typer()


SCHEMA_TYPE_STRING = "String"
SCHEMA_TYPE_NUMBER = "Number"
SCHEMA_TYPE_BOOLEAN = "Boolean"


@logging_setup_decorator
@app.command(
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": ["-h", "--help"],
    },
)
def generate_modeling_rules(
    ctx: typer.Context,
    mapping: Path = typer.Option(
        ...,
        "-m",
        "--mapping",
        exists=True,
        resolve_path=True,
        show_default=False,
        help=(
            "The Path to a csv or tsv file containing the mapping for the modeling rules."
        ),
    ),
    raw_event_path: Path = typer.Option(
        ...,
        "-re",
        "--raw_event",
        exists=True,
        resolve_path=True,
        show_default=False,
        help=("The path to a raw event from the api call in a json format."),
    ),
    one_data_model_path: Path = typer.Option(
        ...,
        "-dm",
        "--data_model",
        exists=True,
        resolve_path=True,
        show_default=False,
        help=("The path to The one data model schema."),
    ),
    output_path: Path = typer.Option(
        ...,
        "-o",
        "--output",
        exists=True,
        resolve_path=True,
        show_default=False,
        help=(
            "A path to the folder you want to generate the modeling rules in. Best practice to put the working pack path"
        ),
    ),
    vendor: str = typer.Option(
        "test",
        "-ve",
        "--vendor",
        show_default=False,
        help=("The vendor name of the product in snake_case"),
    ),
    product: str = typer.Option(
        "test",
        "-p",
        "--product",
        show_default=False,
        help=("The name of the product in snake_case"),
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "-lp",
        "--log-file-path",
        help="Path to save log files onto.",
    ),
):
    logging_setup(
        console_threshold=console_log_threshold,
        file_threshold=file_log_threshold,
        path=log_file_path,
        calling_function=__name__,
    )
    handle_deprecated_args(ctx.args)
    try:
        path_prefix = snake_to_camel_case(vendor)
        outputfile_schema = Path(output_path, (f"{path_prefix}ModelingRules.json"))
        outputfile_xif = Path(output_path, (f"{path_prefix}ModelingRules.xif"))
        outputfile_yml = Path(output_path, (f"{path_prefix}ModelingRules.yml"))
        data_set_name = f"{vendor}_{product}_raw".lower()

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
            logger.error(
                f"<red>{sio.getvalue()}</red>",
            )
        raise typer.Exit(1)


class RawEventData:
    def __init__(
        self,
        field_path_raw,
        is_array_raw,
        type_raw,
    ):
        """
        field_path_raw - the path to the field in the raw event
        is_array_raw - is the raw event of type array.
        type_raw - the type of the raw event field.
        """
        self.field_path_raw = field_path_raw
        self.is_array_raw = is_array_raw
        self.type_raw = type_raw

    def create_schema_types(self) -> dict:
        return {"type": self.type_raw, "is_array": self.is_array_raw}

    def __eq__(self, other) -> bool:
        if isinstance(other, RawEventData):
            return (
                self.field_path_raw == other.field_path_raw
                and self.is_array_raw == other.is_array_raw
                and self.type_raw == other.type_raw
            )
        return False


class MappingField:
    def __init__(
        self,
        xdm_rule,
        xdm_field_type,
        xdm_class_type,
        mapped_to_raw: List[RawEventData],
    ):
        """
        xdm_rule - The xdm rule
        field_type - the field type in the schema.
        xdm_class_type - xdm rule type
        """
        self.xdm_rule = xdm_rule
        self.xdm_field_type = xdm_field_type
        self.xdm_class_type = xdm_class_type
        self.mapped_to_raw = mapped_to_raw

    def get_mapped_to_raw_list(self) -> List[RawEventData]:
        return self.mapped_to_raw


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


def coalesce_wrap(raw_event_data_list: List[str]) -> str:
    return f'coalesce({", ".join(raw_event_data_list)})'


def create_xif_header(dataset_name: str) -> str:
    """
    Creates the xif header
    """
    xif_rule = ""
    xif_rule += f"[MODEL: dataset={dataset_name}]\n"
    xif_rule += "alter\n"
    return xif_rule


def snake_to_camel_case(snake_str) -> str:
    """
    Args:
        snake_str(str): a string in snake_case
    Returns:
        The same string in CameCase
    """
    components = snake_str.split("_")
    return "".join([name.capitalize() for name in components])


def handle_raw_evnet_data(field_paths: str, raw_event: dict) -> List[RawEventData]:
    """
    Args:
        field_paths (str): A '|' seperated string of raw event field paths.
    Returns:
        (List[RawEventData]): A list of RawEventData objects
    """
    field_paths = field_paths.split("|")
    field_paths = list(map(lambda path: path.strip(), field_paths))
    raw_event_data_list: List[RawEventData] = []
    for field_path in field_paths:
        type_raw, is_array_raw = extract_raw_type_data(raw_event, field_path)
        raw_event_data_list.append(
            RawEventData(
                field_path_raw=field_path, is_array_raw=is_array_raw, type_raw=type_raw
            )
        )

    return raw_event_data_list


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
    xdm_onedata_model_names = xdm_rule_to_dclass.keys()
    for field_name, xdm_field_name in zip(name_columen, xdm_one_data_model):
        raw_event_data_list: List[RawEventData] = handle_raw_evnet_data(
            field_name, raw_event
        )

        if xdm_field_name not in xdm_onedata_model_names:
            if not xdm_field_name:
                logger.warning(f"No xdm rule was specified for {field_name}")
            else:
                raise ValueError(
                    f"No XDM field {xdm_field_name} exists in the onedata model. Please check your modelling rules file."
                )

        xdm_field_type = xdm_rule_to_dtype.get(xdm_field_name)
        xdm_class_type = xdm_rule_to_dclass.get(xdm_field_name)

        mapping_list.append(
            MappingField(
                xdm_rule=xdm_field_name,
                xdm_field_type=xdm_field_type,
                xdm_class_type=xdm_class_type,
                mapped_to_raw=raw_event_data_list,
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


def read_mapping_file(mapping: Path) -> Tuple:
    """
    Reads the security mapping file and extracts the raw_path and the Coresponding xdm field.
    """
    name_column = []
    xdm_one_data_model = []

    with open(mapping, newline="") as csvfile:
        reader = csv.DictReader(
            csvfile, delimiter="\t" if str(mapping).endswith("tsv") else ","
        )

        if not reader.fieldnames:
            raise ValueError(
                f"The mapping file {mapping} does not have proper headers."
            )

        for header in ["One Data Model", "Raw Event Path"]:
            if header not in reader.fieldnames:
                raise NameError(
                    f'The mapping file {mapping} must contain "One Data Model" and "Raw Event Path" columns'
                    f"This mapping file is missing the {header=}"
                )

        for row in reader:
            name_column.append(row["Raw Event Path"])
            xdm_one_data_model.append(row["One Data Model"])

    return (name_column, xdm_one_data_model)


def create_xif_for_raw_data(
    xdm_rule, xdm_field_type, xdm_class_type, field_path_raw, type_raw
) -> str:
    """
    Creates the raw data part of the xif file.
    """
    logger.info(
        f'field name: "{field_path_raw}" - xdm type: {xdm_field_type} - raw type {type_raw}'
    )
    name = field_path_raw

    if "." in field_path_raw:
        dict_keys = field_path_raw.split(".")
        prefix = dict_keys[0]
        suffix = ".".join(dict_keys[1:])
        if xdm_class_type == "Array":
            name = json_extract_array_wrap(prefix, suffix)
            return name
        else:
            name = json_extract_scalar_wrap(prefix, suffix)

    if xdm_field_type != convert_raw_type_to_xdm_type(type_raw):
        # Type casting
        name = convert_to_xdm_type(name, xdm_field_type)

    if xdm_class_type == "Array":
        # convert a scalar into an array
        name = array_create_wrap(name)

    return name


def create_xif_file(
    mapping_list: List[MappingField], outputfile_xif: Path, dataset_name: str
) -> None:
    """
    Created the xif file for the modeling rules
    """
    logger.info("Generating xif file")
    xif_rule = create_xif_header(dataset_name)
    for mapping_rule in mapping_list:
        xdm_rule = mapping_rule.xdm_rule
        xdm_field_type = mapping_rule.xdm_field_type
        xdm_class_type = mapping_rule.xdm_class_type

        if not mapping_rule:
            raise ValueError(f"No raw field path was given for {xdm_rule}")

        raw_event_data: RawEventData = mapping_rule.get_mapped_to_raw_list()[0]
        field_path_raw = raw_event_data.field_path_raw
        type_raw = raw_event_data.type_raw
        if len(mapped_to_raw := mapping_rule.get_mapped_to_raw_list()) > 1:
            coales_list: List[str] = []
            for raw_event_data in mapped_to_raw:
                raw_event_data = raw_event_data
                field_path_raw = raw_event_data.field_path_raw
                type_raw = raw_event_data.type_raw
                coales_list.append(
                    create_xif_for_raw_data(
                        xdm_rule,
                        xdm_field_type,
                        xdm_class_type,
                        field_path_raw,
                        type_raw,
                    )
                )
                rule = coalesce_wrap(coales_list)
        else:
            rule = create_xif_for_raw_data(
                xdm_rule, xdm_field_type, xdm_class_type, field_path_raw, type_raw
            )

        xif_rule += f"\t{xdm_rule} = {rule},\n"

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
        for raw_event_data in mapping_rule.get_mapped_to_raw_list():
            keys_list = raw_event_data.field_path_raw.split(".")
            name = keys_list[0]
            if name not in name_type_dict:
                name_type_dict[name] = raw_event_data.create_schema_types()
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
    for key in keys_split:
        if isinstance(temp, dict):
            temp = temp.get(key)  # type: ignore[assignment]
        else:
            # for example when we have an array inside of a dict
            logger.warning(
                f"{path_to_dict_field=} \nWas not found in the event you provided, or is not of type dict. Please check the Raw event"
            )

    discovered = discover_type(temp)
    return ("string", True) if discovered == "array" else (discovered, False)


def extract_data_from_all_xdm_schema(path: Path) -> Tuple[dict, dict]:
    """
    Extracts from the XDM full schema the columns of the xdm rule, datatype, and data class
    Args:
        path (str): The path to the location of the all xdm rules schema
    Returns:
        Tuple[dict, dict]: {xdm_rule: data_type}, {xdm_rule: data_class}
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
