OLD_CLASSIFIER = {
    "brandName": "test",
    "custom": True,
    "defaultIncidentType": "",
    "id": "test classifier",
    "keyTypeMap": {
        "test": "test1"
    },
    "mapping": {
        "Logz.io Alert": {
            "dontMapEventToLabels": False,
            "internalMapping": {
                "test Alert ID": {
                    "complex": None,
                    "simple": "alertId"
                },
                "details": {
                    "complex": None,
                    "simple": "description"
                }
            }
        }
    },
    "transformer": {
        "complex": None,
        "simple": "test"
    },
    "unclassifiedCases": {},
    "version": -1,
    "fromVersion": "5.0.0",
    "toVersion": "5.9.9"
}

NEW_CLASSIFIER = {
    "defaultIncidentType": "test",
    "id": "testing",
    "type": "classification",
    "name": "test Classifier",
    "description": "Classifies test.",
    "keyTypeMap": {
        "test": "test1"
    },
    "transformer": {
        "complex": None,
        "simple": "test"
    },
    "version": -1,
    "fromVersion": "6.0.0",
    "toVersion": "6.0.5"
}

MAPPER = {
    "defaultIncidentType": "test",
    "id": "test Mapper",
    "type": "mapping-incoming",
    "name": "test Mapper",
    "description": "Mapper test",
    "mapping": {
        "test": {
            "dontMapEventToLabels": False,
            "internalMapping": {
                "test Alert ID": {
                    "complex": None,
                    "simple": "alertId"
                }
            }
        }
    },
    "version": -1,
    "fromVersion": "6.0.0",
    "toVersion": "6.0.5"
}

DASHBOARD = {
    "id": "my-dashboard",
    "version": -1,
    "fromVersion": "5.0.0",
    "description": "",
    "period": {
        "byTo": "",
        "byFrom": "days",
        "toValue": None,
        "fromValue": 7,
        "field": ""
    },
    "fromDateLicense": "0001-01-01T00:00:00Z",
    "name": "my-dashboard",
    "layout": [
        {
            "id": "a0e381e0-1c86-11e8-8581-45a91cd24d8e",
            "forceRange": True,
            "x": 8,
            "y": 0,
            "i": "a0e381e0-1c86-11e8-8581-45a91cd24d8e",
            "w": 4,
            "h": 4,
            "widget": {
                "id": "my-tasks",
                "version": 1,
                "modified": "2018-02-28T14:55:09.423998+02:00",
                "name": "My Tasks",
                "dataType": "tasks",
                "widgetType": "list",
                "query": "assignee:\"{me}\" and (state:Waiting or state:inprogress or state:error)",
                "sort": [
                    {
                        "field": "dueDate",
                        "asc": True
                    }
                ],
                "isPredefined": True,
                "dateRange": {
                    "fromDate": "0001-01-01T00:00:00Z",
                    "toDate": "0001-01-01T00:00:00Z",
                    "period": {
                        "byTo": "",
                        "byFrom": "days",
                        "toValue": None,
                        "fromValue": None,
                        "field": ""
                    },
                    "fromDateLicense": "0001-01-01T00:00:00Z"
                },
                "params": None,
                "size": 10,
                "category": ""
            }
        },
    ],
    "isPredefined": True
}

CONNECTION = {
    "canvasContextConnections": [
        {
            "contextKey1": "MD5",
            "contextKey2": "SHA256",
            "connectionDescription": "Belongs to the same file",
            "parentContextKey": "File"
        },
        {
            "contextKey1": "MD5",
            "contextKey2": "SHA1",
            "connectionDescription": "Belongs to the same file",
            "parentContextKey": "File"
        },
    ]
}

INDICATOR_FIELD = {
    "id": "indicator_field",
    "version": -1,
    "modified": "2020-04-30T12:08:12.502031832Z",
    "fromVersion": "5.5.0",
    "name": "indicator_field",
    "ownerOnly": False,
    "placeholder": "",
    "description": "",
    "cliName": "indicator",
    "type": "singleSelect",
    "closeForm": False,
    "editForm": True,
    "required": False,
    "script": "",
    "fieldCalcScript": "",
    "neverSetAsRequired": False,
    "isReadOnly": False,
    "selectValues": [
        "1",
        "2",
    ],
    "validationRegex": "",
    "useAsKpi": True,
    "locked": False,
    "system": False,
    "content": True,
    "group": 2,
    "hidden": False,
    "associatedTypes": [
        "Employee"
    ],
    "systemAssociatedTypes": None,
    "associatedToAll": False,
    "unmapped": False,
    "unsearchable": False,
    "caseInsensitive": True,
    "columns": None,
    "defaultRows": None,
    "sla": 0,
    "threshold": 72,
    "breachScript": ""
}

