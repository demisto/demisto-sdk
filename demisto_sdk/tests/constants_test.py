import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.git_tools import git_path

GIT_ROOT = "{}".format(git_path())
INVALID_PLAYBOOK_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/Playbooks.playbook-invalid.yml"
VALID_TEST_PLAYBOOK_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/Playbooks.playbook-test.yml"
VALID_BETA_PLAYBOOK_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/beta-playbook-valid.yml"
VALID_PLAYBOOK_ARCSIGHT_ADD_DOMAIN_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/Playbooks." \
                                          f"playbook-ArcSight_Add_Domain_Indicators.yml"
INVALID_INTEGRATION_NO_TESTS = f'{GIT_ROOT}/demisto_sdk/tests/test_files/non-valid-integration-no-test-playbooks.yml'
INVALID_INTEGRATION_NON_CONFIGURED_TESTS = f'{GIT_ROOT}/demisto_sdk/tests/test_files/' \
                                           f'non-valid-integration-test-not-configured.yml'
TEST_PLAYBOOK = f'{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-TestPlaybooks.yml'

VALID_PYTHON_INTEGRATION_TEST_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration_test.py"
VALID_PYTHON_INTEGRATION_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test.py"
VALID_METADATA1_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/1.pack_metadata.json'
VALID_METADATA2_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/2.pack_metadata.json'
VALID_DESCRIPTION_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test_description.md'
VALID_README_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test_README.md'
VALID_IMAGE_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test_image.png'
NOT_VALID_IMAGE_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/default.png'
VALID_PIPEFILE_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/Pipfile'
VALID_PIPEFILE_LOCK_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/Pipfile.lock'
VALID_PACK_IGNORE_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/.pack-ignore'
VALID_SECRETS_IGNORE_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/.secrets-ignore'
VALID_CLASSIFIER_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/classifier.json'
VALID_JSON_FILE_FOR_UNIT_TESTING = f'{GIT_ROOT}/demisto_sdk/tests/test_files/fake_pack/Integrations/' \
                                   f'test_data/results.json'

VALID_INTEGRATION_TEST_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test.yml"
INVALID_INTEGRATION_WITH_NO_TEST_PLAYBOOK = 'demisto_sdk/tests/test_files/integration-test-with-no-test-playbook.yml'
VALID_INTEGRATION_ID_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-valid-id-test.yml"
INVALID_INTEGRATION_ID_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-id-test.yml"
VALID_BETA_INTEGRATION_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-test-beta.yml"
INVALID_PLAYBOOK_PATH_FROM_ROOT = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-disconnected_from_root.yml"
VALID_PLAYBOOK_ID_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-valid-id-test.yml"
INVALID_PLAYBOOK_ID_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-invalid-id-test.yml"
INVALID_PLAYBOOK_CONDITION_1 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-Invalid_condition_unhandled_" \
                               f"branch.yml"
INVALID_IGNORED_UNIFIED_INTEGRATION = f'{GIT_ROOT}/demisto_sdk/tests/test_files/integration_ignored_invalid_unified.yml'
IGNORED_PNG = f'{GIT_ROOT}/demisto_sdk/tests/test_files/docs_test/closing_params.png'
SCRIPT_WITH_PLAYBOOK = 'demisto_sdk/tests/test_files/script-with-test-playbook.yml'
INVALID_PLAYBOOK_CONDITION_2 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-Invalid_condition_unhandled_" \
                               f"branch_and_unhandled_condition.yml"
