# `generate-modeling-rules`

**Usage**:

```console
$ generate-modeling-rules [OPTIONS]
```

**Options**:

* `-m, --mapping PATH`: The path to a csv or tsv file containing the mapping for the modeling rules.  [required]
* `-re, --raw_event PATH`: The path to a raw event from the API call in a JSON format.  [required]
* `-dm, --data_model PATH`: The path to the one data model schema, please check the conflunce, for more information.  [required]
* `-o, --output PATH`: A path to the folder you want to generate the modeling rules in. Best practice is to put the working pack path here.  [required]
* `-ve, --vendor TEXT`: The vendor name of the product in snake_case.
* `-p, --product TEXT`: The name of the product in snake_case.
* `-v, --verbose INTEGER RANGE`: Verbosity level -v / -vv / .. / -vvv  [Default: 0; x<=3]
* `--quiet / --no-quiet`: Quiet output - sets verbosity to default.  [Default: no-quiet]
* `-lp, --log-path PATH`: Path of the directory in which you would like to store all log levels. If not given, then the "log_file_name" command line option will be disregarded, and the log output will be to stdout.
* `-ln, --log-name TEXT`: The file name (including extension) where the log output should be saved to.  [Default: generate_modeling_rules.log]
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Preliminary requirements**
The `mapping` file must be written in a specific format as a .csv/.tsv file.<br/>
This document must contain 2 columns.<br/>
[One Data Model - The corresponding field from the one data model]<br/>
[Raw Event Path - The path to the field name in the raw event.]

***Nested fields***
If the field is nested, specify a full path with `.` between the hierarchy.
For example. the UTC field
`{'event' : 'time' : 'UTC' : 5}`
will be specified by event.time.UTC in the mapping file.

***Coalesce***
To specify 2 fields that map to the same xdm one data model rule uses `|`.
For example, under the `Raw Event Path` column, with ipv4 and ip mapped to the same xdm field `ipv4 | ip`.


**Command capabilities**

This command parses the raw events and the one data model to extract the field types.
The command will prepare a draft of the .yml, .json, and .xif file with the basic type conversion needed.
Now supports:
- to_string
- to_number
- create_array
- json_extract_array
- json_extract_scalar
- coalesce
