## Ansible Codegen

Generates a Cortex XSOAR Ansible integration given a integration configuration file.
In the first run of the command, an integration configuration file is created, which needs be modified with the details of the Ansible which will be packaged as a integration.
Then, the command is run a second time with the integration configuration to generate the actual integration files.

**Use-Cases**
This command is used to create Cortex XSOAR integrations from Ansible modules.

**Note**
Docker must be installed for this command to function. If the docker image referenced by `--container_image` is not found locally, it will be attempted to be downloaded from the image registry.

**Arguments**:

* **-h, --help**
Output help text
* **-ci, --container_image**
The ansible-runner container image to use for working with Ansible. If not specified the latest demisto/ansible-runner is used.
* **-cf, --config_file**
The integration configuration YAML file. It is created in the first run of the command.
* **-n, --base_name**
The base filename to use for the generated files
* **-o, --output_dir**
Directory to store the output in (default is current working directory.
* **-f, --fix_code**
Format the python code using autopep8.
* **-v, --verbose**
Be verbose with the log output.

### Configuration File

This command primarily uses a configuration file as input for the settings of the integration. A example YAML template is generated on first run of the command to be further customised. These are the configuration elements:

* **name**
Name of integration

* **display**
Displayed name of integration

* **category**
Integration Category. See [XSOAR Pack Documentation](https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories)

* **description**
Short integration description

* **parameters**
List of integration configuration parameters. See [XSOAR YAML file configuration](https://xsoar.pan.dev/docs/integrations/yaml-file#configuration) for details. Params are sent as arguments to the underlying Ansible module using the param name

* **ignored_args**
List of any Ansible module arguments that should be ignored from the command definition. For example because the argument is coming from the integration parm

* **creds_mapping**
Optional key:value pairs to translate XSOAR param to ansible arguments. Used in cases where argument name collisions may occur.

* **test_command**
Which ansible module should be used as the integration test command. This should be a module that can run with just the integration config parameters. Omit option if such testing is not possible

* **command_prefix**
Prefix all the generated XSOAR commands with this value. Omit config or set to None to not add any prefix  

* **host_type**
The Ansible connection type. Use one of: 'ssh', 'winrm', 'nxos', 'ios', 'local'. Modules that run locally and use their own connection mechanism should use the value 'local'.

* **ansible_modules**
List of ansible modules to include. Preferred to be in the Ansible collection namespace syntax to avoid ambiguity

### Known Limitations

The following limitations in XSOAR Ansible integration API is known:

* **Ansible Module Environment Var Inputs**:
Some Ansible Modules take input from OS Environment Variable. This is not currently supported by the Ansible Integration API.

* **File Operations**:
File copy Ansible modules can only operate in 'remote src to remote dest' mode. They cannot be used to copy files from/to the XSOAR engine server.

* **Shell Modules**:
Ansible Shell/Command modules that use free-form syntax are not supported

* **Connection Types**:
Only the following ansible connection types are supported by the XSOAR Ansible API:
  * ssh
  * winrm
  * nxos
  * ios
  * local

### Recommended Usage Workflow

Ansible-codegen parses the specified Ansible module documentation and confirms the module availability in the provided container image. However it does not have the capability to test if the module pre-requisite requirements are met, or if the module actually functions. For this reason it is recommended to first manually test adhoc Ansible CLI usage of the desired Ansible module with the supplied container image. It may be required to add python modules or OS packages to the container image to support the desired module. If you plan to release a Ansible-based XSOAR integration to the marketplace please submit any required ansible-runner container image changes as a PR to the [Ansible-Runner](https://github.com/demisto/dockerfiles/tree/master/docker/ansible-runner) container in the [demisto/dockerfiles](https://github.com/demisto/dockerfiles) repo.

The suggested workflow is as follows:

1. Run the `ansible-codegen` command with the desired `--base_name` and optionally `--output_dir`. Take note of the latest demisto/ansible-runner that is determined by the command.

    ``` bash
    $ demisto-sdk ansible-codegen --base_name example
    Created empty configuration file example_config.yml. 
    Run the command again with the created configuration file (after populating it): demisto-sdk ansible-codegen -cf "example_config.yml" -ci "demisto/ansible-runner:1.0.0.24037" -n "example"
    ```

    Note how in the above example the latest ansible-runner image is determined to be demisto/ansible-runner:1.0.0.24037.

2. Manually start a container in your test environment with the ansible-runner image: `docker run -it --rm demisto/ansible-runner:1.0.0.24037 bash`. The flag `-it` combined with `bash` connects you to a interactive `bash` terminal inside the container. The flag `--rm` indicates that the container should be removed when you exit `bash`.

3. Confirm that the desired Ansible modules is in the container using the `ansible-doc -t module_name` command.

4. Create a inventory text file similar to one that would be generated by the XSOAR Ansible Integration APIs. Below are examples which can be copied and modified.

    * **ssh**:

      ``` yaml
      all:
        hosts:
          host:
            ansible_host: hostname
            ansible_port: 22
            ansible_user: username
            ansible_password: password
            ansible_become: yes
            ansible_become_method: sudo
            ansible_become_user: root
      ```

    * **winrm**:

      ``` yaml
      all:
        hosts:
          host:
            ansible_connection: winrm
            ansible_winrm_transport: ntlm
            ansible_winrm_server_cert_validation: ignore
            ansible_host: hostname
            ansible_port: 5985
            ansible_user: username
            ansible_password: password
      ```

    * **nxos**:

      ``` yaml
      all:
        hosts:
          host:
            ansible_connection: network_cli
            ansible_network_os: nxos
            ansible_host: hostname
            ansible_port: 22
            ansible_user: username
            ansible_password: password
            ansible_become: yes
            ansible_become_method: enable
      ```

    * **ios**:

      ``` yaml
      all:
        hosts:
          host:
            ansible_connection: network_cli
            ansible_network_os: ios
            ansible_host: hostname
            ansible_port: 22
            ansible_user: username
            ansible_password: password
            ansible_become: yes
            ansible_become_method: enable
            ansible_become_password: enable_password
      ```

    * **local**:

      ``` yaml
      all:
        hosts:
          localhost:
            ansible_connection: local
      ```

5. Run the desired Ansible module via the Ansible adhoc CLI providing the inventory file as input. `ansible -i inventory_file.yml -m module_name -a arg1=value host`. See [Ansible Adhoc Documentation](https://docs.ansible.com/ansible/latest/user_guide/intro_adhoc.html) for further reference information.

6. If the module failed to run, determine the required changes to the container to support the module. A good starting point is to read the Ansible module's requirement documentation: `ansible-doc -t module module_name`

7. Repeat steps 3-6 for all modules to be included in the Integration

8. Populate the ansible-codegen configuration .yml file generated in step #1

9. Run `demisto-sdk ansible-codegen` again with the provided flags in step #1 to generate the XSOAR integration

10. Test the Integration by loading the generated files into your demisto server and using the integration: `demisto-sdk upload`
