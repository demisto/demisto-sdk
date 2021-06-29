DEFAULT_VERSION = -1
NEW_FILE_DEFAULT_5_FROMVERSION = '5.0.0'
NEW_FILE_DEFAULT_5_5_0_FROMVERSION = '5.5.0'
OLD_FILE_DEFAULT_1_FROMVERSION = '4.1.0'
TO_VERSION_5_9_9 = '5.9.9'
VERSION_6_0_0 = '6.0.0'
SCHEMAS_PATH = "schemas"
SUCCESS_RETURN_CODE = 0
ERROR_RETURN_CODE = 1
SKIP_RETURN_CODE = 2
SKIP_VALIDATE_PY_RETURN_CODE = 3

ARGUMENTS_DEFAULT_VALUES = {
    'content': (True, ['IncidentFieldJSONFormat', 'IndicatorFieldJSONFormat']),
    'system': (
        False,
        ['IncidentFieldJSONFormat', 'IncidentTypesJSONFormat', 'IndicatorFieldJSONFormat', 'IndicatorTypeJSONFormat']),
    'required': (False, ['IncidentFieldJSONFormat', 'IndicatorFieldJSONFormat']),
}