INCIDENT_TYPE = {
    "id": "incident_type",
    "version": -1,
    "locked": False,
    "name": "incident_type",
    "prevName": "incident_type",
    "color": "#32d296",
    "playbookId": "my-playbook",
    "hours": 0,
    "days": 0,
    "weeks": 0,
    "hoursR": 0,
    "daysR": 0,
    "weeksR": 0,
    "system": False,
    "readonly": False,
    "default": False,
    "autorun": False,
    "preProcessingScript": "",
    "closureScript": "",
    "disabled": False,
    "reputationCalc": 0,
    "fromVersion": "5.5.0"
}

LAYOUT = {
    "TypeName": "my-layout",
    "kind": "details",
    "fromVersion": "5.0.0",
    "toVersion": "5.9.9",
    "layout": {
        "TypeName": "",
        "id": "my-layout",
        "kind": "details",
        "modified": "2019-09-22T11:09:50.039511463Z",
        "name": "",
        "system": False,
        "tabs": [
            {
                "id": "caseinfoid",
                "name": "Incident Info",
                "sections": [
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "caseinfoid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": "type",
                                "height": 24,
                                "id": "incident-type-field",
                                "index": 0,
                                "startCol": 0
                            },
                        ],
                        "moved": False,
                        "name": "Details",
                        "static": False,
                        "w": 1,
                        "x": 0,
                        "y": 0
                    },
                ],
                "type": "custom",
                "hidden": False
            },
        ],
        "typeId": "some-id",
        "version": -1
    },
    "typeId": "some-id",
    "version": -1
}

LAYOUTS_CONTAINER = {
    "id": "my_layoutscontainer",
    "name": "my_layoutscontainer",
    "group": "incident",
    "description": "description",
    "fromVersion": "6.0.0",
    "detailsV2": {
        "tabs": [
            {
                "id": "caseinfoid",
                "name": "Incident Info",
                "sections": [
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "caseinfoid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": "type",
                                "height": 24,
                                "id": "incident-type-field",
                                "index": 0,
                                "startCol": 0
                            },
                        ],
                        "moved": False,
                        "name": "Details",
                        "static": False,
                        "w": 1,
                        "x": 0,
                        "y": 0
                    },
                ],
                "type": "custom",
                "hidden": False
            },
        ]
    },
    "version": -1
}

