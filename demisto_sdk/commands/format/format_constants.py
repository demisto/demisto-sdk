from demisto_sdk.commands.common.constants import (
    GENERIC_OBJECTS_OLDEST_SUPPORTED_VERSION, FileType)

DEFAULT_VERSION = -1
NEW_FILE_DEFAULT_5_FROMVERSION = '5.0.0'
NEW_FILE_DEFAULT_5_5_0_FROMVERSION = '5.5.0'
OLD_FILE_DEFAULT_1_FROMVERSION = '4.1.0'
GENERIC_OBJECTS_DEFAULT_FROMVERSION = GENERIC_OBJECTS_OLDEST_SUPPORTED_VERSION
TO_VERSION_5_9_9 = '5.9.9'
VERSION_6_0_0 = '6.0.0'
SCHEMAS_PATH = "schemas"
SUCCESS_RETURN_CODE = 0
ERROR_RETURN_CODE = 1
SKIP_RETURN_CODE = 2
SKIP_VALIDATE_PY_RETURN_CODE = 3
GENERIC_FIELD_DEFAULT_GROUP = 4
GENERIC_FIELD_DEFAULT_ID_PREFIX = 'generic_'

ARGUMENTS_DEFAULT_VALUES = {
    'content': (True, ['IncidentFieldJSONFormat', 'IndicatorFieldJSONFormat', 'GenericFieldJSONFormat']),
    'system': (False, ['IncidentFieldJSONFormat', 'IncidentTypesJSONFormat', 'IndicatorFieldJSONFormat',
                       'IndicatorTypeJSONFormat', 'GenericFieldJSONFormat', 'GenericTypeJSONFormat',
                       'GenericTypeJSONFormat', 'GenericDefinitionJSONFormat']),
    'required': (False, ['IncidentFieldJSONFormat', 'IndicatorFieldJSONFormat', 'GenericFieldJSONFormat']),
}
GENERIC_OBJECTS_FILE_TYPES = [FileType.GENERIC_FIELD, FileType.GENERIC_TYPE,
                              FileType.GENERIC_MODULE, FileType.GENERIC_DEFINITION]
