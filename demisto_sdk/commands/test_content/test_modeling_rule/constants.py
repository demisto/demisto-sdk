from datetime import datetime

EXPECTED_SCHEMA_MAPPINGS = {
    str: {"type": "string", "is_array": False},
    dict: {"type": "string", "is_array": False},
    list: {"type": "string", "is_array": False},
    int: {"type": "int", "is_array": False},
    float: {"type": "float", "is_array": False},
    datetime: {"type": "datetime", "is_array": False},
    bool: {"type": "boolean", "is_array": False},
}
SYNTAX_ERROR_IN_MODELING_RULE = (
    "No results were returned by the query - it's possible there is a syntax error with your "
    "modeling rule and that it did not install properly on the tenant"
)
FAILURE_TO_PUSH_EXPLANATION = (
    "Failed pushing test data to tenant, potential reasons could be:\n - an incorrect token\n - "
    'currently only http collectors configured with "Compression" as "gzip" and "Log Format" as'
    ' "JSON" are supported, double check your collector is configured as such\n - the configured '
    "http collector on your tenant is disabled"
)
XQL_QUERY_ERROR_EXPLANATION = (
    "Error executing XQL query, potential reasons could be:\n - mismatch between "
    "dataset/vendor/product marked in the test data from what is in the modeling rule\n"
    " - dataset was not created in the tenant\n - model fields in the query are invalid\n"
    "Try manually querying your tenant to discover the exact problem."
)
TIME_ZONE_WARNING = "Could not find timezone"
NOT_AVAILABLE = "N/A"
