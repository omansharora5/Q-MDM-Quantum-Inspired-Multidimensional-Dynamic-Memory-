import os

import httpx


class MemoryClient:
    """Same tools for a CLI wrapper, local model, or API agent's tool loop."""

    def __init__(self, token=None, url=None):
        self.http = httpx.Client(base_url=url or os.environ.get("MNEMO_URL", "http://127.0.0.1:8000"),
                                 headers={"Authorization": f"Bearer {token or os.environ['MNEMO_TOKEN']}"}, timeout=30)

    def request(self, method, path, **kwargs):
        response = self.http.request(method, "/api" + path, **kwargs)
        response.raise_for_status()
        return response.json()

    def connect(self, platform="custom-python", context=""):
        return self.request("POST", "/connect", json={"platform": platform, "context": context})

    def state(self):
        return self.request("GET", "/state")

    def context(self):
        return self.request("GET", "/context")

    def remember(self, memory, key, expected_version=0, memory_id=None):
        return self.request("PUT" if memory_id else "POST", "/memories" + ("/" + memory_id if memory_id else ""),
                            json={"memory": memory, "idempotency_key": key, "expected_version": expected_version})

    def recall(self, query, budget_chars=2400, max_hops=2, as_of=None, *, dataset=None, strategy="pace", cursor=None, intent=None):
        return self.request("POST", "/recall", json={"query": query, "budget_chars": budget_chars,
                                                    "max_hops": max_hops, "as_of": as_of, "dataset":dataset,
                                                    "strategy":strategy,"cursor":cursor,"intent":intent})

    def expand(self, memory_id, version=None):
        return self.request("GET", "/memories/" + memory_id, params={"version": version} if version else {})

    def handoff(self, title, target_agent, context, memory_ids, key, expected_version=0, task_id=None, status="open"):
        return self.request("PUT" if task_id else "POST", "/handoffs" + ("/" + task_id if task_id else ""),
                            json={"title": title, "target_agent": target_agent, "context": context,
                                  "memory_ids": memory_ids, "idempotency_key": key,
                                  "expected_version": expected_version, "status": status})

    def changes(self, after=0):
        return self.request("GET", "/changes", params={"after": after})

    def message(self, command):
        return self.request("POST", "/messages", json=command)

    def propose(self, memory, key):
        return self.request("POST", "/candidates", json={"memory":memory,"idempotency_key":key})

    def checkpoint(self, command):
        return self.request("POST", "/checkpoints", json=command)

    def claim(self, task_id, expected_task_version, key, lease_seconds=120):
        return self.request("POST", "/handoffs/"+task_id+"/claim", json={"expected_task_version":expected_task_version,
                            "idempotency_key":key,"lease_seconds":lease_seconds})

    def ack_action(self, command):
        return self.request("POST", "/actions", json=command)

    def forget(self, memory_id, expected_version, key):
        return self.request("POST", "/memories/"+memory_id+"/forget", json={"expected_version":expected_version,"idempotency_key":key})

    def close(self):
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
