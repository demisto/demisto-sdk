import subprocess
import sys

import demisto_client

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_demisto_version
from TestSuite.playbook import Playbook
from TestSuite.repo import Repo
from pathlib import Path
import random

def git_clone_demisto_sdk(
    destination_folder: str, sdk_git_branch: str = DEMISTO_GIT_PRIMARY_BRANCH
):
    """Clone demisto-sdk from GitHub and add it to sys.path"""
    from demisto_sdk.commands.common.git_util import GitUtil

    logger.info(f"Cloning demisto-sdk to {destination_folder}")

    GitUtil.REPO_CLS.clone_from(
        url="https://github.com/demisto/demisto-sdk.git",
        to_path=destination_folder,
        multi_options=[f"-b {sdk_git_branch}", "--single-branch", "--depth 1"],
    )

    sys.path.insert(1, f"{destination_folder}")


def cli(command: str) -> subprocess.CompletedProcess:
    if command:
        run_req = str(command).split(" ")
        ret_value: subprocess.CompletedProcess = subprocess.run(run_req)
        ret_value.check_returncode()
        return ret_value
    raise Exception("cli cannot be empty.")


def connect_to_server(insecure: bool = False):
    verify = (
        (not insecure) if insecure else None
    )  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
    client = demisto_client.configure(verify_ssl=verify)
    demisto_version = get_demisto_version(client)
    if demisto_version == "0":
        raise Exception(
            "Could not connect to XSOAR server. Please check your connection configurations."
        )
    return client

def create_pack(repo: Repo):
    unique_id = random.randint(1, 100)
    pack_name = "e2e_test_" + str(unique_id)
    pack = repo.create_pack(name=pack_name)
    source_pack_path = Path(pack.path)

    return pack, pack_name, source_pack_path

def create_playbook(pack, pack_name):
    playbook_name = "pb_e2e_test_" + pack_name
    playbook: Playbook = pack.create_playbook(name=playbook_name)
    playbook.create_default_playbook(name=playbook_name)
    playbook_path = Path(playbook.yml.path)
    
    return playbook, playbook_name, playbook_path

def create_xif_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_string):

    with open(f"{pack_path}/ModelingRules/{modeling_rules_name}/{modeling_rules_name}.xif", 'w') as file:
        file.write(modeling_rules_string)

def create_yml_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_id):
    
    yml_file_string = f"""
fromversion: 8.4.0
id: {modeling_rules_id}
name: {modeling_rules_name}
rules: ''
schema: ''
    """
    
    with open(f"{pack_path}/ModelingRules/{modeling_rules_name}/{modeling_rules_name}.yml", 'w') as file:
        file.write(yml_file_string)

def create_schema_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_schema_string):

    with open(f"{pack_path}/ModelingRules/{modeling_rules_name}/{modeling_rules_name}_schema.json", 'w') as file:
        file.write(modeling_rules_schema_string)

def create_testdata_file_modeling_rules(pack_path, modeling_rules_name, test_data_string):

    with open(f"{pack_path}/ModelingRules/{modeling_rules_name}/{modeling_rules_name}_testdata.json", 'w') as file:
        file.write(test_data_string)

def create_modeling_rules_folder(pack_path, modeling_rules_name, modeling_rules_id, modeling_rules_string, test_data_string, modeling_rules_schema_string):
    """Creating the modeling rules folder, consists of modeling rules file, schema, yml and testdata file

    Args:
        pack_path (str): The path of the pack to add modeling rules to
        modeling_rules_name (str): The name of the modeling rules.
        modeling_rules_id (str): The ID of the modeling rules.
        modeling_rules_string (str): The data of the modeling rules xif file.
        test_data_string (str): The data of the testdata.
        modeling_rules_schema_string (str): The data of the schema
    """
    cli(f"mkdir -p {pack_path}/ModelingRules/{modeling_rules_name}")

    create_testdata_file_modeling_rules(pack_path, modeling_rules_name, test_data_string)
    create_schema_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_schema_string)
    create_yml_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_id)
    create_xif_file_modeling_rules(pack_path, modeling_rules_name, modeling_rules_string)
