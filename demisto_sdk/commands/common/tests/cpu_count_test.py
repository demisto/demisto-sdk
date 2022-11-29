from demisto_sdk.commands.common.cpu_count import DEMISTO_SDK_MAX_THREADS, cpu_count, os


def test_with_env_set(mocker):
    mocker.patch.dict(os.environ, {DEMISTO_SDK_MAX_THREADS: "1"})
    assert cpu_count() == 1


def test_with_invalid_env_set(mocker):
    mocker.patch.dict(os.environ, {DEMISTO_SDK_MAX_THREADS: ""})
    assert cpu_count() == os.cpu_count()


def test_without_env_set():
    assert cpu_count() == os.cpu_count()
