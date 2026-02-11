# Detach

Detach content items from Cortex XSOAR/XSIAM.

## Usage

`demisto-sdk detach [OPTIONS]`

## Description

This command allows you to detach content items (Incident Types, Layouts, Playbooks, Scripts) in a Cortex XSOAR/XSIAM instance. Detaching an item allows you to modify it locally on the instance without it being overwritten by updates from the original pack.

## Options

| **Short Flag** | **Long Flag** | **Description** |
| --- | --- | --- |
| -i | --input | The ID of the content item to detach. Can be used multiple times. |
| -it | --item-type | The type of the content items to detach. Possible values: `IncidentTypes`, `Layouts`, `Playbooks`, `Scripts`. |
| | --insecure | Skip certificate validation. |
| | --console-log-threshold | Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR. |
| | --file-log-threshold | Minimum logging threshold for file output. |
| | --log-file-path | Path to save log files. |

## Examples

### Detach specific items

Detach a playbook and a script by their IDs:

```bash
demisto-sdk detach -i "MyPlaybook" -it Playbooks
demisto-sdk detach -i "MyScript" -it Scripts
```

### Detach multiple items of the same type

```bash
demisto-sdk detach -i "Account Enrichment - Generic v2.1" -i "Autofocus - File Indicators Hunting" -it Playbooks
```
