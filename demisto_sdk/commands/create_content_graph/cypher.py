from neomodel import db
from constants import Rel


def add_dependencies() -> None:
    q = 'MATCH (n1:ContentItemNode), (n2:ContentItemNode) ' \
        'WHERE n2.id IN n1.dependencies_ids ' \
        f'CREATE (n1) -[:{Rel.DEPENDS_ON}]->(n2) RETURN n1, n2'
    db.cypher_query(q)
