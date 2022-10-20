# %%
import neo4j
from demisto_sdk.commands.content_graph.common import NEO4J_DATABASE_URL, NEO4J_USERNAME, NEO4J_PASSWORD, ContentType, Relationship
from demisto_sdk.commands.content_graph.objects.base_content import content_type_to_model
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import Neo4jContentGraphInterface

def test():
    driver = neo4j.GraphDatabase.driver(
        NEO4J_DATABASE_URL,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    )
    with driver.session() as session:
        session.read_transaction(parse)


def parse(tx: neo4j.Transaction):
    query = f"""
    match (n:BaseContent{{object_id:"QRadar"}})
    return n
    """
    result = tx.run(query)
    nodes = [node.get('n') for node in result.data()]
    content_types = {node.get('content_type') for node in nodes}
    if ContentType.INTEGRATION in content_types:
        parse_integrations(tx, list(filter(lambda x: x.get('content_type') == ContentType.INTEGRATION, nodes)))

    if ContentType.PACK in content_types:
        parse_packs(tx, list(filter(lambda x: x.get('content_type') == ContentType.PACK, nodes)))
    print()


def parse_integrations(tx: neo4j.Transaction, integrations):
    query = f"""
    UNWIND $integrations_id as integration_id
    MATCH (i:Integration{{object_id: integration_id}})-[r:HAS_COMMAND]->(c:Command)
    return i, collect({{name: c.name, description: r.description, deprecated: r.deprecated}}) as commands
    """
    data = tx.run(query, integrations_id=[integration.get('object_id') for integration in integrations]).data()
    integrations = [Integration.parse_obj(dict(item.get('i'), commands=item.get('commands'))) for item in data]


def parse_packs(tx: neo4j.Transaction, packs):
    query = f"""
    UNWIND $packs_id as pack_id
    MATCH (p:Pack{{object_id: pack_id}})<-[:{Relationship.IN_PACK}]-(c:{ContentType.BASE_CONTENT})
    return p, collect(c) as content_items
    """
    data = tx.run(query, packs_id=[pack.get('object_id') for pack in packs]).data()
    integrations = []
    for item in data:
        pack = item.get('pack')
        content_items = item.get('content_items')
        for content_item in content_items:
            if content_item.get('content_type') == ContentType.INTEGRATION:
                integrations.append(content_item)
                continue
            
            


def helper(node, node_to_add):
    return f"""
    optional match (cmd1)<-[r_cmd1:{Relationship.HAS_COMMAND}]-({node})
    optional match (content_item)-[:{Relationship.IN_PACK}]->({node})
    optional match (cmd2)<-[r_cmd2:{Relationship.HAS_COMMAND}]-(content_item)
    with collect({{name: cmd2.name, description: r_cmd2.description, deprecated: r_cmd2.deprecated}}) as commands_inner, cmd1, r_cmd1, content_item, {node}, {node_to_add}
    with collect({{name: cmd1.name, description: r_cmd1.description, deprecated: r_cmd1.deprecated}}) as commands, content_item, commands_inner, {node}, {node_to_add}
    with content_item{{.*, commands:commands_inner}} as content_items, commands, content_item, {node}, {node_to_add}
    with collect(content_item) as content_items, commands, {node}, {node_to_add}

    with {node}{{.*, content_items: content_items, commands: commands}} as {node}, {node_to_add}
    """


def get_graph(tx: neo4j.Transaction):
    query = f"""
    MATCH (p:{ContentType.BASE_CONTENT}{{object_id: 'QRadar'}})-[r:{Relationship.IN_PACK}|{Relationship.HAS_COMMAND}*..2]-(n)
    RETURN p, collect(r) as rels, collect(n) as c
    """
    result = []
    run = tx.run(query=query)
    data = run.values()
    graph = run.grgraph()
    # for rel in graph.relationships:
    #     start_node_properties = dict(rel.start_node.items())
    #     end_node_properties = dict(rel.end_node.items())
    #     if rel.type == Relationship.IN_PACK:
    #         end_node_properties.setdefault('content_items', {}).setdefault(start_node_properties.get('content_type'), []).append(end_node_properties)
    #         nodes.add(end_node_properties)
    #     if rel.type == Relationship.HAS_COMMAND:
    #         start_node_properties.setdefault('commands', []).append(end_node_properties)
    #         nodes.add(start_node_properties)
    # for node in nodes:
    #     result.append(dict(node.items()))
    return graph


woriking_query = """
match (n:BaseContent {object_id: "QRadar"})
optional match (cmd1)<-[r_cmd1:HAS_COMMAND]-(n)
optional match (content_item)-[:IN_PACK]->(n)
optional match (cmd2)<-[r_cmd2:HAS_COMMAND]-(content_item)
with collect({name: cmd2.name, description: r_cmd2.description, deprecated: r_cmd2.deprecated}) as commands_inner, cmd1, r_cmd1, n, content_item
with collect({name: cmd1.name, description: r_cmd1.description, deprecated: r_cmd1.deprecated}) as commands, n, content_item, commands_inner
with content_item{.*, commands:commands_inner} as content_items, n, commands, content_item
with collect(content_item) as content_items, n, commands
return n{.*, content_items: content_items, commands: commands}
"""
test()
