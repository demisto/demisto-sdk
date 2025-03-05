from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    CONTENT_ENTITIES_DIRS,
    CORRELATION_RULES_DIR,
    DOC_FILES_DIR,
    DOCS_DIRECTORIES,
    INTEGRATIONS_DIR,
    LAYOUTS_DIR,
    PACKS_FOLDER,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    SCRIPTS_DIR,
    TESTS_DIRECTORIES,
    XDRC_TEMPLATE_DIR,
)
from demisto_sdk.scripts.validate_content_path import (
    DEPTH_ONE_FOLDERS,
    DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES,
    DIRS_ALLOWING_SPACE_IN_FILENAMES,
    MODELING_RULES_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
    ZERO_DEPTH_FILES,
    InvalidClassifier,
    InvalidCorrelationRuleFileName,
    InvalidDepthOneFile,
    InvalidDepthOneFolder,
    InvalidDepthZeroFile,
    InvalidImageFileName,
    InvalidIntegrationScriptFileName,
    InvalidIntegrationScriptFileType,
    InvalidLayoutFileName,
    InvalidModelingRuleFileName,
    InvalidSuffix,
    InvalidXDRCTemplatesFileName,
    InvalidXSIAMDashboardFileName,
    InvalidXSIAMParsingRuleFileName,
    InvalidXSIAMReportFileName,
    PathIsFolder,
    PathIsTestData,
    PathIsUnified,
    PathUnderDeprecatedContent,
    SpacesInFileName,
    _validate,
)


@pytest.mark.parametrize(
    "suffix",
    ("json", "yml"),
)
def test_xdrc_template_file_valid(suffix: str):
    folder = "foo"
    _validate(DUMMY_PACK_PATH / XDRC_TEMPLATE_DIR / folder / f"{folder}.{suffix}")


@pytest.mark.parametrize(
    "file, suffix",
    (
        pytest.param("MyXDRCTemplate_test", "json", id="bad name, good suffix - json"),
        pytest.param("MyXDRCTemplate_test", "yml", id="bad name, good suffix - yml"),
        pytest.param("MyXDRCTemplate", "py", id="good name, bad suffix"),
    ),
)
def test_xdrc_template_file_invalid(file: str, suffix: str):
    folder = "MyXDRCTemplate"
    with pytest.raises(InvalidXDRCTemplatesFileName):
        _validate(DUMMY_PACK_PATH / XDRC_TEMPLATE_DIR / folder / f"{file}.{suffix}")


def test_xsiam_report_file_valid():
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    _validate(pack_path / XSIAM_REPORTS_DIR / f"{pack_name}_Report.json")


@pytest.mark.parametrize(
    "file_prefix, suffix",
    (
        pytest.param("wrongPrefix", "json", id="bad name, good suffix"),
        pytest.param("myPack", "py", id="good name, bad suffix"),
        pytest.param("image2", "png", id="bad name, good suffix"),
    ),
)
def test_xsiam_report_file_invalid(file_prefix: str, suffix: str):
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    with pytest.raises(InvalidXSIAMReportFileName):
        _validate(pack_path / XSIAM_REPORTS_DIR / f"{file_prefix}_Report.{suffix}")


@pytest.mark.parametrize("suffix", (".png", ".json"))
def test_xsiam_dashboard_file__valid(suffix: str):
    """
    Given:
            A valid XSIAM dashboard file
    When:
            Running validate_path
    Then:
            Make sure the validation passes
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    _validate(
        (pack_path / XSIAM_DASHBOARDS_DIR / f"{pack_name}_dashboard").with_suffix(
            suffix
        )
    )


@pytest.mark.parametrize(
    "file_prefix, suffix",
    (
        pytest.param("wrongPrefix", "json", id="bad name, good suffix"),
        pytest.param("wrongPrefix", "png", id="bad name, good suffix"),
        pytest.param("myPack", "py", id="good name, bad suffix"),
    ),
)
def test_xsiam_dashboard_file__invalid(file_prefix: str, suffix: str):
    """
    Given:
            An invalid XSIAM dashboard file
            Case 1: wrong prefix - file name does not start with pack name
            Case 2: wrong suffix - file name does not end with .json
    When:
            Running validate_path
    Then:
            Make sure the validation raises InvalidXSIAMDashboardFileName
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    with pytest.raises(InvalidXSIAMDashboardFileName):
        _validate(
            pack_path / XSIAM_DASHBOARDS_DIR / f"{file_prefix}_dashboard.{suffix}"
        )


