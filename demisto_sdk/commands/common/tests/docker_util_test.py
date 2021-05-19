import platform
import uuid

import pytest
from demisto_sdk.commands.common.docker_util import *
from demisto_sdk.commands.common.legacy_git_tools import git_path

FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
running_inside_docker = pytest.mark.skipif(platform.system().lower() == 'linux',
                                           reason="probably running in docker and this test requires a connection to the docker deamon")


def create():
    return ContainerRunner('demisto/python3', str(uuid.uuid4()))


@running_inside_docker
class TestContainerRunner:

    class TestExecCommand:

        def setup_class(self):
            self.container_runner = create()

        data_test_exec_status = [
            ('echo test', 0),
            ('blabla blabla', 127),
        ]

        @pytest.mark.parametrize('command, status', data_test_exec_status)
        def test_exec_status(self, command, status):
            assert self.container_runner.exec(command=command)['StatusCode'] == status

        data_test_exec_outputs = [
            ('echo test', b'test\n'),
            ('pwd', b'/\n')
        ]

        @pytest.mark.parametrize('command, outputs', data_test_exec_outputs)
        def test_exec_outputs(self, command, outputs):
            assert self.container_runner.exec(command=command)['Outputs'] == outputs

        data_test_exec_errors = [
            ('echo test', None),
            (
                'cd bla/bla',
                {
                    'Message':
                        'OCI runtime create failed: container_linux.go:367: starting container process caused:'
                        ' exec: "cd": executable file not found in $PATH: unknown'
                }
            )
        ]

        @pytest.mark.parametrize('command, error', data_test_exec_errors)
        def test_exec_errors(self, command, error):
            assert self.container_runner.exec(command=command)['Error'] == error

        def test_exec_committed(self):
            self.container_runner.exec('echo test')
            file_name = 'just_a_txt_file.txt'
            file_full_path = os.path.join(FILES_PATH, file_name)
            self.container_runner.exec(f'mkdir -p {FILES_PATH}')
            with open(file_full_path, 'rb') as _file:
                self.container_runner.import_file(_file.read(), file_full_path)
            self.container_runner.exec('echo test')
            assert self.container_runner.container.image != self.container_runner.container.client.images.get(
                self.container_runner._base_image_name)

    class TestImportFile:
        def setup_class(self):
            self.container_runner = create()

        @pytest.mark.parametrize('file_name', ['just_a_txt_file.txt'])
        def test_import_file(self, file_name):
            file_path = FILES_PATH
            file_full_path = os.path.join(FILES_PATH, file_name)
            self.container_runner.exec(f'mkdir -p {file_path}')
            with open(file_full_path, 'rb') as _file:
                data = _file.read()
            self.container_runner.import_file(data, file_full_path)
            assert self.container_runner.export_file(file_full_path) == data

    class TestExportFile:
        def setup_class(self):
            self.container_runner = create()

        @pytest.mark.parametrize('file_name', ['just_a_txt_file.txt'])
        def test_export_file(self, file_name):
            file_full_path = os.path.join(FILES_PATH, file_name)
            self.container_runner.exec(f'mkdir -p {FILES_PATH}')
            with open(file_full_path, 'rb') as _file:
                data = _file.read()
            self.container_runner.import_file(data, file_full_path)
            assert self.container_runner.export_file(file_full_path) == data

    class TestContainerCreation:
        def setup_class(self):
            self.container_runner = create()

        def test_with_container(self, mocker):
            assert self.container_runner._container_obj is None
            caller = mocker.patch.object(self.container_runner, '_create_container')
            self.container_runner.container
            assert caller.called.numerator == 1

        def test_with_create_container(self):
            self.container_runner.container
            assert self.container_runner._container_obj is not None
            self.container_runner._create_container()

    class TestRemoveContainerAndImages:
        def setup_class(self):
            self.container_runner = create()

        def test_remove_container(self):
            self.container_runner.exec('echo test')
            container_id = self.container_runner.container.id
            self.container_runner.remove_container()
            with pytest.raises(docker.errors.NotFound):
                self.container_runner.container.client.containers.get(container_id)

        def test_remove_images(self):
            self.container_runner.exec('echo test1')
            self.container_runner.exec('echo test2')
            self.container_runner.exec('echo test3')
            image = self.container_runner._image_name
            self.container_runner.remove_images()
            with pytest.raises(docker.errors.ImageNotFound):
                self.container_runner.container.client.images.get(image)


@running_inside_docker
class TestDockerTools:

    class TestRemoveContainer:

        @staticmethod
        def remove(name):
            try:
                DockerTools.remove_container(name)
            except:     # noqa: E722
                pass

        @pytest.mark.parametrize('container_name', ['test_remove_running_container'])
        def test_remove_running_container(self, container_name):
            self.remove(container_name)
            client.containers.run('demisto/python3', name=container_name, command='sleep 60', detach=True)
            DockerTools.remove_container(container_name, ignore_container_not_found=False, force=True)
            with pytest.raises(docker.errors.NotFound):
                client.containers.get(container_name)

        @pytest.mark.parametrize('container_name', ['test_remove_existing_container'])
        def test_remove_existing_container(self, container_name):
            self.remove(container_name)
            client.containers.create('demisto/python3', name=container_name, command='sleep 60', detach=True)
            DockerTools.remove_container(container_name, ignore_container_not_found=False)
            with pytest.raises(docker.errors.NotFound):
                client.containers.get(container_name)

        @pytest.mark.parametrize('container_name', ['test_remove_non_existing_container'])
        def test_remove_non_existing_container(self, container_name):
            self.remove(container_name)
            DockerTools.remove_container(container_name, ignore_container_not_found=True)

    class TestRemoveImages:

        def setup(self):
            self.to_delete = []
            for image in self.images:
                container = ContainerRunner(image=image, container_name=str(uuid.uuid4()))
                container.import_file(b'just_something', 'just_something.txt')
                image_to_save = container.container.commit()
                self.to_delete.append(image_to_save.id)
                image_to_save.tag(image, self.tag)
                self.to_delete.append(image_to_save.id)

        def teardown(self):
            for image_id in self.to_delete:
                try:
                    client.images.remove(image_id)
                except:     # noqa: E722
                    pass

        images = ['demisto/python3']
        tag = 'test-docker'

        @pytest.mark.parametrize('image_name', images)
        def test_remove_running_image(self, image_name):
            image_name = f'{image_name}:{self.tag}'
            container = client.containers.run(image=image_name, command='sleep 60', detach=True)
            DockerTools.remove_image(image_name, ignore_image_not_found=False, force=True)
            self.to_delete.append(container.image.id)
            container.remove(force=True)
            with pytest.raises(docker.errors.ImageNotFound):
                client.images.get(image_name)

        @pytest.mark.parametrize('image_name', images)
        def test_remove_existing_image(self, image_name):
            image_name = f'{image_name}:{self.tag}'
            client.containers.create(image=image_name).remove()
            DockerTools.remove_image(image_name, ignore_image_not_found=False)
            with pytest.raises(docker.errors.ImageNotFound):
                client.images.get(image_name)


class TestHelperFunctions:

    @pytest.mark.parametrize('data', [b'test'])
    def test_create_tar_info(self, data):
        tar_info = create_tar_info(name='test.txt', file_bytes=data)
        file_obj = tar_info['fileobj']
        tar_info = tar_info['tarinfo']
        assert file_obj.read() == data
        assert tar_info.size == len(data)
        assert tar_info.name == 'test.txt'
