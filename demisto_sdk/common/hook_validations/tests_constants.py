INVALID_PLAYBOOK_PATH = "./tests/test_files/Playbooks.playbook-invalid.yml"
VALID_TEST_PLAYBOOK_PATH = "./tests/test_files/Playbooks.playbook-test.yml"
VALID_INTEGRATION_TEST_PATH = "./tests/test_files/integration-test.yml"
VALID_INTEGRATION_ID_PATH = "./tests/test_files/integration-valid-id-test.yml"
INVALID_INTEGRATION_ID_PATH = "./tests/test_files/integration-invalid-id-test.yml"
VALID_PLAYBOOK_ID_PATH = "./tests/test_files/playbook-valid-id-test.yml"
INVALID_PLAYBOOK_ID_PATH = "./tests/test_files/playbook-invalid-id-test.yml"
VALID_REPUTATION_PATH = "./tests/test_files/reputations-valid.json"
INVALID_REPUTATION_PATH = "./tests/test_files/reputations-invalid.json"
VALID_LAYOUT_PATH = "./tests/test_files/layout-valid.json"
INVALID_LAYOUT_PATH = "./tests/test_files/layout-invalid.json"
VALID_WIDGET_PATH = "./tests/test_files/widget-valid.json"
INVALID_WIDGET_PATH = "./tests/test_files/widget-invalid.json"
VALID_DASHBOARD_PATH = "./tests/test_files/dashboard-valid.json"
INVALID_DASHBOARD_PATH = "./tests/test_files/dashboard-invalid.json"
VALID_INCIDENT_FIELD_PATH = "./tests/test_files/incidentfield-valid.json"
INVALID_INCIDENT_FIELD_PATH = "./tests/test_files/incidentfield-invalid.json"
INVALID_WIDGET_VERSION_PATH = "./tests/test_files/widget-invalid-version.json"
VALID_SCRIPT_PATH = "./tests/test_files/script-valid.yml"
INVALID_SCRIPT_PATH = "./tests/test_files/script-invalid.yml"
BANG_COMMAND_NAMES = {'file', 'email', 'domain', 'url', 'ip'}
DBOT_SCORES_DICT = {
    'DBotScore.Indicator': 'The indicator that was tested.',
    'DBotScore.Type': 'The indicator type.',
    'DBotScore.Vendor': 'The vendor used to calculate the score.',
    'DBotScore.Score': 'The actual score.'
}

IOC_OUTPUTS_DICT = {
    'domain': {'Domain.Name'},
    'file': {'File.MD5', 'File.SHA1', 'File.SHA256'},
    'ip': {'IP.Address'},
    'url': {'URL.Data'}
}
