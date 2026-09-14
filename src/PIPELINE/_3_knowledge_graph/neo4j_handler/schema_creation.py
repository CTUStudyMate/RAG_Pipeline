import os

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

SCHEMA_QUERIES = [
    """
    DROP CONSTRAINT chunk_database_id_unique IF EXISTS;
    """,
    """
    DROP INDEX entity_normalized_name_index IF EXISTS;
    """,
    """
    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
    FOR (entity:Entity)
    REQUIRE entity.entity_id IS UNIQUE;
    """,
    """
    CREATE INDEX entity_name_key_index IF NOT EXISTS
    FOR (entity:Entity)
    ON (entity.name_key);
    """
]


def initialize_neo4j_schema(
    driver: Driver,
    database: str = "neo4j",
) -> None:
    for query in SCHEMA_QUERIES:
        driver.execute_query(
            query,
            database_=database,
        )

    print("Neo4j schema initialized successfully.")


def main() -> None:
    load_dotenv()

    database = os.getenv("NEO4J_DATABASE") or "neo4j"

    with GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(
            os.environ["NEO4J_USERNAME"],
            os.environ["NEO4J_PASSWORD"],
        ),
    ) as driver:
        driver.verify_connectivity()
        print("Connected to Neo4j AuraDB successfully.")

        initialize_neo4j_schema(
            driver=driver,
            database=database,
        )


if __name__ == "__main__":
    main()