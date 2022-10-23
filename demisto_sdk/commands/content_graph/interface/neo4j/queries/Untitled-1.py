# %%
from itertools import groupby
import neo4j
from demisto_sdk.commands.content_graph.common import NEO4J_DATABASE_URL, NEO4J_USERNAME, NEO4J_PASSWORD, ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import content_type_to_model
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack

from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import Neo4jContentGraphInterface
import timeit


# def get_node(tx: neo4j.Transaction):
#     query = """
#     match (n:Pack)
#     return  n
#     """
#     return nodes_to_pack(tx, tx.run(query))


# def nodes_to_pack(tx: neo4j.Transaction, result: neo4j.Result):
#     query = f"""
#     UNWIND $nodes as nid
#     MATCH (n:{ContentType.PACK})-[:{RelationshipType.IN_PACK}*0..1]-(content_item:{ContentType.BASE_CONTENT})
#     WHERE id(n) = nid
#     OPTIONAL MATCH (content_item)-[r:{RelationshipType.HAS_COMMAND}]->(cmd)
#     WITH content_item, [val in collect({{name: cmd.name, description: r.description, deprecated: r.deprecated}}) WHERE val.name is not null] as commands, n
#     WITH content_item{{.*, commands: commands}}, n
#     WITH [val in collect(content_item) WHERE val.content_type <> '{ContentType.PACK}'] as content_items, n
#     RETURN n{{.*, content_items: content_items, element_id: id(n)}}
#     """
#     nodes = [int(item['n'].element_id) for item in result]
#     results = tx.run(query, nodes=nodes)
#     packs = []
#     for item in results:
#         pack = item.get('n')
#         packs.append(Pack.parse_obj(pack))
#     print()


# def nodes_to_integrations(tx: neo4j.Transaction, result: neo4j.Result):
#     query = f"""
#     UNWIND $nodes as nid
#     MATCH (n:{ContentType.INTEGRATION})-[r:{RelationshipType.HAS_COMMAND}]-(cmd:{ContentType.COMMAND})
#     WHERE id(n) = nid AND n <> cmd
#     with n, collect({{name: cmd.name, description: r.description, deprecated: r.deprecated}}) as commands
#     RETURN n{{.*, commands: commands, element_id: id(n)}}
#     """
#     nodes = [int(item['n'].element_id) for item in result]
#     results = tx.run(query, nodes=nodes)
#     integrations = []
#     for item in results:
#         pack = item.get('n')
#         integrations.append(Integration.parse_obj(pack))
#     print()


# def parse_result(result: neo4j.Result):
#     items = list(result)


# driver: neo4j.Neo4jDriver = neo4j.GraphDatabase.driver(
#     NEO4J_DATABASE_URL,
#     auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
# )

# with driver.session() as session:
#     s = timeit.default_timer()
#     session.execute_read(get_node)
#     print(f'time = {timeit.default_timer() - s}')
# with Neo4jContentGraphInterface() as f:
#     pass

with Neo4jContentGraphInterface() as interface:
    # packs = interface.search_nodes(
    #     marketplace='xsoar',
    #     content_type=ContentType.PACK)
    # integrations = interface.search_nodes(
    #     marketplace='xsoar',
    #     content_type=ContentType.INTEGRATION)

    connected = interface.get_connected_nodes_by_relationship_type(
        'xsoar',
        RelationshipType.USES,
        content_type_from=ContentType.SCRIPT,
        content_type_to=ContentType.SCRIPT,
        recursive=True
    )
print(connected[0])