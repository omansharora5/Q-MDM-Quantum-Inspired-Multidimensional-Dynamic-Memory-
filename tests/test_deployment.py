import runpy
from pathlib import Path

from fastapi.testclient import TestClient


def test_demo_starts_with_the_visible_dataset_and_retries_safely(tmp_path, monkeypatch):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MNEMO_DEMO_KEY", "isolated-demo-test-key")
    monkeypatch.setenv("MNEMO_AUTOSEED", "1")
    entrypoint = Path(__file__).resolve().parents[1] / "api" / "index.py"
    headers = {"Authorization": "Bearer isolated-demo-test-key"}
    ids = None
    for _ in range(2):
        app = runpy.run_path(str(entrypoint))["app"]
        with TestClient(app, base_url="https://memory.example") as client:
            state = client.get("/api/state?dataset=personal-assistant", headers=headers).json()
            assert len(state["memories"]) == 6
            current_ids = {memory["id"] for memory in state["memories"]}
            assert ids is None or ids == current_ids
            ids = current_ids
            assert client.get("/api/timeline?dataset=personal-assistant", headers=headers).json()["messages"]
            setup = client.get("/api/setup", headers=headers).json()
            assert setup["local_setup"] is False and setup["python"] is None
            assert client.get("/api/context", headers={**headers, "Origin": "https://other.example"}).status_code == 403


def test_demo_can_start_without_seeding(tmp_path, monkeypatch):
    monkeypatch.setenv("MNEMO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MNEMO_DEMO_KEY", "isolated-demo-test-key")
    monkeypatch.setenv("MNEMO_AUTOSEED", "0")
    app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "api" / "index.py"))["app"]
    with TestClient(app) as client:
        response = client.get("/api/state", headers={"Authorization": "Bearer isolated-demo-test-key"})
        assert response.status_code == 200 and not response.json()["memories"]
