import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(
        os.environ["NEO4J_USERNAME"],
        os.environ["NEO4J_PASSWORD"],
    ),
)

driver.verify_connectivity()
print("Connected to Neo4j AuraDB successfully!")

records, summary, keys = driver.execute_query(
    "RETURN 1 AS result",
    database_=os.getenv("NEO4J_DATABASE", "neo4j"),
)

print(records[0]["result"])

driver.close()