REPORT = {
    "id": "report",
    "name": "report",
    "description": "",
    "fromVersion": "5.0.0",
    "tags": [],
    "createdBy": "DBot",
    "type": "pdf",
    "modified": "2018-01-24T15:27:36.431127302Z",
    "startDate": "0001-01-01T00:00:00Z",
    "times": 0,
    "recurrent": False,
    "endingDate": "0001-01-01T00:00:00Z",
    "timezoneOffset": 0,
    "cronView": False,
    "scheduled": False,
    "system": True,
    "locked": False,
    "sections": [
        {
            "layout": {
                "tableColumns": [
                    "name",
                    "occurred",
                    "type",
                    "owner",
                    "severity",
                    "status",
                    "dueDate"
                ],
                "readableHeaders": {
                    "name": "Name",
                    "occurred": "Occurred",
                    "type": "Type",
                    "owner": "Owner",
                    "severity": "Severity",
                    "status": "Status",
                    "dueDate": "Due Date"
                },
                "classes": "striped stackable small very compact",
                "i": "1",
                "rowPos": 6,
                "columnPos": 0,
                "w": 12,
                "h": 2
            },
            "query": {
                "type": "incident",
                "filter": {
                    "query": "-status:Closed and (severity:High or severity:Critical)",
                    "period": {
                        "byFrom": "days",
                        "fromValue": None,
                        "by": "day"
                    },
                    "fromDate": None,
                    "toDate": None
                }
            },
            "type": "table",
            "title": "Critical and High Incidents"
        },
    ],
    "recipients": [],
    "orientation": "portrait",
    "paperSize": "A4",
    "runOnce": None,
    "latestReportName": "",
    "latestReportTime": "0001-01-01T00:00:00Z",
    "latestScheduledReportTime": "0001-01-01T00:00:00Z",
    "nextScheduledTime": "0001-01-01T00:00:00Z",
    "latestReportUsername": "",
    "decoder": {
        "evidences.fetched": {
            "type": "date",
            "value": "02/01/06 3:04:05 PM"
        },

    },
    "reportType": "",
    "sensitive": False,
    "runningUser": "",
    "dashboard": {
        "id": "",
        "version": 0,
        "modified": "0001-01-01T00:00:00Z",
        "fromDate": "0001-01-01T00:00:00Z",
        "toDate": "0001-01-01T00:00:00Z",
        "period": {
            "byTo": "",
            "byFrom": "days",
            "toValue": None,
            "fromValue": None,
            "field": ""
        },
        "fromDateLicense": "0001-01-01T00:00:00Z",
        "name": "Critical and High incidents",
        "layout": [
            {
                "id": "2",
                "forceRange": False,
                "x": 0,
                "y": 0,
                "i": "2",
                "w": 12,
                "h": 1,
                "widget": {
                    "id": "58",
                    "version": 1,
                    "modified": "2018-01-23T16:42:36.157893339Z",
                    "name": "criticalAndHighIncidents Headline",
                    "dataType": "incidents",
                    "widgetType": "text",
                    "query": "-status:Closed and (severity:High or severity:Critical)",
                    "isPredefined": False,
                    "dateRange": {
                        "fromDate": "0001-01-01T00:00:00Z",
                        "toDate": "0001-01-01T00:00:00Z",
                        "period": {
                            "byTo": "",
                            "byFrom": "days",
                            "toValue": None,
                            "fromValue": None,
                            "field": ""
                        },
                        "fromDateLicense": "0001-01-01T00:00:00Z"
                    },
                    "params": {
                        "text": "# **Critical and High incidents**\n\n{date}\n\n---"
                    },
                    "size": 0
                }
            },
        ],
        "isPredefined": False
    }
}

REPUTATION = {
    "id": "reputation",
    "version": -1,
    "fromVersion": "5.5.0",
    "modified": "2019-07-18T08:57:51.058271942Z",
    "sortValues": None,
    "commitMessage": "",
    "shouldPublish": False,
    "shouldCommit": False,
    "regex": "",
    "details": "reputation",
    "prevDetails": "reputation",
    "reputationScriptName": "",
    "reputationCommand": "",
    "enhancementScriptNames": [],
    "system": False,
    "locked": False,
    "disabled": False,
    "file": False,
    "updateAfter": 0,
    "mergeContext": False,
    "formatScript": "",
    "contextPath": "",
    "contextValue": "",
    "excludedBrands": [],
    "expiration": 0,
    "defaultMapping": {},
    "manualMapping": None,
    "fileHashesPriority": None,
    "legacyNames": ["Malware"]
}

WIDGET = {
    "id": "widget",
    "version": -1,
    "fromVersion": "5.0.0",
    "name": "widget",
    "dataType": "incidents",
    "widgetType": "bar",
    "query": "-category:job and -status:archived and -status:closed",
    "isPredefined": True,
    "dateRange": {
        "fromDate": "0001-01-01T00:00:00Z",
        "toDate": "0001-01-01T00:00:00Z",
        "period": {
            "byTo": "",
            "byFrom": "days",
            "toValue": None,
            "fromValue": 7,
            "field": ""
        },
        "fromDateLicense": "0001-01-01T00:00:00Z"
    },
    "params": {
        "groupBy": [
            "owner"
        ]
    },
    "description": ""
}

INCIDENT_FIELD = {
    "associatedToAll": False,
    "associatedTypes": [
        "Me"
    ],
    "breachScript": "",
    "caseInsensitive": True,
    "cliName": "incidentfield",
    "closeForm": False,
    "columns": None,
    "content": True,
    "defaultRows": None,
    "description": "",
    "editForm": True,
    "fieldCalcScript": "",
    "group": 0,
    "hidden": False,
    "id": "incident-field",
    "isReadOnly": False,
    "locked": False,
    "name": "incident-field",
    "neverSetAsRequired": False,
    "ownerOnly": False,
    "placeholder": "",
    "required": False,
    "script": "",
    "selectValues": None,
    "sla": 0,
    "system": False,
    "systemAssociatedTypes": None,
    "threshold": 72,
    "type": "shortText",
    "unmapped": False,
    "unsearchable": False,
    "useAsKpi": False,
    "validationRegex": "",
    "version": -1,
    "fromVersion": "5.0.0"
}

