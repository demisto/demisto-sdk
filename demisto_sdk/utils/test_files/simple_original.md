## Configure HelloWorld

1. Navigate to **Settings** > **Integrations** > **Servers & Services**.
2. Search for HelloWorld.
3. Click **Add instance** to create and configure a new integration instance.

    | **Parameter** | **Description** | **Required** |
    | --- | --- | --- |
    | Source Reliability | Reliability of the source providing the intelligence data. | False |
    | Server URL (e.g., https://api.xsoar-example.com) |  | True |

## Commands

### helloworld-say-hello

***
Hello command - prints hello to anyone.

#### Base Command

`helloworld-say-hello`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| name | The name of whom you want to say hello to. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| hello | String | Should be Hello \*\*something\*\* here. |

#### Command example
```!helloworld-say-hello name="Hello Dbot"```
#### Context Example
```json
{
    "hello": "Hello Hello Dbot"
}
```

#### Human Readable Output

> Hello Hello Dbot

### helloworld-alert-list

***
Lists the example alerts as it would be fetched from the API.

#### Base Command

`helloworld-alert-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| alert_id | Filter by alert item ID. If not provided, all IDs will be retrieved. | Optional |
| limit | How many alerts to fetch. Default is 10. | Optional |
| severity | The severity  by which to filter the alerts. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| HelloWorld.alert.id | Number | The ID of the alert. |
| HelloWorld.alert.name | String | The name of the alert. |
| HelloWorld.alert.severity | String | The severity of the alert. |
| HelloWorld.alert.date | Date | The date of the alert occurrence. |
| HelloWorld.alert.status | String | The status of the alert. |

#### Command example
```!helloworld-alert-list limit="3" severity="low"```
#### Context Example
```json
{
    "HelloWorld": {
        "Alert": [
            {
                "date": "2023-09-14T11:30:39.882955",
                "id": 1,
                "name": "XSOAR Test Alert #1",
                "severity": "low",
                "status": "Testing"
            },
            {
                "date": "2023-09-14T11:30:39.882955",
                "id": 2,
                "name": "XSOAR Test Alert #2",
                "severity": "low",
                "status": "Testing"
            },
            {
                "date": "2023-09-14T11:30:39.882955",
                "id": 3,
                "name": "XSOAR Test Alert #3",
                "severity": "low",
                "status": "Testing"
            }
        ]
    }
}
```

#### Human Readable Output

> Items List (Sample Data)
>|date|id|name|severity|status|
>|---|---|---|---|---|
>| 2023-09-14T11:30:39.882955 | 1 | XSOAR Test Alert #1 | low | Testing |
>| 2023-09-14T11:30:39.882955 | 2 | XSOAR Test Alert #2 | low | Testing |
>| 2023-09-14T11:30:39.882955 | 3 | XSOAR Test Alert #3 | low | Testing |


#### Command example
```!helloworld-alert-list alert_id=2```
#### Context Example
```json
{
    "HelloWorld": {
        "Alert": {
            "date": "2023-09-14T11:30:39.882955",
            "id": 2,
            "name": "XSOAR Test Alert #2",
            "severity": "low",
            "status": "Testing"
        }
    }
}
```

#### Human Readable Output

> Items List (Sample Data)
>|date|id|name|severity|status|
>|---|---|---|---|---|
>| 2023-09-14T11:30:39.882955 | 2 | XSOAR Test Alert #2 | low | Testing |



>Note was created successfully.
