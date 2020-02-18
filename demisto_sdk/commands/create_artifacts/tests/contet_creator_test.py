import filecmp
from demisto_sdk.commands.create_artifacts.content_creator import *


def test_copy_dir_files():
    current_dir = os.path.dirname(__file__)
    content_repo_example = os.path.join(current_dir, '/test_files/content_repo_example')

    content_bundle_full_path = f'{current_dir}/test_files/content_repo_example/content_bundle'
    scripts_full_path = f'{current_dir}/test_files/content_repo_example/Scripts/'

    content_creator = ContentCreator(artifacts_path=content_repo_example, content_version='2.5.0',
                                     content_bundle_path='test_files/content_repo_example/content_bundle',
                                     packs_bundle_path='packs_bundle',
                                     test_bundle_path='test_bundle', preserve_bundles=False)

    content_creator.copy_dir_files(scripts_full_path, content_bundle_full_path)

    assert filecmp.cmp(f'{scripts_full_path}/script-Sleep.yml',
                       f'{content_bundle_full_path}/script-Sleep.yml')

    # delete all files in the content_bundle
    for filename in os.listdir(content_bundle_full_path):
        file_path = os.path.join(content_bundle_full_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as err:
            print('Failed to delete %s. Reason: %s' % (file_path, err))
