Set a value in context under the key you entered.

## Script Data
---

| **Name** | **Description** |
| --- | --- |
| Script Type | javascript |
| Tags | Utility |
| Cortex XSOAR Version | 5.0.0 |

## Inputs
---

| **Argument Name** | **Description** |
| --- | --- |
| key | The key to set. Can be a full path such as "Key.ID". If using append=true can also use a DT selector such as "Data\(val.ID == obj.ID\)". |
| value | The value to set to the key. Can be an array. |
| append | If false then the context key will be overwritten. If set to true then the script will append to existing context key. |
| stringify | Whether the argument should be saved as a string. |

## Outputs
---
There are no outputs for this script.


## Script Examples
### Example command
```!Set key=k1 value=v1```
### Context Example
```json
{
    "key": "k1",
    "value": "v1"
}
```

### Human Readable Output

>key | value
>--- | ---
>k1 | v1

### Example command
```!Set key=k2 value=v2 append=true```
### Context Example
```json
{
    "key": "k2",
    "value": "v2",
    "append": "true"
}
```

### Human Readable Output

>key | value | append
>--- | --- | ---
>k2 | v2 | true
