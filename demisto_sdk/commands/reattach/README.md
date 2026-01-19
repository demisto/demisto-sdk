# Reattach

Reattach content items to Cortex XSOAR/XSIAM.

## Usage

`demisto-sdk reattach [OPTIONS]`

## Description

This command allows you to reattach content items (Incident Types, Layouts, Playbooks, Automations) that were previously detached in a Cortex XSOAR/XSIAM instance.

## Options

| **Short Flag** | **Long Flag** | **Description** |
| --- | --- | --- |
| -i | --input | The ID of the content item to reattach. Can be used multiple times. |
| -it | --item-type | The type of the content items to reattach. Required when using `--input`. Possible values: `IncidentTypes`, `Layouts`, `Playbooks`, `Scripts`. |
| -a | --all | Reattach all detached items for all content types in the XSOAR instance. Cannot be used with `--input`. |
| | --insecure | Skip certificate validation. |
| | --console-log-threshold | Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR. |
| | --file-log-threshold | Minimum logging threshold for file output. |
| | --log-file-path | Path to save log files. |

## Examples

### Reattach specific items

Reattach a playbook and an automation by their IDs:

```bash
demisto-sdk reattach -i "MyPlaybook" -it Playbooks
demisto-sdk reattach -i "MyAutomation" -it Scripts
```

### Reattach multiple items

```sh
demisto-sdk reattach -i Access -i Authentication -i "Policy Violation" --item-type IncidentTypes
```

### Reattach all items

Reattach all detached items in the instance:

```bash
demisto-sdk reattach --all
```
