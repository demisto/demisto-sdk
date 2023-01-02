from subprocess import CalledProcessError

from demisto_sdk.commands.test_content.tools import is_redhat_instance


def raise_exception():
    raise CalledProcessError(1, "ls -l /home/ec2-user/rhel_ami".split())


class CheckOutputMock:
    stdout = "output"


def test_is_redhat_instance_positive(mocker):
    mocker.patch("subprocess.run", return_value=CheckOutputMock)
    assert is_redhat_instance("instance_ip")


def test_is_redhat_instance_negative(mocker):
    mocker.patch("subprocess.check_output", side_effect=raise_exception)
    assert not is_redhat_instance("instance_ip")