GENERIC_FIELD = {
    "associatedToAll": False,
    "associatedTypes": [
        "Workstation"
    ],
    "caseInsensitive": True,
    "cliName": "operatingsystem",
    "id": "asset_operatingsystem",
    "name": "Operating System",
    "closeForm": False,
    "content": True,
    "editForm": True,
    "group": 0,
    "definitionId": "asset",
    "genericModuleId": "rbvm",
    "hidden": False,
    "isReadOnly": False,
    "locked": False,
    "neverSetAsRequired": False,
    "ownerOnly": False,
    "required": False,
    "sla": 0,
    "system": False,
    "threshold": 72,
    "type": "shortText",
    "unmapped": False,
    "unsearchable": False,
    "useAsKpi": False,
    "version": -1,
    "fromVersion": "6.5.0"
}

GENERIC_TYPE = {
    "id": "Workstation",
    "layout": "Workstation Layout",
    "locked": False,
    "name": "Workstation",
    "color": "#8052f4",
    "definitionId": "asset",
    "genericModuleId": "rbvm",
    "system": False,
    "version": -1,
    "fromVersion": "6.5.0"
}

GENERIC_MODULE = {
    "id": "rbvm",
    "version": -1,
    "name": "Risk Based Vulnerability Management",
    "fromVersion": "6.5.0",
    "definitionIds": [
        "asset"
    ],
    "views": [{
        "icon": "icon-widget-infinity-24-s",
        "name": "RBVM",
        "title": "Risk Base Vulnerability Management",
        "tabs": [
            {
                "name": "Assets",
                "newButtonDefinitionId": "asset",
                "dashboard": {
                    "id": "asset_dashboard",
                    "version": -1,
                    "fromDate": "0001-01-01T00:00:00Z",
                    "toDate": "0001-01-01T00:00:00Z",
                    "period": {
                        "by": "",
                        "byTo": "",
                        "byFrom": "days",
                        "toValue": None,
                        "fromValue": 7,
                        "field": ""
                    },
                    "name": "Assets Dashboard",
                    "prevName": "Assets Dashboard",
                    "layout": [
                        {
                            "id": "3a352fc0-dca9-11eb-999f-35f993b96a7c",
                            "forceRange": False,
                            "x": 0,
                            "y": 0,
                            "i": "3a352fc0-dca9-11eb-999f-35f993b96a7c",
                            "w": 12,
                            "h": 3,
                            "widget": {
                                "id": "f5833f22-7357-40c9-8d5b-c02ee1f0c53b",
                                "version": 2,
                                "modified": "2021-03-20T23:03:11.86024+02:00",
                                "sortValues": None,
                                "packID": "",
                                "itemVersion": "",
                                "fromServerVersion": "",
                                "toServerVersion": "",
                                "propagationLabels": [
                                    "all"
                                ],
                                "vcShouldIgnore": False,
                                "vcShouldKeepItemLegacyProdMachine": False,
                                "commitMessage": "",
                                "shouldCommit": False,
                                "name": "A Widget v2",
                                "prevName": "A Widget v2",
                                "dataType": "incidents",
                                "widgetType": "pie",
                                "query": "",
                                "sort": None,
                                "isPredefined": False,
                                "dateRange": {
                                    "fromDate": "0001-01-01T00:00:00Z",
                                    "toDate": "0001-01-01T00:00:00Z",
                                    "period": {
                                        "by": "",
                                        "byTo": "",
                                        "byFrom": "days",
                                        "toValue": None,
                                        "fromValue": 7,
                                        "field": ""
                                    },
                                    "fromDateLicense": "0001-01-01T00:00:00Z"
                                },
                                "params": {
                                    "groupBy": [
                                        "type"
                                    ],
                                    "tableColumns": [
                                        {
                                            "isDefault": True,
                                            "key": "id",
                                            "position": 0,
                                            "width": 110
                                        }
                                    ]
                                },
                                "size": 0,
                                "category": ""
                            },
                            "reflectDimensions": True
                        }
                    ],
                    "system": True,
                    "isCommon": True
                }
            }]
    }]
}

GENERIC_DEFINITION = {
    "version": -1,
    "locked": False,
    "system": False,
    "fromVersion": "6.5.0",
    "id": "assets",
    "name": "Assets",
    "partitioned": True,
    "auditable": False,
    "rbacSupport": True
}
