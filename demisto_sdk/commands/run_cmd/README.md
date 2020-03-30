## Run

**Run commands in the playground of a remote Demisto instance, and pretty print the output.**

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Demisto base URL, and `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```


### Use Cases
This command is used in order to run integration or script commands of a remote Demisto instance. This is useful especially when developing new commands or fixing bugs, so that while working on the code the developer can debug it directly from the CLI and optimize the development process flow.


### Arguments
* **-q QUERY, --query QUERY**

    The query to run

* **-k, --insecure**

    Skip certificate validation

* **-v, --verbose**

    Verbose output

* **-D, --debug**

    Whether to enable the debug-mode feature or not, if you want to save the output file, please use the --debug-path option

* **--debug-path [DEBUG_LOG]**

    The path to save the debug file at, if not specified the debug file will be printed to the terminal

### Examples
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"'
```
This will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance and print the output.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -k
```
This will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance without a certificate validation, and print the output.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -v
```
This will run the query `!gct-translate-text text="ciao" target="iw"` on the playground of the Demisto instance, print the output and additional meta-data.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -D
```
This will run the query `!gct-translate-text text="ciao" target="iw"` in debug mode (with `debug-mode="true"`) on the playground of the Demisto instance, print the output, retrieve the debug log file and pretty print it.
<br/><br/>
```
demisto-sdk run -q '!gct-translate-text text="ciao" target="iw"' -D --debug-path output.log
```
This will run the query `!gct-translate-text text="ciao" target="iw"` in debug mode (with `debug-mode="true"`) on the playground of the Demisto instance, print the output and creates `output.log` file that contains the command debug logs.
