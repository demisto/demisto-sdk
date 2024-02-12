import re
import shutil
from pprint import pformat
from typing import List, Optional, Union

import demisto_client
from packaging.version import Version
from wcmatch.pathlib import IGNORECASE, Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import MODELING_RULE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class SingleModelingRule:
    """Parsed object model for a single rule.

    The old xdm model syntax was such that a single rule would actually be composed of multiple rules, each mapping
    to a different datamodel. This meant that a single xif file typically was composed of multiple rules each mapping
    to a different datamodel. This class represents a single rule, and is used to parse the old xif format into a list
    of these objects. This class structure is used to maintain backwards compatibility with the old xif format, while
    allowing forward compatibility with the new xdm format in which a xif file maps to a single rule.

    Attributes:
        rule_text (str): The raw text of the rule
        dataset (str): The dataset that the rule applies to
        vendor (str): The vendor that the rule applies to
        product (str): The product that the rule applies to
        datamodel (str): The datamodel that the rule applies to (Only used in the old xif format)
        fields (List[str]): The xdm fields that the rule maps to
        filter_condition (str): The filter condition defining when to apply the modeling rule mapping
    """

    RULE_HEADER_REGEX = re.compile(
        r"\[MODEL:\s*model\s*=\s*\"?(?P<datamodel>\w+)\"?\s*,?\s*"
        r"dataset\s*=\s*\"?(?P<dataset>\w+)\"?\]"
    )
    RULE_HEADER_REGEX_REVERSED = re.compile(
        r"\[MODEL:\s*dataset\s*=\s*\"?(?P<dataset>\w+)\"?\s*,?\s*"
        r"model\s*=\s*\"?(?P<datamodel>\w+)\"?\]"
    )
    RULE_HEADER_NEW_REGEX = re.compile(
        r"\[MODEL:\s*dataset\s*=\s*\"?(?P<dataset>\w+)\"?\s*\]"
    )
    RULE_FIELDS_REGEX = re.compile(
        r"XDM\.[\w\.]+(?=\s*?=\s*?\"?\w+)", flags=re.IGNORECASE
    )
    RULE_FILTER_REGEX = re.compile(
        r"^\s*filter\s*(?P<condition>(?!.*(\||alter)).+$(\s*(^\s*(?!\||alter).+$))*)",
        flags=re.M,
    )
    TIME_FIELD = "_time"

    def __init__(self, rule_text: str):
        self.rule_text = rule_text
        self._dataset = ""
        self._vendor = ""
        self._product = ""
        self._datamodel = ""
        self._fields: List[str] = []
        self._filter_condition = ""

    @property
    def dataset(self) -> str:
        if not self._dataset:
            match = (
                re.match(self.RULE_HEADER_REGEX, self.rule_text)
                or re.match(self.RULE_HEADER_REGEX_REVERSED, self.rule_text)
                or re.match(self.RULE_HEADER_NEW_REGEX, self.rule_text)
            )
            if match:
                self.dataset = match.groupdict().get("dataset", "")
                if not self._dataset:
                    raise ValueError(
                        f'could not parse the dataset from the rule text: "{self.rule_text}"'
                    )
                if not self._datamodel:
                    dm = match.groupdict().get("datamodel")
                    if dm:
                        self.datamodel = dm
        return self._dataset

    @dataset.setter
    def dataset(self, value):
        self._dataset = value

    @property
    def datamodel(self) -> str:
        if not self._datamodel:
            match = re.match(self.RULE_HEADER_REGEX, self.rule_text) or re.match(
                self.RULE_HEADER_REGEX_REVERSED, self.rule_text
            )
            if match:
                self.datamodel = match.groupdict().get("datamodel", "")
                if not self._datamodel:
                    raise ValueError(
                        f'could not parse the datamodel from the rule text: "{self.rule_text}"'
                    )
                if not self._dataset:
                    ds = match.groupdict().get("dataset")
                    if ds:
                        self.dataset = ds
        return self._datamodel

    @datamodel.setter
    def datamodel(self, value):
        self._datamodel = value

    @property
    def fields(self) -> List[str]:
        if not self._fields:
            uniq_fields = list(set(re.findall(self.RULE_FIELDS_REGEX, self.rule_text)))
            if not uniq_fields:
                raise ValueError(
                    f'could not parse datamodel fields from the rule text: "{self.rule_text}"'
                )

            uniq_fields.append(self.TIME_FIELD)  # The '_time' field is always required.
            self.fields = sorted(uniq_fields)

        return self._fields

    @fields.setter
    def fields(self, value):
        self._fields = value

    @property
    def vendor(self):
        if not self._vendor:
            try:
                self.vendor = self.dataset.split("_")[0]
            except ValueError:
                pass
        return self._vendor

    @vendor.setter
    def vendor(self, value):
        self._vendor = value

    @property
    def product(self):
        if not self._product:
            try:
                splitted_dataset = self.dataset.split("_")[1:]
                splitted_dataset.remove("raw")
                self.product = "_".join(splitted_dataset)
            except ValueError:
                pass
        return self._product

    @product.setter
    def product(self, value):
        self._product = value

    @property
    def filter_condition(self):
        if not self._filter_condition:
            match = re.match(self.RULE_FILTER_REGEX, self.rule_text)
            if match:
                self.filter_condition = match.groupdict().get("condition", "")
        return self._filter_condition

    @filter_condition.setter
    def filter_condition(self, value):
        self._filter_condition = value

    def __repr__(self) -> str:
        return pformat(
            {
                "datamodel": self.datamodel,
                "dataset": self.dataset,
                "fields": self.fields,
                "filter_condition": self.filter_condition,
                "rule_text": self.rule_text,
            }
        )


