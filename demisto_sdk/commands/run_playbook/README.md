## Run playbook

### Overview

This command runs the given playbook in Cortex XSOAR or Cortex XSIAM.

In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.
To use the command on Cortex XSIAM the `XSIAM_AUTH_ID` environment variable should also be set.
To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```
and for Cortex XSIAM
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
* **-u, --url** URL to a XSOAR instance. If not provided, the url will be taken from DEMISTO_BASE_URL environment variable.
* **-p, --playbook_id** The ID of the playbook to run.
* **-t, --timeout** Timeout for the command in seconds.The playbook will continue to run in Cortex XSOAR/Cortex XSIAM. The default is 90 seconds.
* **--insecure** Skip certificate validation.
* **-w, --wait** Wait until the playbook run is finished and get a response.


### Examples
For the examples let's assume we set both the `DEMISTO_API_KEY` and `DEMISTO_BASE_URL` environment variables:
<br/><br/>
export DEMISTO_BASE_URL = `https://demisto.local`
<br/><br/>
export DEMISTO_API_KEY = `api key`
<br/><br/>


```
demisto-sdk run-playbook -p 'playbook_id'
```

This will run the playbook with `playbook_id` in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run.
If the run is taking more than 90 seconds (the default timeout), the command will stop while the playbook will keep running in Demisto.
<br/><br/>

```
demisto-sdk run-playbook -p 'playbook_id' -n
```
This will run the playbook with `playbook_id` in Demisto instance `https://demisto.local` and will not wait to see the response.
The playbook will keep running in Demisto.
<br/><br/>

```
demisto-sdk run-playbook -p 'playbook_id' -t 300
```
This will run the playbook with 'playbook_id' in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run.
If the playbook is running for more than 5 minutes (300 seconds), the command will stop while the playbook will keep running in Demisto.
If you have a long running playbook, consider increasing the timeout argument respectively.
