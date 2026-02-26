from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "12345678"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def test_connection():
    with driver.session(database="nemhemgraph") as session:
        result = session.run("MATCH (n) RETURN count(n) AS count")
        print("Total nodes:", result.single()["count"])

if __name__ == "__main__":
    test_connection()