import pytest
import requests
from requests.sessions import HTTPAdapter
from urllib3 import Retry

from demisto_sdk.commands.common.MDXServer import (DEMISTO_DEPS_DOCKER_NAME,
                                                   start_docker_MDX_server)
from demisto_sdk.commands.lint.docker_helper import init_global_docker_client


def assert_successful_mdx_call():
    session = requests.Session()
    retry = Retry(total=2)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    response = session.request(
        'POST',
        'http://docker:6161',
        data='## Hello',
        timeout=20
    )
    assert response.status_code == 200


def assert_not_successful_mdx_call():
    session = requests.Session()
    retry = Retry(total=2)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    response = session.request(
        'POST',
        'http://docker:6161',
        data='<div> Hello',
        timeout=20
    )
    assert response.status_code == 500


def container_is_up():
    return any(container.name == DEMISTO_DEPS_DOCKER_NAME
               for container in init_global_docker_client().containers.list())


def test_is_file_not_valid():
    with start_docker_MDX_server() as boolean:
        assert boolean
        assert container_is_up()
        assert_not_successful_mdx_call()
    assert not container_is_up()


def test_docker_server_reentrant():
    with start_docker_MDX_server():
        if start_docker_MDX_server():
            assert container_is_up()
            assert_successful_mdx_call()
        assert_successful_mdx_call()
        assert container_is_up()
    assert not container_is_up()


def test_docker_server_up_and_down():
    with start_docker_MDX_server() as boolean:
        assert boolean
        assert container_is_up()
        assert_successful_mdx_call()
    assert not container_is_up()
