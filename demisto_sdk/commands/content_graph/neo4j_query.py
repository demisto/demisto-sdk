
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel


class Neo4jQuery:
    @staticmethod
    def create_nodes_indexes() -> List[str]:
        queries: List[str] = []
        template = 'CREATE INDEX ON :{label}({props})'
        constraints = ContentTypes.props_indexes()
        for label, props in constraints.items():
            props = ', '.join(props)
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def create_nodes_props_uniqueness_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE {props} IS UNIQUE'
        constraints = ContentTypes.props_uniqueness_constraints()
        for label, props in constraints.items():
            props = ', '.join([f'n.{p}' for p in props])
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def create_nodes_props_existence_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL'
        constraints = ContentTypes.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    @staticmethod
    def create_relationships_props_existence_constraints() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:{label}]-() REQUIRE r.{prop} IS NOT NULL'
        constraints = Rel.props_existence_constraints()
        for label, props in constraints.items():
            for prop in props:
                queries.append(template.format(label=label, prop=prop))
        return queries

    @staticmethod
    def create_nodes(content_type: ContentTypes) -> str:
        return f"""
            UNWIND $data AS node_data
            CREATE (n:{Neo4jQuery.labels_of(content_type)}{{node_id: node_data.node_id}}) SET n += node_data
        """

    @staticmethod
    def create_has_command_relationships_from_csv() -> str:
        """
        Since commands nodes might be already created when creating the USES_COMMAND_OR_SCRIPT relationships
        but we haven't yet catagorized them as commands, we search them by their `id` property
        When they are created/found, we set their node_id and labels.
        """
        return f"""
            UNWIND $data AS rel_data
            MATCH (a:{ContentTypes.INTEGRATION}{{node_id: rel_data.from}})
            MERGE (b:{Neo4jQuery.labels_of(ContentTypes.COMMAND)}{{
                node_id: "{ContentTypes.COMMAND}:" + rel_data.to,
                id: rel_data.to
            }})
            ON CREATE
                SET b.in_xsoar = toBoolean(rel_data.in_xsoar),
                    b.in_xsiam = toBoolean(rel_data.in_xsiam)
            ON MATCH
                SET b.in_xsoar = CASE WHEN toBoolean(b.in_xsoar) OR toBoolean(rel_data.in_xsoar) THEN "True"
                                 ELSE "False" END,
                    b.in_xsiam = CASE WHEN toBoolean(b.in_xsiam) OR toBoolean(rel_data.in_xsiam) THEN "True"
                                 ELSE "False" END
            MERGE (a)-[r:{Rel.HAS_COMMAND}{{deprecated: toBoolean(rel_data.deprecated)}}]->(b)
        """

    @staticmethod
    def create_uses_relationships_from_csv() -> str:
        """
        We search both source and target nodes by their `node_id` properties.
        Note: the FOR EACH statements are a workaround for Cypher not supporting IF statements.
        """
        query = f"""
            UNWIND $data AS rel_data
            MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}})
        """
        for content_type in ContentTypes.content_items():
            query += f"""
            FOREACH (_ IN CASE WHEN rel_data.target_label = "{content_type}" THEN [1] ELSE [] END|
                MERGE (b:{Neo4jQuery.labels_of(content_type)}{{
                    node_id: "{content_type}:" + rel_data.to,
                    id: rel_data.to
                }})
                MERGE (a)-[r:{Rel.USES}{{is_source_deprecated: toBoolean(a.deprecated)}}]->(b)
                ON CREATE
                    SET r.mandatorily = toBoolean(rel_data.mandatorily)
                ON MATCH
                    SET r.mandatorily = r.mandatorily OR toBoolean(rel_data.mandatorily)
            )
            """
        return query

    @staticmethod
    def create_uses_command_or_script_relationships_from_csv() -> str:
        """
        When creating these relationships, since the target nodes types are not known (either Command or Script),
        we are using only the `id` property to search/create it. If created, this is a Command (because script nodes
        were already created).
        """
        return f"""
            UNWIND $data AS rel_data
            MATCH (a:{ContentTypes.SCRIPT}{{node_id: rel_data.from}})
            MERGE (b:{ContentTypes.COMMAND_OR_SCRIPT}{{id: rel_data.to}})
            ON CREATE
                SET b:{Neo4jQuery.labels_of(ContentTypes.COMMAND)}, b.node_id = "{ContentTypes.COMMAND}:" + rel_data.to

            MERGE (a)-[r:{Rel.USES}{{is_source_deprecated: toBoolean(a.deprecated)}}]->(b)
            ON CREATE
                SET r.mandatorily = toBoolean(rel_data.mandatorily)
            ON MATCH
                SET r.mandatorily = r.mandatorily OR toBoolean(rel_data.mandatorily)
        """

    @staticmethod
    def create_tested_by_relationships_from_csv() -> str:
        return f"""
            UNWIND $data AS rel_data
            MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}})
            MERGE (b:{ContentTypes.TEST_PLAYBOOK}{{
                node_id: "{ContentTypes.TEST_PLAYBOOK}:" + rel_data.to,
                id: rel_data.to
            }})
            MERGE (a)-[r:{Rel.TESTED_BY}{{is_source_deprecated: toBoolean(a.deprecated)}}]->(b)
        """

    @staticmethod
    def create_relationships(rel_type: Rel) -> str:
        if rel_type == Rel.USES:
            return Neo4jQuery.create_uses_relationships_from_csv()
        if rel_type == Rel.USES_COMMAND_OR_SCRIPT:
            return Neo4jQuery.create_uses_command_or_script_relationships_from_csv()
        if rel_type == Rel.HAS_COMMAND:
            return Neo4jQuery.create_has_command_relationships_from_csv()
        if rel_type == Rel.TESTED_BY:
            return Neo4jQuery.create_tested_by_relationships_from_csv()

        # default
        return f"""
            UNWIND $data AS rel_data
            MATCH (a:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.from}})
            MERGE (b:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.to}})
            MERGE (a)-[r:{rel_type}]->(b)
        """

    @staticmethod
    def update_in_xsoar_property() -> str:
        # todo: maybe need to run this in a while loop until no changes?
        return f"""
            MATCH (a:{ContentTypes.BASE_CONTENT}{{in_xsoar: "True"}})
                -[:{Rel.USES}*{{mandatorily: true}}]->
                    (b:{ContentTypes.BASE_CONTENT}{{in_xsoar: "False"}}),
            (b)-[:{Rel.IN_PACK}]->(p)
            WHERE NOT p.id IN ["DeprecatedContent", "NonSupported"]
            SET a.in_xsoar = "False"
        """

    @staticmethod
    def update_in_xsiam_property() -> str:
        # todo: maybe need to run this in a while loop until no changes?
        return f"""
            MATCH (a:{ContentTypes.BASE_CONTENT}{{in_xsiam: "True"}})
                -[:{Rel.USES}*{{mandatorily: true}}]->
                    (b:{ContentTypes.BASE_CONTENT}{{in_xsiam: "False"}}),
            (b)-[:{Rel.IN_PACK}]->(p)
            WHERE NOT p.id IN ["DeprecatedContent", "NonSupported"]
            SET a.in_xsiam = "False"
        """

    @staticmethod
    def create_depends_on_in_xsoar() -> str:
        return f"""
            MATCH (a)-[:{Rel.USES}]->(b), (a)-[:{Rel.IN_PACK}]->(p1), (b)-[:{Rel.IN_PACK}]->(p2)
            WHERE a.in_xsoar = "True" AND b.in_xsoar = "True"
            AND p1.node_id <> p2.node_id
            AND NOT p1.name CONTAINS 'Common' AND NOT p2.name CONTAINS 'Common'
            AND NOT p1.name CONTAINS 'Deprecated' AND NOT p2.name CONTAINS 'Deprecated'
            AND  p1.name <> 'Base' AND  p2.name <> 'Base'
            WITH p1, p2
            MERGE (p1)-[r:DEPENDS_ON_IN_XSOAR]->(p2)
            RETURN *
        """

    @staticmethod
    def create_depends_on_in_xsiam() -> str:
        return f"""
            MATCH (a)-[:{Rel.USES}]->(b), (a)-[:{Rel.IN_PACK}]->(p1), (b)-[:{Rel.IN_PACK}]->(p2)
            WHERE a.in_xsiam = "True" AND b.in_xsiam = "True"
            AND p1.node_id <> p2.node_id
            AND NOT p1.name CONTAINS 'Common' AND NOT p2.name CONTAINS 'Common'
            AND NOT p1.name CONTAINS 'Deprecated' AND NOT p2.name CONTAINS 'Deprecated'
            AND  p1.name <> 'Base' AND  p2.name <> 'Base'
            WITH p1, p2
            MERGE (p1)-[r:DEPENDS_ON_IN_XSIAM]->(p2)
            RETURN *
        """

    @staticmethod
    def export_nodes_by_type(content_type: ContentTypes) -> None:
        filename = f'{content_type}.csv'
        return (
            f'MATCH (n:{content_type}) '
            'WITH collect(n) AS nodes '
            f'CALL apoc.export.csv.data(nodes, [], "{filename}", {{}}) '
            'YIELD file, nodes, done '
            'RETURN file, nodes, done'
        )

    @staticmethod
    def export_relationships_by_type(rel_type: Rel) -> None:
        filename = f'{rel_type}.csv'
        return (
            f'MATCH ()-[n:{rel_type}]->() '
            'WITH collect(n) AS rels '
            f'CALL apoc.export.csv.data([], rels, "{filename}", {{}}) '
            'YIELD done '
            'RETURN done'
        )

    @staticmethod
    def labels_of(content_type: ContentTypes) -> str:
        return ':'.join(content_type.labels)
