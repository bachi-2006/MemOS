try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    GraphDatabase = None

from typing import Dict, Any
from app.core.config import settings

class KnowledgeGraphService:
    def __init__(self):
        self.driver = None

    def get_driver(self):
        if not HAS_NEO4J:
            return None
        if not self.driver:
            try:
                self.driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
            except Exception as e:
                print(f"Neo4j connection notice: {e}")
                return None
        return self.driver


    def close(self):
        if self.driver:
            self.driver.close()

    def add_fact(self, user_id: str, entity_a: str, label_a: str, predicate: str, entity_b: str, label_b: str):
        """
        Adds a graph triple (EntityA)-[PREDICATE]->(EntityB) scoped to a user.
        Example: (User)-[:USES]->(Python)
        """
        driver = self.get_driver()
        if not driver:
            return
        cypher = f"""
        MERGE (u:User {{id: $user_id}})
        MERGE (a:{label_a} {{name: $entity_a}})
        MERGE (b:{label_b} {{name: $entity_b}})
        MERGE (u)-[:HAS_ENTITY]->(a)
        MERGE (a)-[r:{predicate}]->(b)
        RETURN a, r, b
        """
        try:
            with driver.session() as session:
                session.run(cypher, user_id=user_id, entity_a=entity_a, entity_b=entity_b)
        except Exception as e:
            print(f"Neo4j add_fact notice: {e}")

    def get_user_graph(self, user_id: str) -> Dict[str, Any]:
        """Retrieves nodes and edges for rendering in Frontend React Flow graph visualizer"""
        driver = self.get_driver()
        if not driver:
            return {"nodes": [], "edges": []}
        cypher = """
        MATCH (u:User {id: $user_id})-[r1:HAS_ENTITY]->(a)-[r2]->(b)
        RETURN a.name AS source, type(r2) AS relationship, b.name AS target, labels(a)[0] AS source_type, labels(b)[0] AS target_type
        LIMIT 100
        """
        nodes = set()
        edges = []
        try:
            with driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                for record in result:
                    src = record["source"]
                    tgt = record["target"]
                    rel = record["relationship"]
                    nodes.add((src, record["source_type"]))
                    nodes.add((tgt, record["target_type"]))
                    edges.append({"source": src, "target": tgt, "relationship": rel})

            formatted_nodes = [{"id": n[0], "label": n[0], "type": n[1]} for n in nodes]
            return {"nodes": formatted_nodes, "edges": edges}
        except Exception as e:
            print(f"Neo4j get_user_graph notice: {e}")
            return {"nodes": [], "edges": []}


graph_service = KnowledgeGraphService()
