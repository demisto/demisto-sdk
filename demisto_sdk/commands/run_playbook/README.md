## Run playbook

**Run a playbook in a given Demisto instance.**
**This command creates a new instance in Demisto and runs the given playbook.**

* In order to run the command, `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
* You can either specify a URL as an environment variable named: `DEMISTO_BASE_URL`, or enter it as an argument.

To set the environment variables, run the following shell commands:
```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```

**Arguments**:
* **-u, --url**
                        URL to a Demisto instance.
* **-p, --playbook_id**
                        The ID of the playbook to run.
* **-n, --no-wait**
                        Trigger the playbook without waiting for it to finish its run.
                        (default: False)
* **-t, --timeout**
                        Timeout for the command in seconds. The playbook will continue to run in Demisto.
                        (default: 90)


### Examples
For the examples let's assume we set both the `DEMISTO_API_KEY` and `DEMISTO_BASE_URL` environment variables:
<br/><br/>
export DEMISTO_BASE_URL = `https://demisto.local`
<br/><br/>
export DEMISTO_API_KEY = `api key`
<br/><br/>


```
demisto-sdk run-playbook -p 'playbook_name'
```

This will run the playbook `playbook_name` in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run.
If the run is taking more than 90 seconds (the default timeout), the command will stop while the playbook will keep running in Demisto.
<br/><br/>

```
demisto-sdk run-playbook -p 'playbook_name' -n
```
This will run the playbook `playbook_name` in Demisto instance `https://demisto.local` and will not wait to see the response.
The playbook will keep running in Demisto.
<br/><br/>

```
demisto-sdk run-playbook -p 'playbook_name' -t 300
```
This will run the playbook 'playbook_name' in Demisto instance `https://demisto.local` and will wait for the playbook to finish its run.
If the playbook is running for more than 5 minutes (300 seconds), the command will stop while the playbook will keep running in Demisto.
If you have a long running playbook, consider increasing the timeout argument respectively.