class ModelingRule(YAMLContentUnifiedObject):
    """Object model representing a modeling rule content entity.

    Abstraction of a modeling rule content entity. Includes functions to return information about the
    rule itself as well as the concrete rule(s) that are defined in the rule.

    Attributes:
        rules (List[SingleModelingRule]): A list of the rules that are defined as part of the Modeling Rule
            content entity. Note that for the new xdm model syntax (>= version 1.3), there should only be one rule per
            Modeling Rule content entity.
    """

    MODEL_REGEX = re.compile(
        r"(?P<model_header>\[MODEL:.*?\])(\s*(^\s*?(?!\s*\[MODEL:.*?\])(?!\s*\[RULE:.*?\]).*?$))+",
        flags=re.M,
    )
    RULE_REGEX = re.compile(
        r"(?P<rule_header>\[RULE:\s*(?P<rule_name>.*?)\])(\s*(^\s*?(?!\s*\[MODEL:.*?\])(?!\s*\[RULE:.*?\]).*?$))+",
        flags=re.M,
    )
    CALL_RULE_REGEX = re.compile(
        r"call\s+(?P<rule_name>\w+)",
        flags=re.IGNORECASE,
    )
    TESTDATA_FILE_SUFFIX = "_testdata.json"
    SCHEMA_FILE_SUFFIX = "_schema.json"

    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.MODELING_RULE, MODELING_RULE)
        self._rules: List[SingleModelingRule] = []
        self.rules_dict: dict = {}

    def __repr__(self) -> str:
        path_name = Path(self.path).name
        return f"{path_name} ({self.from_version}->{self.to_version})"

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, MODELING_RULE)

    def upload(self, client: demisto_client.demisto_api.DefaultApi):
        """
        Upload the modeling_rule to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_modeling_rules(file=self.path)
        pass

    def get_nested_rules(self, modal_text: str) -> str:
        """
        Returns the model with the rules text instead of rule call
            Original modeling rule file text:
                rule_a: "some text..."
                modal_a: "call <rule_a>"

        Args:
            modal_text: The original model text with the rule call's.
                Gets:
                    modal_a: "call <rule_a>"

        Returns:
            The result of the model text with the rule text embedded.
                Returns:
                    modal_a: "some text..."
        """
        if rule_name_match := self.CALL_RULE_REGEX.search(modal_text):
            rule_name = rule_name_match.groupdict().get("rule_name")
            return self.get_nested_rules(
                modal_text.replace(
                    f"call {rule_name}", self.rules_dict.get(rule_name, "")
                )
            )
        else:
            return modal_text

    @property
    def rules(self):
        if not self._rules:
            _rules: List[SingleModelingRule] = []
            rule_initialization_errs = []
            try:
                if self.rules_path:
                    rules_text = self.rules_path.read_text()
                else:
                    rules_text = self.get("rules", "")

                for rule in self.RULE_REGEX.finditer(rules_text):
                    self.rules_dict[rule.groupdict().get("rule_name")] = rule.group()
                matches = self.MODEL_REGEX.finditer(rules_text)
                _rules.extend(
                    SingleModelingRule(self.get_nested_rules(match.group()))
                    for match in matches
                )
                self.rules = _rules
            except ValueError as ve:
                rule_initialization_errs.append(ve)
            if rule_initialization_errs:
                err_msg = f"Failed to initialize ModelingRule with the following errors: {rule_initialization_errs}"
                raise exc.ContentInitializeError(self, self.path, err_msg)
        return self._rules

    @rules.setter
    def rules(self, value):
        self._rules = value

    def get_path_by_file_suffix(self, file_path: str) -> Optional[Path]:
        patterns = [f"*{file_path}"]
        return next(self.path.parent.glob(patterns=patterns, flags=IGNORECASE), None)  # type: ignore

    @property
    def testdata_path(self) -> Optional[Path]:
        """Modeling rule related testdata file path.

        Returns:
            Testdata file path or None if testdata file is not found.
        """
        return self.get_path_by_file_suffix(self.TESTDATA_FILE_SUFFIX)

    @property
    def schema_path(self) -> Optional[Path]:
        return self.get_path_by_file_suffix(self.SCHEMA_FILE_SUFFIX)

    def type(self):
        return FileType.MODELING_RULE

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        # after XSIAM 1.2 is obsolete, we can clear this block and only export the file with the `external-` prefix.
        # Issue: CIAC-4349

        created_files: List[Path] = []
        created_files.extend(super().dump(dest_dir=dest_dir))
        new_file_path = created_files[0]

        if Version(self.get("fromversion", "0.0.0")) >= Version("6.10.0"):
            # export XSIAM 1.3 items only with the external prefix
            if not new_file_path.name.startswith("external-"):
                move_to_path = new_file_path.parent / self.normalize_file_name()
                shutil.move(new_file_path.as_posix(), move_to_path)
                created_files.remove(new_file_path)
                created_files.append(move_to_path)

        elif Version(self.get("toversion", "99.99.99")) < Version("6.10.0"):
            # export XSIAM 1.2 items only without the external prefix
            if new_file_path.name.startswith("external-"):
                move_to_path = Path(str(new_file_path).replace("external-", ""))
                shutil.move(new_file_path.as_posix(), move_to_path)
                created_files.remove(new_file_path)
                created_files.append(move_to_path)

        else:
            # export 2 versions of the file, with/without the external prefix.
            if new_file_path.name.startswith("external-"):
                copy_to_path = str(new_file_path).replace("external-", "")
            else:
                copy_to_path = f"{new_file_path.parent}/{self.normalize_file_name()}"

            shutil.copyfile(new_file_path.as_posix(), copy_to_path)

        return created_files