VALID_PLAYBOOK_CONDITION = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-valid_condition.yml"
VALID_REPUTATION_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/reputations-valid.json"
INVALID_REPUTATION_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/reputations-invalid.json"
VALID_LAYOUT_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/layout-valid.json"
INVALID_LAYOUT_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/layout-invalid.json"
VALID_LAYOUT_CONTAINER_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/layoutscontainer_valid.json"
INVALID_LAYOUT_CONTAINER_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/layoutscontainer_invalid.json"
VALID_INCIDENT_TYPE_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/incidenttype-valid.json"
VALID_WIDGET_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/widget-valid.json"
INVALID_WIDGET_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/widget-invalid.json"
VALID_DASHBOARD_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/dashboard-valid.json"
INVALID_DASHBOARD_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/dashboard-invalid.json"
VALID_INCIDENT_FIELD_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/incidentfield-valid.json"
INVALID_INCIDENT_FIELD_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/incidentfield-invalid.json"
VALID_INDICATOR_FIELD_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/indicatorfield-valid.json"
INVALID_WIDGET_VERSION_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/widget-invalid-version.json"
VALID_SCRIPT_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/script-valid.yml"
INVALID_SCRIPT_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/script-invalid.yml"
VALID_ONE_LINE_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid-one-line_CHANGELOG.md"
VALID_ONE_LINE_LIST_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid-one-line-list_CHANGELOG.md"
VALID_MULTI_LINE_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid-multi-line_CHANGELOG.md"
VALID_MULTI_LINE_LIST_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid-multi-line-list_CHANGELOG.md"
INVALID_ONE_LINE_1_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-one-line_1_CHANGELOG.md"
INVALID_ONE_LINE_2_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-one-line_2_CHANGELOG.md"
INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-one-line-list_1_CHANGELOG.md"
INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-one-line-list_2_CHANGELOG.md"
INVALID_MULTI_LINE_1_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-multi-line_1_CHANGELOG.md"
INVALID_MULTI_LINE_2_CHANGELOG_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid-multi-line_2_CHANGELOG.md"
PACK_TARGET = "Packs/TestPack"
LAYOUT_TARGET = f"{PACK_TARGET}/Layouts/layout-mock.json"
LAYOUTS_CONTAINER_TARGET = f"{PACK_TARGET}/Layouts/layoutscontainer-mock.json"
INDICATOR_TYPE_TARGET = f"{PACK_TARGET}/IndicatorTypes/reputations-valid.json"
WIDGET_TARGET = f"{PACK_TARGET}/Widgets/widget-mocks.json"
DASHBOARD_TARGET = f"{PACK_TARGET}/Dashboards/dashboard-mocks.json"
PLAYBOOK_TARGET = f"{PACK_TARGET}/Playbooks/playbook-test.yml"
INTEGRATION_TARGET = f"{PACK_TARGET}/Integrations/integration-test.yml"
INCIDENT_FIELD_TARGET = f"{PACK_TARGET}/IncidentFields/incidentfield-test.json"
INCIDENT_TYPE_TARGET = f"{PACK_TARGET}/IncidentTypes/incidenttype-valid.json"
PLAYBOOK_PACK_TARGET = "Packs/Int/Playbooks/playbook-test.yml"
INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION = f'{GIT_ROOT}/demisto_sdk/tests/test_files/content_repo_example/Packs/' \
                                            f'FeedAzure/TestPlaybooks/playbook-FeedAzure_test_copy_no_prefix.yml'
INVALID_PLAYBOOK_UNHANDLED_CONDITION = f'{GIT_ROOT}/demisto_sdk/tests/test_files/content_repo_example/Packs/' \
                                       f'FeedAzure/Playbooks/FeedAzure_test.yml'
SCRIPT_TARGET = f"{PACK_TARGET}/Scripts/script-test.yml"
SCRIPT_RELEASE_NOTES_TARGET = f"{PACK_TARGET}/Scripts/script-test_CHANGELOG.md"
INTEGRATION_RELEASE_NOTES_TARGET = f"{PACK_TARGET}/Integrations/integration-test_CHANGELOG.md"
SOURCE_FORMAT_INTEGRATION_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_New_Integration_copy.yml"
DESTINATION_FORMAT_INTEGRATION_COPY = "new_format_New_Integration_copy.yml"
SOURCE_FORMAT_SCRIPT_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_New_script_copy.yml"
DESTINATION_FORMAT_SCRIPT_COPY = "new_format_New_script_copy.yml"
SOURCE_FORMAT_PLAYBOOK_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_new_playbook_copy.yml"
DESTINATION_FORMAT_PLAYBOOK_COPY = "playbook-new_format_new_playbook_copy.yml"
INTEGRATION_WITH_TEST_PLAYBOOKS = f'{GIT_ROOT}/demisto_sdk/tests/test_files/format_Integration_with_test_playbooks.yml'
PLAYBOOK_WITH_TEST_PLAYBOOKS = f'{GIT_ROOT}/demisto_sdk/tests/test_files/format_playbook_with_test_playbooks.yml'
SCRIPT_WITH_TEST_PLAYBOOKS = f'{GIT_ROOT}/demisto_sdk/tests/test_files/format_script_with_test_playbooks.yml'
INDICATORFIELD_EXTRA_FIELDS = f"{GIT_ROOT}/demisto_sdk/tests/test_files/indicatorfield-extra-fields.json"
INDICATORFIELD_EXACT_SCHEME = f"{GIT_ROOT}/demisto_sdk/tests/test_files/indicator-field-exact-scheme.json"
INDICATORFIELD_MISSING_FIELD = f"{GIT_ROOT}/demisto_sdk/tests/test_files/indicator-field-missing-field.json"
INDICATORFIELD_MISSING_AND_EXTRA_FIELDS = f"{GIT_ROOT}/demisto_sdk/tests/test_files/" \
                                          f"indicatorfield-missing-and-extra-fields.json"
