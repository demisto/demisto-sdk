DEFAULT_MODELING_RULES_STRING = """
[MODEL: dataset=hello_world_raw]
alter
    xdm.event.id = to_string(id),
    xdm.event.description = description,
    xdm.source.user.identifier = json_extract_scalar(custom_details, "$.triggered_by_uuid"),
    xdm.target.port = t_port,
    xdm.network.protocol_layers = arraycreate(protocol);
"""

DEFAULT_MODELING_RULES_SCHEMA_STRING = """
{
    "hello_world_raw": {
        "id": {
            "type": "int",
            "is_array": false
        },
        "t_port": {
            "type": "int",
            "is_array": false
        },
        "protocol": {
            "type": "string",
            "is_array": false
        },
        "description": {
            "type": "string",
            "is_array": false
        },
        "custom_details": {
            "type": "string",
            "is_array": false
        }
    }
}
"""

DEFAULT_TEST_DATA_STRING = """
{
    "data": [
        {
            "test_data_event_id": "7e8ddd41-ed64-4dd0-ae2a-8516c2bf1cd1",
            "vendor": "hello",
            "product": "world",
            "dataset": "hello_world_raw",
            "tenant_timezone": "UTC",
            "event_data": {
                "id": 1,
                "description": "This is test description 1",
                "alert_status": "Pending",
                "t_port": 22,
                "protocol": "UDP",
                "custom_details": {
                    "triggered_by_name": "Name for id: 1",
                    "triggered_by_uuid": "uuid",
                    "type": "customType",
                    "requested_limit": 5,
                    "requested_From_date": "2022-12-21T03:42:05Z"
                }
            },
            "expected_values": {
                "xdm.event.id": "1",
                "xdm.source.user.identifier": "uuid",
                "xdm.event.description": "This is test description 1",
                "xdm.network.protocol_layers": ["UDP"],
                "xdm.target.port": 22
            }
        }
    ],
    "ignored_validations": []
}
"""
