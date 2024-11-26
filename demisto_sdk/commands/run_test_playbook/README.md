## Run test playbook

### Overview

**Run a test playbook in a given XSOAR instance.**
**This command creates a new instance in XSOAR and runs the given test playbook.**

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
* **-tpb', '--test-playbook-path**
                        Path to test playbook to run, can be a path to specific test playbook or path to pack name for example: Packs/GitHub.
* **-t, --timeout**
                        Timeout for the command in seconds. The test playbook will continue to run in XSOAR.
                        (default: 90)
* **--insecure**
                        Skip certificate validation.
* **-w, --wait**
                        Wait until the playbook run is finished and get a response.
                        (default: True)
* **--all**
                        Run all the test playbooks from this repository.


### Examples
For the examples let's assume we set both the `DEMISTO_API_KEY` and `DEMISTO_BASE_URL` environment variables:
<br/><br/>
export DEMISTO_BASE_URL = `https://demisto.local`
<br/><br/>
export DEMISTO_API_KEY = `api key`
<br/><br/>


```
demisto-sdk run-playbook -tpb 'Packs/Github/TestPlaybooks/Test-Github_test_playbook.yml'
```

This will run the playbook `Test-Github_test_playbook.yml` in XSOAR instance `https://demisto.local` and will wait for the test playbook to finish its run.
<br/><br/>

```
demisto-sdk run-playbook -tpb 'Packs/Github'
```
This will run all the test playbooks in `Packs/GitHub/TestPlaybooks` in XSOAR instance `https://demisto.local` and will wait for the playbooks to finish its run.
<br/><br/>

```
demisto-sdk run-playbook --all
```
This will run all the test playbooks from the repository in XSOAR instance `https://demisto.local` and will wait for the playbooks to finish its run.
