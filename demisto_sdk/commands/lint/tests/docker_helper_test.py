import os
from unittest import mock

import demisto_sdk.commands.common.docker_helper as dhelper


def test_init_global_docker_client():
    res = dhelper.init_global_docker_client(log_prompt="unit testing")
    assert res is not None
    assert res == dhelper.DOCKER_CLIENT
    dhelper.DOCKER_CLIENT = None
    # test with bad creds (should still get a valid instance)
    with mock.patch.dict(
        os.environ, {"DOCKERHUB_USER": "dummy", "DOCKERHUB_PASSWORD": "dummy"}
    ):
        res = dhelper.init_global_docker_client(log_prompt="unit testing")
        assert res is not None
        assert res == dhelper.DOCKER_CLIENT
