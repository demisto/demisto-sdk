import os
import shutil
from content_parser import RepositoryParser
from datetime import datetime
from demisto_sdk.commands.lint.docker_helper import init_global_docker_client
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.content.content import Content

import docker


def parse_content() -> None:
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
                     'NEO4J_dbms_connector_http_advertised__address': '127.0.0.1:7474',
                     'NEO4J_dbms_connector_bolt_advertised__address': '127.0.0.1:7687',
                     'NEO4J_dbms_connector_bolt_listen__address': '0.0.0.0'},
        volumes={f'{git_path}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                 f'{git_path}/neo4j/logs': {'bind': '/logs', 'mode': 'rw'},
                 f'{git_path}/neo4j/plugins': {'bind': '/plugins', 'mode': 'rw'},
                 f'{git_path}/neo4j/import': {'bind': '/var/lib/neo4j/import', 'mode': 'rw'}},

    )
    now_1 = datetime.now()
    RepositoryParser(git_path).run()
    now_2 = datetime.now()
    print(f'Finished updating in {(now_2 - now_1).total_seconds()} seconds')


def dump():
    """docker run --interactive --tty --rm \
   --volume=$HOME/neo4j/data:/data \  
   --volume=$HOME/neo4j/backups:/backups \  
   neo4j/neo4j-admin:4.4.9 \
neo4j-admin dump --database=neo4j --to=/backups/<dump-name>.dump
"""
    git_path = GitUtil(Content.git()).git_path()
    docker_client = docker.from_env()
    try:
        docker_client.containers.get('neo4j_dump').remove(force=True)
    except Exception as e:
        print('Container does not exist')

    docker_client.containers.run(image='neo4j/neo4j-admin:4.4.9',
                                 remove=True,
                                 volumes={f'{git_path}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                                          f'{git_path}/neo4j/backups': {'bind': '/backups', 'mode': 'rw'}},

                                 command='neo4j-admin dump --database=neo4j --to=/backups/content_graph.db'
                                 )


def load():
    """
    docker run --interactive --tty --rm \
    --volume=$HOME/neo4j/data:/data \ 
    --volume=$HOME/neo4j/backups:/backups \ 
    neo4j/neo4j-admin:4.4.9 \
neo4j-admin load --database=neo4j --from=/backups/<dump-name>.dump

    """
    git_path = GitUtil(Content.git()).git_path()
    docker_client = docker.from_env()
    try:
        docker_client.containers.get('neo4j_load').remove(force=True)
    except Exception as e:
        print('Container does not exist')
    # remove neo4j folder
    shutil.rmtree(f'{git_path}/neo4j/data')
    docker_client.containers.run(image='neo4j/neo4j-admin:4.4.9',
                                 name='neo4j_load',
                                 remove=True,
                                 volumes={f'{git_path}/neo4j/data': {'bind': '/data', 'mode': 'rw'},
                                          f'{git_path}/neo4j/backups': {'bind': '/backups', 'mode': 'rw'}},

                                 command='neo4j-admin load --database=neo4j --from=/backups/graph.dump'
                                 )


if __name__ == '__main__':
    # load()
    parse_content()
    dump()
    load()
