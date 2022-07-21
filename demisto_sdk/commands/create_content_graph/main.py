import os
from content_parser import RepositoryParser
from datetime import datetime
from demisto_sdk.commands.lint.docker_helper import init_global_docker_client
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content

import docker

def main() -> None:
    git_path = GitUtil(Content.git()).git_path()
    print('Starting...')

    docker_client = docker.from_env()
    try:
        container = docker_client.containers.get('testneo4j')
        container.remove(force=True)
    except Exception as e:
        print('Container does not exist')
        pass
    container = docker_client.containers.run(
        name='testneo4j',
        image='neo4j:latest',
        detach=True,
        ports={'7474': '7474',
               '7687': '7687',
               },
        environment={'NEO4J_AUTH': 'neo4j/test',
                     'NEO4J_dbms_connector_http_advertised__address': 'localhost:7474',
                     'NEO4J_dbms_connector_bolt_advertised__address': 'localhost:7687',
                     'NEO4J_dbms_connector_bolt_listen__address': '0.0.0.0'},
        volumes={f'{os.getenv("CONTENT")}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                 f'{os.getenv("CONTENT")}/neo4j/logs': {'bind': '/logs', 'mode': 'rw'},
                 f'{os.getenv("CONTENT")}/neo4j/plugins': {'bind': '/plugins', 'mode': 'rw'},
                 f'{os.getenv("CONTENT")}/neo4j/import': {'bind': '/var/lib/neo4j/import', 'mode': 'rw'}},

    )
    now_1 = datetime.now()
    RepositoryParser(git_path).run()
    now_2 = datetime.now()
    print(f'Finished updating in {(now_2 - now_1).total_seconds()} seconds')


if __name__ == '__main__':
    main()
