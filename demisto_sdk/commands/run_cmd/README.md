## Run

### Overview
**Run commands in the playground of a remote Cortex XSOAR instance, and pretty print the output.**

This command is used in order to run integration or script commands of a remote Cortex XSOAR instance. This is useful especially when developing new commands or fixing bugs, so that while working on the code the developer can debug it directly from the CLI and optimize the development process flow.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

**Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
- Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button in the top right corner, and not the browser URL.
- API key should be of a `standard` security level, and have the `Instance Administrator` role.
- To use the command the `XSIAM_AUTH_ID` environment variable should also be set.


To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```
and for Cortex XSIAM or Cortex XSOAR 8.x
```
export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
```
Note!
As long as `XSIAM_AUTH_ID` environment variable is set, SDK commands will be configured to work with an XSIAM instance.
In order to set Demisto SDK to work with Cortex XSOAR instance, you need to delete the XSIAM_AUTH_ID parameter from your environment.
```bash
unset XSIAM_AUTH_ID
```

### Options
* **-q --query** The query to run.
* **--insecure** Skip certificate validation.
* **-id --incident-id** The incident to run the query on, if not specified the playground will be used.
* **--json-to-outputs** Whether to run json_to_outputs command on the context output of the query. If the context output does not exist or the `-r` flag is used, will use the raw response of the query.
* **-p, --prefix** Used with `json-to-outputs` flag. Output prefix e.g. Jira.Ticket, VirusTotal.IP, the base path for the outputs that the script generates.
* **-r, --raw-response** Used with `json-to-outputs` flag. Use the raw response of the query for `json-to-outputs`.
* **-d, --debug** Whether to enable the debug-mode feature or not, if you want to save the output file, please use the --debug-path option.
* **--debug-path**The path to save the debug file at, if not specified the debug file will be printed to the terminal.

### Examples
Note that `!` is not mandatory, as we add it if needed. You can also use double quotes `"` or single quotes `'` to wrap the query.
```
demisto-sdk run -q 'ip ip="8.8.8.8"'
```
Runs the query `!ip ip="8.8.8.8"` on the playground of the Cortex XSOAR instance and print the output.
<br/><br/>

```
demisto-sdk run -q "panorama-list-address-groups"
```
Runs the query `!panorama-list-address-groups` on the playground of the Cortex XSOAR instance and print the output.
<br/><br/>

```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"'
```
Runs the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Cortex XSOAR instance and print the output.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -k
```
Runs the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Cortex XSOAR instance without a certificate validation, and print the output.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -v
```
Runs the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Cortex XSOAR instance, print the output and additional meta-data.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -D
```
Runs the query `!gct-translate-text text="ciao" target="iw"` in debug mode (with `debug-mode="true"`) on the playground of the Cortex XSOAR instance, print the output, retrieve the debug log file and pretty print it.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -D --debug-path output.log
```
Runs the query `!gct-translate-text text="ciao" target="iw"` in debug mode (with `debug-mode="true"`) on the playground of the Cortex XSOAR instance, print the output and creates `output.log` file that contains the command debug logs.
