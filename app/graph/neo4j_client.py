import logging
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jClient:
    """
    Singleton-style manager for Neo4j database connections.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance.driver = None
        return cls._instance

    def connect(self):
        """Initializes the Neo4j driver."""
        if not self.driver:
            try:
                self.driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                logger.info("Connected to Neo4j successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                self.driver = None

    def close(self):
        """Closes the Neo4j driver."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j connection closed.")

    def get_driver(self):
        """Returns the active driver, connecting if necessary."""
        if not self.driver:
            self.connect()
        return self.driver

    def setup_schema(self):
        """
        Creates constraints and indexes for the Graph RAG.
        Ensures nodes like Policies, Departments, and Penalties have unique IDs.
        """
        driver = self.get_driver()
        if not driver:
            logger.warning("Cannot setup Neo4j schema: Driver not initialized.")
            return

        queries = [
            "CREATE CONSTRAINT unique_policy IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT unique_department IF NOT EXISTS FOR (d:Department) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT unique_penalty IF NOT EXISTS FOR (p:Penalty) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT unique_category IF NOT EXISTS FOR (c:GrievanceCategory) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT unique_citizen IF NOT EXISTS FOR (c:Citizen) REQUIRE c.id IS UNIQUE",
        ]
        
        with driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    logger.error(f"Failed to run schema query '{q}': {e}")
        logger.info("Neo4j schema setup complete.")

neo4j_client = Neo4jClient()
