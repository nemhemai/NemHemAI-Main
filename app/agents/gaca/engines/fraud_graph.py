"""4.12 Fraud & Risk - Graph Analytics (Neo4j). Finds fraud rings (direct + multi-hop)."""
from collections import defaultdict
from neo4j import GraphDatabase
from app.agents.gaca.config import settings


def _driver():
    return GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))


def sync_citizens(citizens) -> int:
    with _driver() as driver, driver.session() as session:
        for c in citizens:
            session.run("MERGE (c:Citizen {id:$id})", id=c.citizen_id)
            if c.address:
                session.run("MATCH (c:Citizen {id:$id}) MERGE (a:Address {value:$v}) "
                            "MERGE (c)-[:LIVES_AT]->(a)", id=c.citizen_id, v=c.address)
            if c.bank_account:
                session.run("MATCH (c:Citizen {id:$id}) MERGE (b:Bank {value:$v}) "
                            "MERGE (c)-[:HAS_BANK]->(b)", id=c.citizen_id, v=c.bank_account)
            if c.mobile:
                session.run("MATCH (c:Citizen {id:$id}) MERGE (m:Mobile {value:$v}) "
                            "MERGE (c)-[:HAS_MOBILE]->(m)", id=c.citizen_id, v=c.mobile)
    return len(citizens)


def _shared_pairs():
    with _driver() as driver, driver.session() as session:
        result = session.run(
            "MATCH (c1:Citizen)-[]->(s)<-[]-(c2:Citizen) WHERE c1.id < c2.id "
            "RETURN c1.id AS a, c2.id AS b, labels(s)[0] AS attr, s.value AS value")
        return [{"a": r["a"], "b": r["b"], "attr": r["attr"], "value": r["value"]}
                for r in result]


def _connected_components(pairs):
    parent = {}
    def find(x):
        parent.setdefault(x, x); root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root
    def union(a, b):
        parent[find(a)] = find(b)
    for p in pairs:
        union(p["a"], p["b"])
    groups = defaultdict(set)
    for node in list(parent):
        groups[find(node)].add(node)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def fraud_networks():
    pairs = _shared_pairs()
    rings = _connected_components(pairs)
    return {"direct_links": pairs, "fraud_rings": rings, "ring_count": len(rings)}