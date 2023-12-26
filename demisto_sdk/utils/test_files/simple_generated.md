## Configure HelloWorld

1. Navigate to **Settings** > **Integrations** > **Servers & Services**.
2. Search for HelloWorld.
3. Click **Add instance** to create and configure a new integration instance.

    | **Parameter** | **Description** | **Required** |
    | --- | --- | --- |
    | Source Reliability | Reliability of the source providing the intelligence data. | False |
    | Server URL (e.g., mock://api.xsoar-example.com) |  | True |

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

### helloworld-alert-note-create

***
Example of creating a new item in the API.

#### Base Command

`helloworld-alert-note-create`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| alert_id | The alert's ID to add the note to. | Required |
| note_text | The comment to add to the note. | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| HelloWorld.alert.id | Number | The ID of the alert. |
| HelloWorld.alert.name | String | The name of the alert. |
| HelloWorld.alert.severity | String | The severity of the alert. |
| HelloWorld.alert.date | Date | The date of the alert occurrence. |
| HelloWorld.alert.status | String | The status of the alert. |
