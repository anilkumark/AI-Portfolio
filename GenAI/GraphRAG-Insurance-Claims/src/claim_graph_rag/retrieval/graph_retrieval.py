"""Given entity names from a question, retrieves connected facts from Neo4j."""

from claim_graph_rag.graph.neo4j_client import get_neo4j_driver


def get_connected_facts(entity_names: list[str]) -> list[dict]:
    driver = get_neo4j_driver()
    facts = []
    try:
        with driver.session() as session:
            for name in entity_names:
                result = session.run(
                    """MATCH (e:Entity {name: $name})-[r]-(other:Entity)
                       RETURN e.name AS entity, type(r) AS relationship,
                              other.name AS related_entity, other.type AS related_type""",
                    name=name,
                )
                facts.extend([dict(record) for record in result])
    finally:
        driver.close()
    return facts


if __name__ == "__main__":
    facts = get_connected_facts(["Sewer Backup"])
    for fact in facts:
        print(fact)
