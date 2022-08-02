
from typing import Any, Dict, List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, MARKETPLACE_PROPERTIES


IGNORED_PACKS_IN_DEPENDENCY_CALC = ['NonSupported', 'Base', 'ApiModules']

class Neo4jQuery:
    @staticmethod
    def create_nodes_keys() -> List[str]:
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
    def create_node_map(data: Dict[str, str]) -> str:
        return f"{{{', '.join([f'{prop}: {val}' for prop, val in data.items()])}}}"

    @staticmethod
    def create_single_node_map() -> str:
        data: Dict[str, str] = {
            'id': 'data.id',
            'fromversion': 'data.fromversion',
        }
        for marketplace, mp_propery in MARKETPLACE_PROPERTIES.items():
            data[mp_propery] = f'"{marketplace}" IN data.marketplaces'

        return Neo4jQuery.create_node_map(data)

    @staticmethod
    def create_source_node_map() -> str:
        data: Dict[str, str] = {
            'id': 'data.source_id',
            'fromversion': 'data.source_fromversion',
        }
        for marketplace, mp_propery in MARKETPLACE_PROPERTIES.items():
            data[mp_propery] = f'"{marketplace}" IN data.source_marketplaces'

        return Neo4jQuery.create_node_map(data)

    @staticmethod
    def create_target_node_map() -> str:
        data: Dict[str, str] = {
            'id': 'data.target_id',
        }
        return Neo4jQuery.create_node_map(data)

    @staticmethod
    def create_nodes(content_type: ContentTypes) -> str:
        return f"""
            UNWIND $data AS data
            CREATE (n:{Neo4jQuery.labels_of(content_type)}{Neo4jQuery.create_single_node_map()})
            SET n += data
        """

    @staticmethod
    def get_command_marketplace_properties_to_set(
        is_create: bool = True,
        initialize_to_false: bool = False,
    ) -> str:
        if is_create:
            if initialize_to_false:
                return ', '.join([
                f'cmd.{mp_property} = false' for mp_property in MARKETPLACE_PROPERTIES.values()
            ])
            return ', '.join([
                f'cmd.{mp_property} = data.{mp_property}'
                for mp_property in MARKETPLACE_PROPERTIES.values()
            ])

        return ', '.join([
            f'cmd.{mp_property} = cmd.{mp_property} OR data.{mp_property}'
            for mp_property in MARKETPLACE_PROPERTIES.values()
        ])

    @staticmethod
    def create_has_command_relationships() -> str:
        return f"""
            UNWIND $data AS data
            MATCH (integration:{ContentTypes.INTEGRATION}{Neo4jQuery.create_source_node_map()})
            MERGE (cmd:{Neo4jQuery.labels_of(ContentTypes.COMMAND)}{Neo4jQuery.create_target_node_map()})
            ON CREATE
                SET {Neo4jQuery.get_command_marketplace_properties_to_set(is_create=True)}
            ON MATCH
                SET {Neo4jQuery.get_command_marketplace_properties_to_set(is_create=False)}
            MERGE (integration)-[r:{Rel.HAS_COMMAND}{{deprecated: data.deprecated}}]->(cmd)
        """

    @staticmethod
    def create_uses_relationships(source_type: ContentTypes, target_type: ContentTypes) -> str:
        if target_type == ContentTypes.COMMAND_OR_SCRIPT:
            return Neo4jQuery.create_uses_command_or_script_relationships()

        source_node_map = Neo4jQuery.create_source_node_map()
        target_node_map = Neo4jQuery.create_target_node_map()

        query = f"""
            UNWIND $data AS data
            MATCH (content_item:{source_type}{source_node_map})
            MATCH (dependency:{Neo4jQuery.labels_of(target_type)}{target_node_map})
            MERGE (content_item)-[r:{Rel.USES}]->(dependency)
            ON CREATE
                SET r.mandatorily = data.mandatorily
            ON MATCH
                SET r.mandatorily = r.mandatorily OR data.mandatorily
        """
        return query

    @staticmethod
    def create_uses_command_or_script_relationships() -> str:
        """
        This query creates a relationship between a script and a command/scripts that is executed by the script.
        Before running this query, it is not known whether the target node is a script or a command.
        However, if the node was created during the merge, it is necessarily a command, since all scripts 
        were previously created.
        In this case, we initialize the command's marketplaces properties to 'false' and they will be updated
        during the creation of HAS_COMMAND relationships (according to the implementing integrations' properties).
        """
        return f"""
            UNWIND $data AS data
            MATCH (script:{ContentTypes.SCRIPT}{Neo4jQuery.create_source_node_map()})
            MERGE (cmd:{ContentTypes.COMMAND_OR_SCRIPT}{Neo4jQuery.create_target_node_map()})
            ON CREATE
                SET cmd:{Neo4jQuery.labels_of(ContentTypes.COMMAND)},
                    {Neo4jQuery.get_command_marketplace_properties_to_set(initialize_to_false=True)}

            MERGE (script)-[r:{Rel.USES}]->(cmd)
            ON CREATE
                SET r.mandatorily = data.mandatorily
            ON MATCH
                SET r.mandatorily = r.mandatorily OR data.mandatorily
        """

    @staticmethod
    def create_relationships(source_type: ContentTypes, rel_type: Rel, target_type: ContentTypes) -> str:
        if rel_type == Rel.USES:
            return Neo4jQuery.create_uses_relationships(source_type, target_type)
        if rel_type == Rel.HAS_COMMAND:
            return Neo4jQuery.create_has_command_relationships()

        # default query
        return f"""
            UNWIND $data AS data
            MATCH (source:{source_type}{Neo4jQuery.create_source_node_map()})
            MERGE (target:{target_type}{Neo4jQuery.create_target_node_map()})
            MERGE (source)-[r:{rel_type}]->(target)
        """

    @staticmethod
    def update_marketplace_property(mp_property: str) -> List[str]:
        """
        In this query, we find all content items that are currently considered in a specific marketplace,
        but uses a dependency that is not in this marketplace.
        To make sure the dependency is not in this marketplace, we make sure there is no other node with
        the same content type and id as the dependency.
        We ignore dependencies that are part of a pack in IGNORED_PACKS_IN_DEPENDENCY_CALC list.

        If such dependencies were found, we set the content item's marketplace property to "false".
        """
        queries: List[str] = []
        for dependency_content_type in ContentTypes.content_items():
            queries.append(f"""
                MATCH (content_item:{ContentTypes.BASE_CONTENT}{{{mp_property}: true}})
                    -[:{Rel.USES}*{{mandatorily: true}}]->
                        (dependency:{dependency_content_type}{{{mp_property}: false}})
                            -[:{Rel.IN_PACK}]->(pack),
                (alternative_dependency:{dependency_content_type}{{
                    {mp_property}: true,
                    id: dependency.id
                }})
                WHERE NOT pack.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC},
                WITH count(alternative_dependency) = 0 AS dependency_not_in_mp
                WHERE dependency_not_in_mp
                SET content_item.{mp_property} = false
            """)
        return queries

    @staticmethod
    def create_dependencies_for_marketplace(mp_property: str) -> str:
        return f"""
            MATCH (pack_a)<-[:{Rel.IN_PACK}]-(a)-[r:{Rel.USES}]->(b)-[:{Rel.IN_PACK}]->(pack_b),
            WHERE a.{mp_property} AND b.{mp_property}
            AND pack_a.id <> pack_b.id
            AND NOT pack_a.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
            AND NOT pack_b.id IN {IGNORED_PACKS_IN_DEPENDENCY_CALC}
            WITH pack_a, pack_b
            MERGE (pack_a)-[r:DEPENDS_ON{{
                mandatorily: r.mandatorily,
                {mp_property}: true
            }}]->(pack_b)
            RETURN *
        """

    @staticmethod
    def labels_of(content_type: ContentTypes) -> str:
        return ':'.join(content_type.labels)
