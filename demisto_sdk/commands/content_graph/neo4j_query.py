
from typing import List

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel


IGNORED_PACKS_IN_DEPENDENCY_CALC = ['NonSupported', 'Base', 'ApiModules']

class Neo4jQuery:
    @staticmethod
    def create_nodes_indexes() -> List[str]:
        queries: List[str] = []
        template = 'CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON ({props})'
        constraints = ContentTypes.props_indexes()
        for label, props in constraints.items():
            props = ', '.join([f'n.{p}' for p in props])
            queries.append(template.format(label=label, props=props))
        return queries

    @staticmethod
    def create_node_keys() -> List[str]:
        queries: List[str] = []
        template = 'CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE ({props}) IS NODE KEY'
        constraints = ContentTypes.node_key_constraints()
        for label, props in constraints.items():
            props = ', '.join([f'n.{p}' for p in props])
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
            CREATE (n:{Neo4jQuery.labels_of(content_type)}{{id: node_data.id}})
            SET n += node_data
        """

    @staticmethod
    def create_has_command_relationships() -> str:
        # this must be the first rel query to execute!
        return f"""
            UNWIND $data AS rel_data
            MATCH (integration:{Neo4jQuery.labels_of(ContentTypes.INTEGRATION)}{{
                node_id: rel_data.source_node_id,
                fromversion: rel_data.source_fromversion,
                marketplaces: rel_data.source_marketplaces
            }})
            MERGE (cmd:{Neo4jQuery.labels_of(ContentTypes.COMMAND)}{{
                node_id: "{ContentTypes.COMMAND}:" + rel_data.target,
                id: rel_data.target
            }})
            ON CREATE
                SET cmd.marketplaces = rel_data.source_marketplaces
            ON MATCH
                SET cmd.marketplaces = REDUCE(
                    marketplaces = cmd.marketplaces, mp IN rel_data.source_marketplaces |
                    CASE WHEN NOT mp IN cmd.marketplaces THEN marketplaces + mp ELSE marketplaces END
                )
            MERGE (integration)-[r:{Rel.HAS_COMMAND}{{deprecated: rel_data.deprecated}}]->(cmd)
        """

    @staticmethod
    def create_uses_relationships(target_type: ContentTypes) -> str:
        """
        Args:
            target_type (ContentTypes): If node_id is known, target type is BaseContent.
                Otherwise, a more specific ContentType, E.g., CommandOrScript.

        This query searches for a content item by its type, ID and marketplaces,
        as well as the dependency by its ID, type and whether it exists in one of the content item's marketplaces.
        If both found, we create a USES relationship between them.
        """
        if target_type == ContentTypes.BASE_CONTENT:
            target_property = 'node_id'
        else:
            target_property = 'id'

        query = f"""
            UNWIND $data AS rel_data
            MATCH (content_item:{ContentTypes.BASE_CONTENT}{{
                node_id: rel_data.source_node_id,
                fromversion: rel_data.source_fromversion,
                marketplaces: rel_data.source_marketplaces
            }})
            MERGE (dependency:{Neo4jQuery.labels_of(target_type)}{{
                {target_property}: rel_data.target
            }})
            WITH rel_data, content_item, dependency,
                ANY(
                    marketplace IN dependency.marketplaces
                    WHERE marketplace IN rel_data.source_marketplaces
                ) AS dependency_exists_in_source_marketplace
            WHERE dependency_exists_in_source_marketplace
            MERGE (content_item)-[r:{Rel.USES}]->(dependency)
            ON CREATE
                SET r.mandatorily = rel_data.mandatorily
            ON MATCH
                SET r.mandatorily = r.mandatorily OR rel_data.mandatorily
        """
        return query

    @staticmethod
    def create_relationships(relationship: Rel) -> str:
        if relationship == Rel.HAS_COMMAND:
            return Neo4jQuery.create_has_command_relationships()
        if relationship == Rel.USES:
            return Neo4jQuery.create_uses_relationships(target_type=ContentTypes.BASE_CONTENT)
        if relationship == Rel.USES_COMMAND_OR_SCRIPT:
            return Neo4jQuery.create_uses_relationships(target_type=ContentTypes.COMMAND_OR_SCRIPT)

        # default query
        return f"""
            UNWIND $data AS rel_data
            MATCH (source:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.source_node_id}})
            MERGE (target:{ContentTypes.BASE_CONTENT}{{node_id: rel_data.target}})
            MERGE (source)-[r:{relationship}]->(target)
        """

    @staticmethod
    def update_marketplace_property(marketplace: str) -> str:
        """
        In this query, we find all content items that are currently considered in a given marketplace,
        but uses a dependency that is not in this marketplace.
        To make sure the dependency is not in this marketplace, we make sure there is no alternative with
        the same content type and id as the dependency which is in the marketplace.

        If such dependencies were found, we drop the content item from the marketplace.
        """
        # todo: USES{mandatorily?}
        # ignore IGNORED_PACKS_IN_DEPENDENCY_CALC?
        return f"""
            MATCH (content_item:{ContentTypes.BASE_CONTENT})
                -[:{Rel.USES}*{{mandatorily: true}}]->
                    (dependency:{ContentTypes.BASE_CONTENT}),
            (alternative_dependency:{ContentTypes.BASE_CONTENT}{{
                node_id: dependency.node_id
            }})
            WHERE "{marketplace}" IN content_item.marketplaces
            AND NOT "{marketplace}" IN dependency.marketplaces
            AND "{marketplace}" IN alternative_dependency.marketplaces
            WITH content_item,
                count(alternative_dependency) = 0 AS no_alternative_dependency
            WHERE no_alternative_dependency
            SET content_item.marketplaces = REDUCE(
                marketplaces = [], mp IN content_item.marketplaces |
                CASE WHEN mp <> "{marketplace}" THEN marketplaces + mp ELSE marketplaces END
            )
            RETURN count(content_item) AS updated_marketplaces_count
        """

    @staticmethod
    def create_dependencies_for_marketplace() -> str:
        return f"""
            MATCH (pack_a:{ContentTypes.BASE_CONTENT})<-[:{Rel.IN_PACK}]-(a)-[r:{Rel.USES}]->(b)-[:{Rel.IN_PACK}]->(pack_b:{ContentTypes.BASE_CONTENT})
            WHERE ANY(marketplace IN pack_a.marketplaces WHERE marketplace IN pack_b.marketplaces)
            AND pack_a.id <> pack_b.id
            AND NOT pack_a.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
            AND NOT pack_b.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
            WITH r, pack_a, pack_b
            MERGE (pack_a)-[dep:DEPENDS_ON]->(pack_b)
            WITH dep, r, REDUCE(
                marketplaces = [], mp IN pack_a.marketplaces |
                CASE WHEN mp IN pack_b.marketplaces THEN marketplaces + mp ELSE marketplaces END
            ) AS common_marketplaces
            SET dep.marketplaces = common_marketplaces,
                dep.mandatorily = r.mandatorily
            RETURN *
        """

    @staticmethod
    def labels_of(content_type: ContentTypes) -> str:
        return ':'.join(content_type.labels)
