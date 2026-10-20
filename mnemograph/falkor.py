import json

from falkordb.graph import Graph
from redis import Redis

from .auth import DomainError
from .store import encode, prepare, prepare_forget


MEMORY_RELATIONS = ("SUPPORTS", "SUPERSEDES", "CONTRADICTS", "REFINES", "DUPLICATES", "DERIVED_FROM")


class FalkorStore:
    name = "falkordb"

    def __init__(self, url):
        self.redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=15)
        self.redis.ping()

    def graph(self, scope):
        graph = Graph(self.redis, "mnemo_" + scope.namespace)
        graph.query("MERGE (p:Project {id:'project'}) ON CREATE SET p.revision=0")
        return graph

    def snapshot(self, scope):
        rows = self.graph(scope).query(
            "MATCH (n) WHERE n.category IS NOT NULL RETURN n.category, n.record",
            timeout=5000).result_set
        state = {"revision": 0, "entities": {}, "history": [], "events": [], "receipts": {}}
        for category, raw in rows:
            value = json.loads(raw)
            if category == "entity":
                state["entities"][value["id"]] = value
            elif category == "history":
                state["history"].append(value)
            elif category == "event":
                state["events"].append(value)
                state["revision"] = max(state["revision"], value["revision"])
            elif category == "receipt":
                state["receipts"][value["key"]] = value
        state["history"].sort(key=lambda item: item["revision"])
        state["events"].sort(key=lambda item: item["revision"])
        return state

    def adjacency(self, scope):
        rows = self.graph(scope).query("""
            MATCH (a:Entity)-[:HAS_CUE]->(c:Cue)<-[:HAS_CUE]-(b:Entity)
            WHERE a.id <> b.id RETURN a.id AS source,b.id AS target,'cue:' + c.name AS relation
            UNION
            MATCH (a:Entity)-[r:RELATED_TO|SUPPORTS|SUPERSEDES|CONTRADICTS|REFINES|DUPLICATES|DERIVED_FROM]-(b:Entity)
            RETURN a.id AS source,b.id AS target,type(r) AS relation
        """, timeout=5000).result_set
        adjacency = {}
        for source, target, relation in rows:
            adjacency.setdefault(source, {})[target] = relation
        return adjacency

    def commit(self, scope, entity_id, kind, payload, expected, key, request_hash):
        graph = self.graph(scope)
        # shortcut: project revision retries serialize short commits, use narrower invariants after measuring contention.
        for _ in range(16):
            state = self.snapshot(scope)
            receipt, change = prepare(state, scope, entity_id, kind, payload, expected, key, request_hash)
            if not change:
                return receipt
            record = change["record"]
            params = {"base": state["revision"], "id": entity_id, "kind": kind, "record": encode(record),
                      "revision": record["revision"], "event": encode(change["event"]),
                      "receipt_key": change["receipt_key"], "receipt": encode({"key": change["receipt_key"],
                       "request_hash": request_hash, "receipt": receipt}), "actor": scope.agent,
                      "title": payload.get("title", payload.get("query", kind)),
                      "dataset": payload.get("dataset", "workspace")}
            query = """
                MATCH (p:Project {id:'project'}) WHERE p.revision=$base
                SET p.revision=$revision
                MERGE (n:Entity {id:$id})
                SET n.category='entity', n.record=$record, n.kind=$kind, n.title=$title, n.dataset=$dataset
                MERGE (n)-[:ABOUT]->(p)
                MERGE (a:Agent {id:$actor}) MERGE (a)-[:WORKS_ON]->(p)
                CREATE (v:Revision {category:'history',record:$record,version:$revision})
                CREATE (v)-[:CHANGED]->(n)
                CREATE (e:Event {category:'event',record:$event})
                CREATE (r:WriteReceipt {id:$receipt_key,category:'receipt',record:$receipt})
                CREATE (r)-[:RECORDED]->(v)
            """
            if kind == "memory":
                params.update(source_id=f"{entity_id}-v{record['version']}", source=encode(payload["source"]))
                query += """
                    CREATE (s:Source {id:$source_id,record:$source})
                    CREATE (v)-[:EVIDENCED_BY]->(s)
                    MERGE (n)-[:AUTHORED_BY]->(a)
                    WITH p,n,v
                    OPTIONAL MATCH (n)-[old:HAS_CUE|RELATED_TO|SUPPORTS|SUPERSEDES|CONTRADICTS|REFINES|DUPLICATES|DERIVED_FROM|SOURCED_FROM]->() DELETE old
                    WITH DISTINCT p,n,v
                """
                for index, cue in enumerate(payload.get("cues", [])):
                    params[f"cue{index}"] = cue
                    query += f" MERGE (c{index}:Cue {{name:$cue{index}}}) MERGE (n)-[:HAS_CUE]->(c{index}) "
                for index, related in enumerate(payload.get("related_ids", [])):
                    params[f"related{index}"] = related
                    query += f" WITH p,n,v MATCH (b{index}:Entity {{id:$related{index}}}) MERGE (n)-[:RELATED_TO]->(b{index}) "
                for index, link in enumerate(payload.get("links", [])):
                    relation = link["relation"]
                    if relation not in MEMORY_RELATIONS:
                        raise DomainError(422, "Unsupported memory relationship")
                    params[f"link{index}"] = link["target_id"]
                    query += f" WITH p,n,v MATCH (l{index}:Entity {{id:$link{index}}}) MERGE (n)-[:{relation}]->(l{index}) "
                if payload.get("source_message_id"):
                    params["source_message"] = payload["source_message_id"]
                    query += " WITH p,n,v MATCH (m:Entity {id:$source_message}) MERGE (n)-[:SOURCED_FROM]->(m) "
            if kind == "task":
                params["target"] = payload["target_agent"]
                query += " MERGE (t:Agent {id:$target}) MERGE (n)-[:ASSIGNED_TO]->(t) "
            query += " RETURN n.id "
            if graph.query(query, params=params, timeout=5000).result_set:
                return receipt
        raise DomainError(503, "Project is busy; retry this command with the same idempotency key")

    def forget(self, scope, entity_id, expected, key):
        graph = self.graph(scope)
        for _ in range(16):
            state = self.snapshot(scope)
            receipt, change = prepare_forget(state, scope, entity_id, expected, key)
            if not change:
                return receipt
            params = {"base": state["revision"], "revision": receipt["revision"], "id": entity_id,
                      "redactions": [{"id": removed_id, "record": encode(record)}
                                     for removed_id, record in change["tombstones"].items()],
                      "record": encode(change["tombstones"][entity_id]), "event": encode(change["event"]),
                      "receipt_key": change["receipt_key"],
                      "receipt": encode({"key": change["receipt_key"], "request_hash": change["request_hash"],
                                         "receipt": receipt})}
            params["forgotten_cues"] = sorted({cue for record in state["history"] + list(state["entities"].values())
                                                if record["id"] in change["tombstones"]
                                                for cue in record["payload"].get("cues", [])})
            query = """
                MATCH (p:Project {id:'project'}) WHERE p.revision=$base
                SET p.revision=$revision
                WITH p
                UNWIND $redactions AS item
                MATCH (n:Entity {id:item.id})
                SET n.record=item.record, n.kind='tombstone', n.title='Forgotten', n.dataset=''
                WITH p,n,item
                OPTIONAL MATCH (v:Revision)-[:CHANGED]->(n)
                SET v.record=item.record
                WITH p,n,v
                OPTIONAL MATCH (v)-[:EVIDENCED_BY]->(s:Source)
                DETACH DELETE s
                WITH DISTINCT p,n
                OPTIONAL MATCH (n)-[old]-()
                DELETE old
                WITH DISTINCT p
                OPTIONAL MATCH (c:Cue) WHERE c.name IN $forgotten_cues AND NOT (c)--()
                DELETE c
                WITH DISTINCT p
                MATCH (n:Entity {id:$id})
                CREATE (v:Revision {category:'history',record:$record,version:$revision})
                CREATE (v)-[:CHANGED]->(n)
                CREATE (e:Event {category:'event',record:$event})
                CREATE (r:WriteReceipt {id:$receipt_key,category:'receipt',record:$receipt})
                CREATE (r)-[:RECORDED]->(v)
                RETURN n.id
            """
            if graph.query(query, params=params, timeout=5000).result_set:
                return receipt
        raise DomainError(503, "Project is busy; retry this command with the same idempotency key")
