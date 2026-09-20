try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    GraphDatabase = None

import re
from typing import Dict, Any, List
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.models import GraphFact

# Neo4j Cypher does not allow parameterizing node labels or relationship types.
# Since these values originate from LLM extraction, they must pass a strict
# identifier allow-list before being interpolated into the query. Anything
# unexpected falls back to a safe default so the query is never injectable.
_CYPHER_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

def _safe_token(token: str, fallback: str) -> str:
    if isinstance(token, str) and _CYPHER_TOKEN_RE.match(token):
        return token
    return fallback

class KnowledgeGraphService:
    def __init__(self):
        self.driver = None
        # In-process cache is retained only as a compatibility/test seam. The
        # durable GraphFact table is authoritative whenever Neo4j is offline.
        self._local_facts: Dict[str, List[Dict[str, Any]]] = {}

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

    def _add_local_fact(self, user_id: str, entity_a: str, label_a: str, predicate: str, entity_b: str, label_b: str):
        if user_id not in self._local_facts:
            self._local_facts[user_id] = []
        exists = any(
            f["source"] == entity_a and f["relationship"] == predicate and f["target"] == entity_b
            for f in self._local_facts[user_id]
        )
        if not exists:
            self._local_facts[user_id].append({
                "source": entity_a,
                "source_type": label_a,
                "relationship": predicate,
                "target": entity_b,
                "target_type": label_b,
            })

    def _get_local_graph(self, user_id: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            persisted = db.query(GraphFact).filter(GraphFact.user_id == user_id).all()
            facts = [
                {
                    "source": fact.source,
                    "source_type": fact.source_type,
                    "relationship": fact.relationship,
                    "target": fact.target,
                    "target_type": fact.target_type,
                }
                for fact in persisted
            ]
        finally:
            db.close()
        if not facts:
            facts = self._local_facts.get(user_id, [])
        nodes = set()
        edges = []
        for f in facts:
            nodes.add((f["source"], f["source_type"]))
            nodes.add((f["target"], f["target_type"]))
            edges.append({
                "source": f["source"],
                "target": f["target"],
                "relationship": f["relationship"],
            })
        formatted_nodes = [{"id": n[0], "label": n[0], "type": n[1]} for n in nodes]
        return {"nodes": formatted_nodes, "edges": edges}

    def add_fact(self, user_id: str, entity_a: str, label_a: str, predicate: str, entity_b: str, label_b: str):
        """
        Adds a graph triple (EntityA)-[PREDICATE]->(EntityB) scoped to a user.
        Example: (User)-[:USES]->(Python)
        Entity nodes are keyed by (name, user_id) to prevent cross-user data
        pollution — each user maintains their own isolated entity namespace.
        """
        label_a = _safe_token(label_a, "Concept")
        label_b = _safe_token(label_b, "Concept")
        predicate = _safe_token(predicate, "DISCUSSES")

        # Always update in-process graph fallback
        self._add_local_fact(user_id, entity_a, label_a, predicate, entity_b, label_b)

        driver = self.get_driver()
        if not driver:
            db = SessionLocal()
            try:
                exists = db.query(GraphFact).filter(
                    GraphFact.user_id == user_id,
                    GraphFact.source == entity_a,
                    GraphFact.relationship == predicate,
                    GraphFact.target == entity_b,
                ).first()
                if not exists:
                    db.add(GraphFact(
                        user_id=user_id,
                        source=entity_a,
                        source_type=label_a,
                        relationship=predicate,
                        target=entity_b,
                        target_type=label_b,
                    ))
                    db.commit()
            finally:
                db.close()
            return

        cypher = f"""
        MERGE (u:User {{id: $user_id}})
        MERGE (a:{label_a} {{name: $entity_a, user_id: $user_id}})
        MERGE (b:{label_b} {{name: $entity_b, user_id: $user_id}})
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
            return self._get_local_graph(user_id)

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
            if not formatted_nodes and self._local_facts.get(user_id):
                return self._get_local_graph(user_id)
            return {"nodes": formatted_nodes, "edges": edges}
        except Exception as e:
            print(f"Neo4j get_user_graph notice: {e}")
            return self._get_local_graph(user_id)

    def delete_fact(self, user_id: str, entity_name: str):
        """Safe graph pruning: removes the HAS_ENTITY relationship for this user,
        then deletes the node itself only if no other users still reference it.
        This prevents cross-user data loss that DETACH DELETE would cause.
        """
        if user_id in self._local_facts:
            self._local_facts[user_id] = [
                f for f in self._local_facts[user_id]
                if f["source"] != entity_name and f["target"] != entity_name
            ]

        driver = self.get_driver()
        if not driver:
            db = SessionLocal()
            try:
                db.query(GraphFact).filter(
                    GraphFact.user_id == user_id,
                    (GraphFact.source == entity_name) | (GraphFact.target == entity_name),
                ).delete(synchronize_session=False)
                db.commit()
            finally:
                db.close()
            return

        cypher = """
        MATCH (u:User {id: $user_id})-[r1:HAS_ENTITY]->(a {name: $entity_name, user_id: $user_id})
        DELETE r1
        WITH a
        WHERE NOT (a)<-[:HAS_ENTITY]-()
        DETACH DELETE a
        """
        try:
            with driver.session() as session:
                session.run(cypher, user_id=user_id, entity_name=entity_name)
        except Exception as e:
            raise RuntimeError(f"Neo4j graph deletion failed: {e}") from e


graph_service = KnowledgeGraphService()