INVALID_INTEGRATION_YML_1 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-yml1.yml"
INVALID_INTEGRATION_YML_2 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-yml2.yml"
INVALID_INTEGRATION_YML_3 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-yml3.yml"
INVALID_INTEGRATION_YML_4 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-yml4.yml"
VALID_REPUTATION_FILE = f"{GIT_ROOT}/demisto_sdk/tests/test_files/reputation-cidr-valid.json"
INVALID_REPUTATION_FILE = f"{GIT_ROOT}/demisto_sdk/tests/test_files/reputation-cidr-invalid.json"
EQUAL_VAL_FORMAT_PLAYBOOK_SOURCE = f"{GIT_ROOT}/demisto_sdk/tests/test_files/playbook-invalid-equal.yml"
EQUAL_VAL_FORMAT_PLAYBOOK_DESTINATION = "Playbooks/playbook-invalid-equal.yml"
EQUAL_VAL_PATH = 'Playbooks'
INVALID_NO_HIDDEN_PARAMS = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-invalid-no-hidden-params.yml"
VALID_NO_HIDDEN_PARAMS = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-valid-no-unallowed-hidden-params.yml"
GIT_HAVE_MODIFIED_AND_NEW_FILES = f"{GIT_ROOT}/demisto_sdk/tests/test_files/git_have_modified_and_new_files.json"
SOURCE_FORMAT_INCIDENTFIELD_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_incidentfield-copy.json"
DESTINATION_FORMAT_INCIDENTFIELD_COPY = "IncidentFields/incidentfield-copy.json"
INCIDENTFIELD_PATH = "IncidentFields"
SOURCE_FORMAT_INCIDENTTYPE_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_incidenttype-copy.json"
DESTINATION_FORMAT_INCIDENTTYPE_COPY = "IncidentTypes/incidenttype-copy.json"
INCIDENTTYPE_PATH = "IncidentTypes"

SOURCE_FORMAT_INDICATORFIELD_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_indicatorfield-copy.json"
DESTINATION_FORMAT_INDICATORFIELD_COPY = "IndicatorFields/incidentfield-copy.json"
INDICATORFIELD_PATH = "IndicatorFields"

SOURCE_FORMAT_INDICATORTYPE_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_indicatortype-copy.json"
DESTINATION_FORMAT_INDICATORTYPE_COPY = "Packs/Base/Misc/reputation-copy.json"
INDICATORTYPE_PATH = "Packs/Base/Misc"

SOURCE_FORMAT_LAYOUT_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_layout-copy.json"
DESTINATION_FORMAT_LAYOUT_COPY = "Layouts/layout-copy.json"
DESTINATION_FORMAT_LAYOUT_INVALID_NAME_COPY = "Layouts/layoutt-copy.json"
LAYOUT_PATH = "Layouts"
LAYOUT_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/layout.yml"

SOURCE_FORMAT_LAYOUTS_CONTAINER = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_layoutscontainer-for-class-test.json"
SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_layoutscontainer-test.json"
DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY = "Layouts/formatted_layoutscontainer-test.json"
LAYOUTS_CONTAINER_PATH = "Layouts"
LAYOUTS_CONTAINER_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/layoutscontainer.yml"

SOURCE_FORMAT_CLASSIFIER_5_9_9 = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_classifier_5_9_9.json"
DESTINATION_FORMAT_CLASSIFIER_5_9_9 = "Classifiers/formatted_classifier_5_9_9.json"
CLASSIFIER_5_9_9_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/classifier_5_9_9.yml"

SOURCE_FORMAT_CLASSIFIER = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_new_classifier.json"
DESTINATION_FORMAT_CLASSIFIER = "Classifiers/formatted_classifier.json"
CLASSIFIER_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/classifier.yml"
CLASSIFIER_PATH = "Classifiers"

