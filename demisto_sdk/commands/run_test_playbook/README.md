## Run test playbook

**Run a test playbook in a given XSOAR instance.**
**This command creates a new instance in XSOAR and runs the given test playbook.**

* In order to run the command, `DEMISTO_API_KEY` environment variable should contain a valid Demisto API Key.
* You can either specify a URL as an environment variable named: `DEMISTO_BASE_URL`, or enter it as an argument.

To set the environment variables, run the following shell commands:

```
export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
```

**Arguments**:
* **-i, --input**
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
demisto-sdk run-playbook -i 'Packs/Github/TestPlaybooks/Test-Github_test_playbook.yml'
```

This will run the playbook `Test-Github_test_playbook.yml` in XSOAR instance `https://demisto.local` and will wait for the test playbook to finish its run.
<br/><br/>

```
demisto-sdk run-playbook -p 'Packs/Github'
```
This will run all the test playbooks in `Packs/GitHub/TestPlaybooks` in XSOAR instance `https://demisto.local` and will wait for the playbooks to finish its run.
<br/><br/>

```
demisto-sdk run-playbook --all
```
This will run all the test playbooks from the repository in XSOAR instance `https://demisto.local` and will wait for the playbooks to finish its run.
