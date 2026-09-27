"""Writes extracted entities and relationships into Neo4j."""

from claim_graph_rag.graph.neo4j_client import get_neo4j_driver


def save_entities(tx, entities: list[dict]) -> None:
    for entity in entities:
        tx.run(
            "MERGE (e:Entity {name: $name}) SET e.type = $type",
            name=entity["name"],
            type=entity["type"],
        )


def save_relationships(tx, relationships: list[dict]) -> None:
    for rel in relationships:
        rel_type = rel["relationship"].replace(" ", "_").upper()
        tx.run(
            f"""MATCH (a:Entity {{name: $source}}), (b:Entity {{name: $target}})
                MERGE (a)-[:{rel_type}]->(b)""",
            source=rel["source"],
            target=rel["target"],
        )


def save_to_graph(entities: list[dict], relationships: list[dict]) -> None:
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            session.execute_write(save_entities, entities)
            session.execute_write(save_relationships, relationships)
    finally:
        driver.close()
