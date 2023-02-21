# `generate-modeling-rules`

This command is used to help develope modeling rules. 
It generates the .yml/.xif/.json files related to the modeling rules. 

**Usage**:

```console
$ generate-modeling-rules [OPTIONS] MAPPING RAW_EVENT_PATH OUTPUT_PATH [VENDOR] [PRODUCT]
```

**Example**:

generate-modeling-rules mapping_dfender_for_cloud.csv event.json test_output_folder test_vendor test_product -lp test_logs_folder -v 3

**Arguments**:

* `MAPPING`: The Path to a csv or tsv file containing the mapping for the modeling rules.  [required]
* `RAW_EVENT_PATH`: The path to a raw event from the api call in a json format.  [required]
* `OUTPUT_PATH`: A path to the pack you want to generate the modeling rules in. Best practice to put the working pack path  [required]
* `[VENDOR]`: The vendor name of the product
* `[PRODUCT]`: The name of the product

**Options**:

* `-v, --verbose INTEGER RANGE`: Verbosity level -v / -vv / .. / -vvv  [default: 0; x<=3]
* `--quiet / --no-quiet`: Quiet output - sets verbosity to default.  [default: no-quiet]
* `-lp, --log-path PATH`: Path of directory in which you would like to store all levels of logs. If not given, then the "log_file_name" command line option will be disregarded, and the log output will be to stdout.
* `-ln, --log-name TEXT`: The file name (including extension) where log output should be saved to.  [default: generate_modeling_rules.log]
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.




**Preliminary requirements**
The `MAPPING` file needs to be written with a specific format as a .csv/.tsv file.<br/>
This document must contain 2 columns.<br/>
[XDM Field One Data Model - The corresponding field from the one data model]<br/>
[Name - The path to the field name in the raw event.]
If the field is nested specify full path with `.` between hirarchy
for example the field UTC
`{'event' : 'time' : 'UTC' : 5}`
will be specified by event.time.UTC in the mapping file. 

**Command capabilitys**

This command parses the raw events and the one data model to extracts the fields types.
The command will prepare a draft of the .xif file with the basic type conversion needed. 
Now supports: 
- to_string
- to_number
- create_array
- json_extract_array
- json_extract_scalar