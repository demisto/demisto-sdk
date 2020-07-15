from wcmatch.pathlib import Path, NODIR
from shutil import copyfile, make_archive
from multiprocessing import Pool
from os import cpu_count
from content import Content


CONTNET_NEW = 'content_new'
CONTENT_TEST = 'content_test'
CONTENT_PACK = 'content_pack'
LATEST_SUPPORTED_VERSION = '4.1.0'


class ContentArtifacts:
    def __init__(self, artifacts_path: str, content_version: str, suffix: str, preserve_bundles: bool,
                 no_update_commonserver: bool, no_fromversion: bool, packs: bool):
        self._suffix = suffix
        self._artifacts_path = Path(artifacts_path)
        self._content_version = content_version
        self._predserve_bunles = preserve_bundles
        self._no_update_commonserver = no_update_commonserver
        self._no_fromversion = no_fromversion
        self._packs = packs
        self._contnet_new_path = self._artifacts_path / CONTNET_NEW
        self._contnet_test_path = self._artifacts_path / CONTENT_TEST
        self._contnet_packs_path = self._artifacts_path / CONTENT_PACK

    def create_content_artifact(self) -> int:
        content = Content.from_cwd()
        import time
        start = time.time()
        self._create_content_test_artifact(content)
        self._create_content_pack_artifact(content)
        self._create_content_new_artifact()
        self._compress_artifacts()
        print(f"Total seconds {time.time() - start}")

    def _create_content_test_artifact(self, content: Content) -> None:
        self._contnet_test_path.mkdir(parents=True, exist_ok=True)
        # Collect TestPlaybook from content/TestPlaybooks
        for test_playbook in content.test_playbooks:
            test_playbook.dump(self._contnet_test_path)
        # Iterate over all content/Packs
        for pack in content.packs.values():
            # Collect all TestPlaybooks from content/Packs/<Pack-name>/TestPlaybooks
            for test_playbook in pack.test_playbooks:
                test_playbook.dump(self._contnet_test_path)

    @staticmethod
    def _hook(self):
        pass

    def _create_content_pack_artifact(self, content: Content) -> None:
        self._contnet_packs_path.mkdir(parents=True, exist_ok=True)
        pool = Pool(cpu_count())
        for pack in content.packs.values():
            pool.apply_async(func=pack.dump,
                             kwds={
                                 'dest': self._contnet_packs_path,
                                 'secrets_ignore': False,
                                 'change_log': False,
                                 'readme': False
                             })
        pool.close()
        pool.join()

    def _create_content_new_artifact(self) -> None:
        self._contnet_new_path.mkdir(parents=True, exist_ok=True)
        for file in self._contnet_packs_path.rglob("*", flags=NODIR):
            copyfile(file, self._contnet_new_path / file.name)

    def _compress_artifacts(self) -> None:
        pool = Pool(cpu_count())
        for artifact in [self._contnet_test_path, self._contnet_new_path, self._contnet_packs_path]:
            make_archive(artifact, 'zip', artifact)
        pool.close()
        pool.join()
