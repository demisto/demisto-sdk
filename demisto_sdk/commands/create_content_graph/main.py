from content_parser import RepositoryParser
from datetime import datetime

REPO_PATH = '/Users/dtavori/dev/demisto/content/'


def main() -> None:
    print(f'Starting...')
    now_1 = datetime.now()
    RepositoryParser(REPO_PATH).run()
    now_2 = datetime.now()
    print(f'Finished updating in {(now_2 - now_1).total_seconds()} seconds')
    

if __name__ == '__main__':
    main()