def test_correlation_rule_file__valid():
    """
    Given:
            A valid XSIAM dashboard file
    When:
            Running validate_path
    Then:
            Make sure the validation passes
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    _validate(pack_path / CORRELATION_RULES_DIR / f"{pack_name}_anything.yml")


@pytest.mark.parametrize(
    "stem, suffix",
    (
        pytest.param("wrongPrefix", "yml", id="bad name, good suffix"),
        pytest.param("myPack", "py", id="good name, bad suffix"),
    ),
)
def test_correlation_rule_file__invalid(stem: str, suffix: str):
    """
    Given:
            An invalid XSIAM correlation rule name
    When:
            Running validate_path
    Then:
            Make sure the validation raises InvalidCorrelationRuleFileName
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    with pytest.raises(InvalidCorrelationRuleFileName):
        _validate(pack_path / CORRELATION_RULES_DIR / f"{stem}.{suffix}")


def test_xsiam_parsing_rule_file__valid():
    """
    Given:
            A valid XSIAM parsing rule file
    When:
            Running validate_path
    Then:
            Make sure the validation passes
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    folder_name = f"{pack_name}_{PARSING_RULES_DIR}"
    _validate(pack_path / PARSING_RULES_DIR / folder_name / f"{folder_name}.yml")


@pytest.mark.parametrize(
    "file_name, suffix",
    (
        pytest.param("wrongName", "json", id="bad name, good suffix"),
        pytest.param("myPack_ParsingRules", "py", id="good name, bad suffix"),
    ),
)
def test_xsiam_parsing_rule_file__invalid(file_name: str, suffix: str):
    """
    Given:
            An invalid XSIAM parsing rule file
            Case 1: wrong name - file name is not identical to the folder name
            Case 2: wrong suffix - file name does not end with .yml or.xif
    When:
            Running validate_path
    Then:
            Make sure the validation raises InvalidXSIAMParsingRuleFileName
    """
    pack_name = "myPack"
    pack_path = Path("content", "Packs", pack_name)
    folder_name = f"{pack_name}_{PARSING_RULES_DIR}"
    with pytest.raises(InvalidXSIAMParsingRuleFileName):
        _validate(pack_path / PARSING_RULES_DIR / folder_name / f"{file_name}.{suffix}")


def test_content_entities_dir_length():
    """
    This test is here so we don't forget to update FOLDERS_ALLOWED_TO_CONTAIN_FILES when adding/removing content types.
    If this test failed, it's likely you modified either CONTENT_ENTITIES_DIRS or FOLDERS_ALLOWED_TO_CONTAIN_FILES.
    Update the test values accordingly.
    """
    assert len(set(DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)) == 35

    # change this one if you added a content item folder that can't have files directly under it
    assert (
        len(
            DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES.intersection(
                CONTENT_ENTITIES_DIRS
            )
        )
        == 27
    )


folders_not_allowed_to_contain_files = (
    set(CONTENT_ENTITIES_DIRS) | DEPTH_ONE_FOLDERS
).difference(DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)

DUMMY_PACK_PATH = Path("content", "Packs", "myPack")


@pytest.mark.parametrize("file_name", ZERO_DEPTH_FILES)
def test_depth_zero_pass(file_name: str):
    """
    Given
            A file name which is allowed directly under the pack
    When
            Running validate_path
    Then
            Make sure the validation passes
    """
    _validate(Path(PACKS_FOLDER, "MyPack", file_name))


@pytest.mark.parametrize("file_name", ("foo.py", "bar.md"))
def test_depth_zero_fail(file_name: str):
    """
    Given
            A file name which is NOT allowed directly under the pack
    When
            Running validate_path
    Then
            Make sure the validation raises InvalidDepthZeroFile
    """
    assert file_name not in ZERO_DEPTH_FILES  # sanity
    with pytest.raises(InvalidDepthZeroFile):
        _validate(Path(PACKS_FOLDER, "MyPack", file_name))


def test_first_level_folder_fail():
    """
    Given
            A name of a folder, which is NOT allowed as a first-level folder
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure the validation raises InvalidDepthOneFolder
    """
    assert (folder_name := "folder_name") not in DEPTH_ONE_FOLDERS
    with pytest.raises(InvalidDepthOneFolder):
        _validate(Path(DUMMY_PACK_PATH, folder_name, "file"))
    with pytest.raises(InvalidDepthOneFolder):
        _validate(Path(DUMMY_PACK_PATH, folder_name, "nested", "very nested", "file"))


@pytest.mark.parametrize("folder", DEPTH_ONE_FOLDERS)
def test_depth_one_pass(folder: str):
    """
    Given
            A name of a folder, which IS allowed as a first-level folder
    When
            Running validate_path on a file created indirectly under it
    Then
            Make sure the validation does not raise InvalidDepthOneFileError
    """
    assert folder in DEPTH_ONE_FOLDERS
    try:
        _validate(Path(DUMMY_PACK_PATH, folder, "nested", "file"))
        _validate(Path(DUMMY_PACK_PATH, folder, "nested", "nested_deeper", "file"))
    except PathIsTestData:
        pass
    except (
        InvalidIntegrationScriptFileType,
        InvalidIntegrationScriptFileName,
        InvalidXDRCTemplatesFileName,
        InvalidModelingRuleFileName,
        InvalidXSIAMParsingRuleFileName,
    ):
        # In Integration/script, InvalidIntegrationScriptFileType will be raised but is irrelevant for this test.
        # InvalidXDRCTemplatesFileName will be raised but it is irrelevant for this test.
        # InvalidModelingRuleFileName will be raised but it is irrelevant for this test.
        pass


@pytest.mark.parametrize("folder", folders_not_allowed_to_contain_files)
def test_depth_one_fail(folder: str):
    """
    Given
            A name of a folder, which may NOT contain files directly
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure InvalidDepthOneFileError is raised
    """
    with pytest.raises(InvalidDepthOneFile):
        _validate(DUMMY_PACK_PATH / folder / "file")


@pytest.mark.parametrize(
    "path",
    (
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.yml"),
            id="Unified script (yml)",
        ),
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.md"),
            id="Unified script (md)",
        ),
        pytest.param(
            Path("Packs/myPack/Integrations/integration-foo.yml"),
            id="Unified integration (yml)",
        ),
        pytest.param(
            Path("Packs/myPack/Integrations/integration-foo.md"),
            id="Unified integration (md)",
        ),
    ),
)
def test_unified_conten(path: Path):
    """
    Given
            A file under a path under UnifiedContent
    When
            Running validate_path on the path
    Then
            Make sure the validation raises PathIsUnified
    """
    with pytest.raises(PathIsUnified):
        _validate(path)


@pytest.mark.parametrize(
    "path",
    (
        "foo",
        "foo/bar",
        "foo/bar.py",
        "Integrations/myIntegration.yml",
        "Integrations/myIntegration/myIntegration.py",
        "Integrations/myIntegration/myIntegration.yml",
    ),
)
def test_deprecatedcontent(path: str):
    with pytest.raises(PathUnderDeprecatedContent):
        _validate(Path("Packs/DeprecatedContent", path))


def test_first_level_folders_subset():
    assert DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES.issubset(DEPTH_ONE_FOLDERS)


def test_dir(repo):
    """
    Given
            A repo
    When
            Calling validate_path on a folder path
    Then
            Make sure it raises the apporpiate exception
    """
    pack = repo.create_pack("myPack")
    integration = pack.create_integration()
    with pytest.raises(PathIsFolder):
        _validate(Path(pack.path))

    with pytest.raises(PathIsFolder):
        _validate(Path(integration.path))


DUMMY_INTEGRATION_NAME = "MyIntegration"
DUMMY_INTEGRATION_PATH = DUMMY_PACK_PATH / INTEGRATIONS_DIR / DUMMY_INTEGRATION_NAME
MALFORMED_DUMMY_INTEGRATION_NAME = DUMMY_INTEGRATION_NAME + "-"


def test_space_invalid():
    with pytest.raises(SpacesInFileName):
        _validate(DUMMY_INTEGRATION_PATH / "foo bar.yml")


@pytest.mark.parametrize("path", DIRS_ALLOWING_SPACE_IN_FILENAMES)
def test_space_valid(path):
    """Make sure files under"""
    _validate(DUMMY_INTEGRATION_PATH / path / "foo bar.yml")


@pytest.mark.parametrize(
    "file_name",
    [
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.yml",
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.png",
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.py",
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.js",
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.ps1",
        f"{MALFORMED_DUMMY_INTEGRATION_NAME}.Tests.ps1",
        f"{DUMMY_INTEGRATION_NAME}_Test.py",
        f"{DUMMY_INTEGRATION_NAME}_tests.py",
        f"{DUMMY_INTEGRATION_NAME.upper()}.py",
        "README",
        "{DUMMY_INTEGRATION_NAME}_description",
    ],
)
def test_integration_script_file_invalid(file_name: str):
    with pytest.raises(InvalidIntegrationScriptFileName):
        _validate(DUMMY_INTEGRATION_PATH / file_name)


@pytest.mark.parametrize(
    "file_name",
    [
        f"{DUMMY_INTEGRATION_NAME}.yml",
        f"{DUMMY_INTEGRATION_NAME}_image.png",
        f"{DUMMY_INTEGRATION_NAME}.py",
        f"{DUMMY_INTEGRATION_NAME}.js",
        f"{DUMMY_INTEGRATION_NAME}.ps1",
        f"{DUMMY_INTEGRATION_NAME}.Tests.ps1",
        f"{DUMMY_INTEGRATION_NAME}_test.py",
        "conftest.py",
        ".vulture_whitelist.py",
        "README.md",
        f"{DUMMY_INTEGRATION_NAME}_description.md",
        "command_examples.txt",
        ".pylintrc",
    ],
)
def test_integration_script_file_valid(file_name: str):
    _validate(DUMMY_INTEGRATION_PATH / file_name)


@pytest.mark.parametrize(
    "file_name",
    (
        "layouts-.json",
        "not-layout-.json",
        "not-layoutscontainer-.json",
        "foo.json",
        "Layout-.json",
        "Layoutscontainer-.json",
        "layout_.json",
        "layout-foo.py",
        "layoutscontainer-foo.py",
    ),
)
def test_layout_invalid(file_name: str):
    with pytest.raises(InvalidLayoutFileName):
        _validate(DUMMY_PACK_PATH / LAYOUTS_DIR / file_name)


@pytest.mark.parametrize(
    "folder",
    (
        LAYOUTS_DIR,
        PLAYBOOKS_DIR,
        f"{INTEGRATIONS_DIR}/myIntegration",
        f"{SCRIPTS_DIR}/myScript",
    ),
)
@pytest.mark.parametrize("suffix", (".yaml", ".json5", ".bar", ".docx"))
def test_invalid_suffix(folder: str, suffix: str):
    with pytest.raises(InvalidSuffix):
        _validate(DUMMY_PACK_PATH / folder / f"foo.{suffix}")


@pytest.mark.parametrize(
    "file_name",
    (
        "layout-foo.json",
        "layoutscontainer-.json",
    ),
)
def test_layout_file_valid(file_name: str):
    _validate(DUMMY_PACK_PATH / LAYOUTS_DIR / file_name)


@pytest.mark.parametrize(
    "file_name",
    (
        "classifier-foo.json",
        "mapper-foo.json",
        "classifier-mapper-foo.json",
    ),
)
def test_classifier_mapper_file_valid(file_name: str):
    _validate(DUMMY_PACK_PATH / CLASSIFIERS_DIR / file_name)


@pytest.mark.parametrize(
    "file_name",
    (
        "not-classifier.json",
        "clasifier.json",
        "Clasifier.json",
        "Mapper.json",
        "maper.json",
        "foo.json",
        "classifier.yml",
        "mapper.md",
    ),
)
def test_classifier_mapper_file_invalid(file_name: str):
    with pytest.raises(InvalidClassifier):
        _validate(DUMMY_PACK_PATH / CLASSIFIERS_DIR / file_name)


@pytest.mark.parametrize(
    "file_name",
    (
        "image_file.png",
        "image.svg",
        "image1.svg",
        "image-1-1.png",
    ),
)
def test_doc_file_valid(file_name: str):
    _validate(DUMMY_PACK_PATH / DOC_FILES_DIR / file_name)


@pytest.mark.parametrize(
    "file_name",
    (
        "Mitre&Attc.png",
        "image(1).png",
        "image_%.svg",
    ),
)
def test_doc_file_invalid(file_name: str):
    with pytest.raises(InvalidImageFileName):
        _validate(DUMMY_PACK_PATH / DOC_FILES_DIR / file_name)


EXOTIC_SUFFIXES = ("xys", "sh", "pem")


@pytest.mark.parametrize("folder", TESTS_DIRECTORIES)
@pytest.mark.parametrize("suffix", EXOTIC_SUFFIXES)
def test_exotic_suffix_test_data(folder: str, suffix: str):
    # should NOT raise InvalidSuffix
    with pytest.raises(PathIsTestData):
        _validate((DUMMY_PACK_PATH / folder / "file").with_suffix(f".{suffix}"))


@pytest.mark.parametrize("folder", DOCS_DIRECTORIES)
@pytest.mark.parametrize("suffix", EXOTIC_SUFFIXES)
def test_exotic_suffix_doc_data(folder: str, suffix: str):
    # should NOT raise InvalidSuffix
    _validate((DUMMY_PACK_PATH / folder / "file").with_suffix(f".{suffix}"))


@pytest.mark.parametrize(
    "file_name",
    [
        "RuleEventCollector_1_2.yml",
        "RuleEventCollector_1_2.xif",
        "RuleEventCollector_1_2_schema.json",
        "RuleEventCollector_1_2_testdata.json",
    ],
)
def test_modeling_rule_file_valid(file_name: str):
    folder = "RuleEventCollector_1_2"
    _validate(DUMMY_PACK_PATH / MODELING_RULES_DIR / folder / file_name)


@pytest.mark.parametrize(
    "file_name",
    [
        "RuleEventCollector_1_3.yml",
        "RuleEventCollector1_1_2.xif",
        "RuleEventColector_1_2_schema.json",
        "RuleEventCollector_1_2.json",  # json without schema
        "RuleEventCollector_1_2_3.yml",
    ],
)
def test_modeling_rule_file_invalid(file_name: str):
    folder = "RuleEventCollector_1_2"
    with pytest.raises(InvalidModelingRuleFileName):
        _validate(DUMMY_PACK_PATH / MODELING_RULES_DIR / folder / file_name)
