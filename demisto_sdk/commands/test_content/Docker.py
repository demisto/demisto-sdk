import logging
import re
from subprocess import PIPE, Popen

from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


class Docker:
    """Client for running docker commands on remote machine using ssh connection."""

    PYTHON_INTEGRATION_TYPE = "python"
    POWERSHELL_INTEGRATION_TYPE = "powershell"
    JAVASCRIPT_INTEGRATION_TYPE = "javascript"
    DEFAULT_PYTHON2_IMAGE = "demisto/python"
    DEFAULT_PYTHON3_IMAGE = "demisto/python3"
    COMMAND_FORMAT = "{{json .}}"
    MEMORY_USAGE = "MemUsage"
    PIDS_USAGE = "PIDs"
    CONTAINER_NAME = "Name"
    CONTAINER_ID = "ID"
    DEFAULT_CONTAINER_MEMORY_USAGE = 75
    DEFAULT_CONTAINER_PIDS_USAGE = 3
    DEFAULT_PWSH_CONTAINER_MEMORY_USAGE = 140
    DEFAULT_PWSH_CONTAINER_PIDS_USAGE = 24
    REMOTE_MACHINE_USER = "ec2-user"
    SSH_OPTIONS = "ssh -o StrictHostKeyChecking=no"

    @classmethod
    def _build_ssh_command(cls, server_ip, remote_command, force_tty=False):
        """Add and returns ssh prefix and escapes remote command

        Args:
            server_ip (str): remote machine ip to connect using ssh.
            remote_command (str): command to execute in remote machine.
            force_tty (bool): adds -t flag in order to force tty allocation.

        Returns:
            str: full ssh command

        """
        remote_server = f"{cls.REMOTE_MACHINE_USER}@{server_ip}"
        ssh_prefix = f"{cls.SSH_OPTIONS} {remote_server}"
        if force_tty:
            ssh_prefix += " -t"
        # escaping the remote command with single quotes
        cmd = f"{ssh_prefix} '{remote_command}'"

        return cmd

    @classmethod
    def _build_stats_cmd(cls, server_ip, docker_images):
        """Builds docker stats and grep command string.

        Example of returned value:
        ssh -o StrictHostKeyChecking=no ec2-user@server_ip
        'sudo docker stats --no-stream --no-trunc --format "{{json .}}" | grep -Ei "demistopython33.7.2.214--"'
        Grep is based on docker images names regex.

            Args:
                server_ip (str): Remote machine ip to connect using ssh.
                docker_images (set): Set of docker images.

            Returns:
                str: String command to run later as subprocess.

        """
        # docker stats command with json output
        docker_command = (
            f'sudo docker stats --no-stream --no-trunc --format "{cls.COMMAND_FORMAT}"'
        )
        # replacing : and / in docker images names in order to grep the stats by container name
        docker_images_regex = [
            "{}--".format(re.sub("[:/]", "", docker_image))
            for docker_image in docker_images
        ]
        pipe = " | "
        grep_command = 'grep -Ei "{}"'.format("|".join(docker_images_regex))
        remote_command = docker_command + pipe + grep_command
        cmd = cls._build_ssh_command(server_ip, remote_command)

        return cmd

    @classmethod
    def _build_kill_cmd(cls, server_ip, container_name):
        """Constructs docker kll command string to run on remote machine.

        Args:
            server_ip (str): Remote machine ip to connect using ssh.
            container_name (str): Docker container name to kill.

        Returns:
            str: String of docker kill command on remote machine.
        """
        remote_command = f"sudo docker kill {container_name}"
        cmd = cls._build_ssh_command(server_ip, remote_command)

        return cmd

    @classmethod
    def _build_pid_info_cmd(cls, server_ip, container_id):
        """Constructs docker exec ps command string to run on remote machine.

        Args:
            server_ip (str): Remote machine ip to connect using ssh.
            container_id (str): Docker container id.

        Returns:
            str: String of docker exec ps command on remote machine.

        """
        remote_command = f"sudo docker exec -it {container_id} ps -fe"
        cmd = cls._build_ssh_command(server_ip, remote_command, force_tty=True)

        return cmd

    @classmethod
    def _parse_stats_result(cls, stats_lines, logging_module=logging):
        """Parses the docker statics str and converts to Mib.

        Args:
            stats_lines (str): String that contains docker stats.
            logging_module: The logging module that should be used.
        Returns:
            list: List of dictionaries with parsed docker container statistics.

        """
        stats_result = []
        try:
            containers_stats = [json.loads(c) for c in stats_lines.splitlines()]

            for container_stat in containers_stats:
                memory_usage_stats = (
                    container_stat.get(cls.MEMORY_USAGE, "").split("/")[0].lower()
                )

                if "kib" in memory_usage_stats:
                    mib_usage = (
                        float(memory_usage_stats.replace("kib", "").strip()) / 1024
                    )
                elif "gib" in memory_usage_stats:
                    mib_usage = (
                        float(memory_usage_stats.replace("kib", "").strip()) * 1024
                    )
                else:
                    mib_usage = float(memory_usage_stats.replace("mib", "").strip())

                stats_result.append(
                    {
                        "memory_usage": mib_usage,
                        "pids": int(container_stat.get(cls.PIDS_USAGE)),
                        "container_name": container_stat.get(cls.CONTAINER_NAME),
                        "container_id": container_stat.get(cls.CONTAINER_ID),
                    }
                )
        except Exception:
            logging_module.exception(
                "Failed in parsing docker stats result, returned empty list."
            )
        finally:
            return stats_result

    @classmethod
    def run_shell_command(cls, cmd):
        """Executes shell command and returns outputs of the process.

        Args:
            cmd (str): command to execute.

        Returns:
            str: stdout of the executed command.
            str: stderr of the executed command.

        """
        process = Popen(
            cmd, stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True
        )
        stdout, stderr = process.communicate()

        return stdout, stderr

    @classmethod
    def get_image_for_container_id(
        cls, server_ip, container_id, logging_module=logging
    ):
        cmd = cls._build_ssh_command(
            server_ip,
            "sudo docker inspect -f {{.Config.Image}} " + container_id,
            force_tty=False,
        )
        stdout, stderr = cls.run_shell_command(cmd)
        if stderr:
            logging_module.warning(
                f"Received stderr from docker inspect command. Additional information: {stderr}"
            )
        res = stdout or ""
        return res.strip()

    @classmethod
    def get_integration_image(cls, integration_config):
        """Returns docker image of integration that was configured using rest api call via demisto_client

        Args:
            integration_config (dict): Integration config that included script section.
        Returns:
            list: List that includes integration docker image name. If no docker image was found,
                  default python2 and python3 images are returned.

        """
        integration_script = (
            integration_config.get("configuration", {}).get("integrationScript", {})
            or {}
        )
        integration_type = integration_script.get("type")
        docker_image = integration_script.get("dockerImage")

        if integration_type == cls.JAVASCRIPT_INTEGRATION_TYPE:
            return None
        elif (
            integration_type
            in {cls.PYTHON_INTEGRATION_TYPE, cls.POWERSHELL_INTEGRATION_TYPE}
            and docker_image
        ):
            return [docker_image]
        else:
            return [cls.DEFAULT_PYTHON2_IMAGE, cls.DEFAULT_PYTHON3_IMAGE]

    @classmethod
    def docker_stats(cls, server_ip, docker_images, logging_module=logging):
        """Executes docker stats command and greps all containers with prefix of docker images names.

        Args:
            server_ip (str): Remote machine ip to connect using ssh.
            docker_images (set): Set of docker images to check their resource usage.
            logging_module: The logging module that should be used.

        Returns:
            list: List of dictionaries with parsed container memory statistics.
        """
        cmd = cls._build_stats_cmd(server_ip, docker_images)
        stdout, stderr = cls.run_shell_command(cmd)

        if stderr:
            logging_module.warning(
                f"Failed running docker stats command. Additional information: {stderr}"
            )
            return []

        return cls._parse_stats_result(stdout, logging_module)

    @classmethod
    def kill_container(cls, server_ip, container_name, logging_module):
        """Executes docker kill command on remote machine using ssh.

        Args:
            server_ip (str): The remote server ip address.
            container_name (str): The container name to kill
            logging_module: The logging module to use

        """
        cmd = cls._build_kill_cmd(server_ip, container_name)
        _, stderr = cls.run_shell_command(cmd)

        if stderr:
            logging_module.debug(
                f"Failed killing container: {container_name}\nAdditional information: {stderr}"
            )

    @classmethod
    def get_docker_pid_info(cls, server_ip, container_id, logging_module):
        """Executes docker exec ps command on remote machine using ssh.

        Args:
            server_ip (str): The remote server ip address.
            container_id (str): Docker container id.
            logging_module: The logging module to use

        Returns:
            str: output of executed command.
        """
        cmd = cls._build_pid_info_cmd(server_ip, container_id)
        stdout, stderr = cls.run_shell_command(cmd)

        if stderr:
            ignored_warning_message = f"Connection to {server_ip} closed"
            if ignored_warning_message not in stderr:
                logging_module.debug(
                    f"Failed getting pid info for container id: {container_id}.\n"
                    f"Additional information: {stderr}"
                )

        return stdout

    @classmethod
    def check_resource_usage(
        cls,
        server_url,
        docker_images,
        def_memory_threshold,
        def_pid_threshold,
        docker_thresholds,
        logging_module,
    ):
        """
        Executes docker stats command on remote machine and returns error message in case of exceeding threshold.

        Args:
            server_url (str): Target machine full url.
            docker_images (set): Set of docker images to check their resource usage.
            def_memory_threshold (int): Memory threshold of specific docker container, in Mib.
            def_pids_threshold (int): PIDs threshold of specific docker container, in Mib.
            docker_thresholds: thresholds per docker image
            logging_module: The logging module that should be used.

        Returns:
            str: The error message. Empty in case that resource check passed.

        """
        server_ip = server_url.lstrip("https://")
        containers_stats = cls.docker_stats(server_ip, docker_images, logging_module)
        error_message = ""

        for container_stat in containers_stats:
            failed_memory_test = False
            container_name = container_stat["container_name"]
            container_id = container_stat["container_id"]
            memory_usage = container_stat["memory_usage"]
            pids_usage = container_stat["pids"]
            image_full = cls.get_image_for_container_id(
                server_ip, container_id, logging_module
            )  # get full name (ex: demisto/slack:1.0.0.4978)
            image_name = image_full.split(":")[0]  # just the name such as demisto/slack

            memory_threshold = (
                docker_thresholds.get(image_full, {}).get("memory_threshold")
                or docker_thresholds.get(image_name, {}).get("memory_threshold")
                or def_memory_threshold
            )
            pid_threshold = (
                docker_thresholds.get(image_full, {}).get("pid_threshold")
                or docker_thresholds.get(image_name, {}).get("pid_threshold")
                or def_pid_threshold
            )
            logging_module.debug(
                f"Checking container: {container_name} "
                f"(image: {image_full}) for memory: {memory_threshold} pid: {pid_threshold} thresholds "
                f"with actual values: memory {memory_usage} pids: {pids_usage} ..."
            )
            if memory_usage > memory_threshold:
                error_message += (
                    "Failed docker resource test. Docker container {} exceeded the memory threshold, "
                    "configured: {} MiB and actual memory usage is {} MiB.\n"
                    "Fix container memory usage or add `memory_threshold` key to failed test "
                    "in conf.json with value that is greater than {}\n".format(
                        container_name, memory_threshold, memory_usage, memory_usage
                    )
                )
                failed_memory_test = True
            if pids_usage > pid_threshold:
                error_message += (
                    "Failed docker resource test. Docker container {} exceeded the pids threshold, "
                    "configured: {} and actual pid number is {}.\n"
                    "Fix container pid usage or add `pid_threshold` key to failed test "
                    "in conf.json with value that is greater than {}\n".format(
                        container_name, pid_threshold, pids_usage, pids_usage
                    )
                )
                additional_pid_info = cls.get_docker_pid_info(
                    server_ip, container_id, logging_module
                )
                if additional_pid_info:
                    error_message += (
                        f"Additional pid information:\n{additional_pid_info}"
                    )
                failed_memory_test = True

            if failed_memory_test:
                # killing current container in case of memory resource test failure
                cls.kill_container(server_ip, container_name, logging_module)

        return error_message