SOURCE_FORMAT_MAPPER = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_mapper.json"
DESTINATION_FORMAT_MAPPER = "Classifiers/formatted_mapper.json"
MAPPER_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/mapper.yml"
MAPPER_PATH = "Classifiers"

SOURCE_FORMAT_DASHBOARD_COPY = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_dashboard-copy.json"
DESTINATION_FORMAT_DASHBOARD_COPY = "Dashboards/dashboard-copy.json"
DASHBOARD_PATH = "Dashboards"

SOURCE_FORMAT_WIDGET = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_widget.json"
DESTINATION_FORMAT_WIDGET = "Widgets/formatted-widget.json"
WIDGET_PATH = "Widgets"

SOURCE_FORMAT_REPORT = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_report.json"
DESTINATION_FORMAT_REPORT = "Reports/formatted-Reports.json"
REPORT_PATH = "Reports"

SOURCE_FORMAT_PLAYBOOK = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_playbook.yml"
DESTINATION_FORMAT_PLAYBOOK = "Playbook/playbook.yml"
PLAYBOOK_PATH = "Playbook"

SOURCE_FORMAT_TEST_PLAYBOOK = f"{GIT_ROOT}/demisto_sdk/tests/test_files/format_test_playbook.yml"
DESTINATION_FORMAT_TEST_PLAYBOOK = "TestPlaybook/test-playbook.yml"
TEST_PLAYBOOK_PATH = "TestPlaybook"

VALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-valid.md'
INVALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'

DEFAULT_IMAGE = f'{git_path()}/demisto_sdk/tests/test_files/default_image.png'
VALID_PACK = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Packs/FeedAzure'
VALID_PACK_RELATIVE_PATH = 'Packs/FeedAzure'
VALID_BETA_INTEGRATION = f'{git_path()}/demisto_sdk/tests/test_files/valid-beta-integration.yml'
INVALID_BETA_INTEGRATION = f'{git_path()}/demisto_sdk/tests/test_files/invalid-beta-integration.yml'

INVALID_OUTPUT_PATH = f"{GIT_ROOT}/demisto_sdk/tests/test_files"
CONF_JSON_MOCK_PATH = f'{GIT_ROOT}/demisto_sdk/tests/test_files/conf.json'

SOURCE_FORMAT_INTEGRATION_VALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-fetch-valid.yml"
SOURCE_FORMAT_INTEGRATION_INVALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-fetch-invalid.yml"

FEED_INTEGRATION_VALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-feedvalid.yml"
FEED_INTEGRATION_INVALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/integration-feed-invalid.yml"

XSOAR_LINTER_PY3_VALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid_py3_XSOARLinter.py"
XSOAR_LINTER_PY3_INVALID = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid_py3_XSOARLinter.py"
XSOAR_LINTER_PY3_INVALID_WARNINGS = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid_py3_XSOARLinter_warnings.py"
XSOAR_LINTER_PY3_INVALID_WARNINGS_PARTNER = f"{GIT_ROOT}/demisto_sdk/tests/test_files/invalid_py3_XSOARLinter_warnings_partner.py"

DESTINATION_FORMAT_INTEGRATION = "Integrations/integration.yml"
INTEGRATION_PATH = "Integrations"
CONNECTION_SCHEMA_PATH = f"{GIT_ROOT}/demisto_sdk/commands/common/schemas/canvas-context-connections.yml"
DIR_LIST = [
    f'{PACK_TARGET}/{constants.INTEGRATIONS_DIR}',
    f'{PACK_TARGET}/{constants.SCRIPTS_DIR}',
    f'{PACK_TARGET}/{constants.PLAYBOOKS_DIR}',
    f'{PACK_TARGET}/{constants.REPORTS_DIR}',
    f'{PACK_TARGET}/{constants.DASHBOARDS_DIR}',
    f'{PACK_TARGET}/{constants.WIDGETS_DIR}',
    f'{PACK_TARGET}/{constants.INCIDENT_TYPES_DIR}',
    f'{PACK_TARGET}/{constants.INCIDENT_FIELDS_DIR}',
    f'{PACK_TARGET}/{constants.LAYOUTS_DIR}',
    f'{PACK_TARGET}/{constants.CLASSIFIERS_DIR}',
    f'{PACK_TARGET}/{constants.INDICATOR_TYPES_DIR}',
    f'{PACK_TARGET}/{constants.CONNECTIONS_DIR}',
    f'{PACK_TARGET}/{constants.INDICATOR_FIELDS_DIR}',
    constants.TESTS_DIR
]
