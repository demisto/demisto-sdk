from pathlib import Path
# from pprint import pformat
from typing import List, Optional
from google.cloud import bigquery
from google.cloud.pubsub_v1 import PublisherClient
from google.oauth2 import service_account
from google.auth import default

# test_modeling_rules(
#     input, pre_clean, post_clean, fail_missing, xsiam_url, api_key, auth_id, project_id, service_account
# )


def create_google_pubsub_client(service_account_filepath: Optional[Path]) -> PublisherClient:
    if service_account_filepath:
        credentials = service_account.Credentials.from_service_account_file(service_account_filepath.as_posix())
        publisher = PublisherClient(credentials=credentials)
    else:
        publisher = PublisherClient()
    return publisher


def create_google_bigquery_client(project_id: str, service_account_filepath: Optional[str]):
    if service_account_filepath:
        credentials = service_account.Credentials.from_service_account_file(service_account_filepath)
        bigquery_client = bigquery.Client(project=project_id, credentials=credentials)
    else:
        bigquery_client = bigquery.Client(project=project_id)
    return bigquery_client


def test_modeling_rule(mrule_dir: Path):
    ...


# def test_modeling_rules(*args, **kwargs):
#     print(pformat(args))
#     print(pformat(kwargs))


def test_modeling_rules(mrule_dirs: List[Path], pre_clean: bool, post_clean: bool, fail_missing: bool,
                        xsiam_url: str, api_key: str, auth_id: str, project_id: Optional[str],
                        service_account: Optional[Path]):
    if not project_id:
        project_id = default()[1]
    pubsub_client = create_google_pubsub_client(service_account)
