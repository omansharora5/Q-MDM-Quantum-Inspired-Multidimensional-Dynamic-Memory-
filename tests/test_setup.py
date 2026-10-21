from pathlib import Path

from test_contract import environment, headers


def test_setup_is_scoped_and_does_not_return_keys(environment):
    client, _, _ = environment
    assert client.get("/api/setup").status_code == 401
    response = client.get("/api/setup",headers=headers())
    assert response.status_code == 200
    data = response.json()
    assert data["agents"] == ["developer","reader","researcher"]
    assert data["local_setup"] is True
    assert data["tenant"] == "tenant-a" and data["url"] == "http://testserver"
    assert Path(data["python"]).is_absolute()
    assert "token" not in data and "keys" not in data
    assert client.get("/api/setup",headers=headers("c")).json()["agents"] == ["outsider"]


def test_remote_setup_omits_server_paths(environment):
    from fastapi.testclient import TestClient
    from mnemograph.api import create_app

    _, store, credentials = environment
    with TestClient(create_app(store, credentials, allowed_hosts=["memory.example"], local_setup=False),
                    base_url="https://memory.example") as client:
        assert client.get("/api/setup").status_code == 401
        data = client.get("/api/setup", headers=headers()).json()
        assert data["local_setup"] is False
        assert data["python"] is None and data["workspace"] is None and data["data_directory"] is None
        assert data["url"] == "https://memory.example"
        assert data["agents"] == ["developer", "reader", "researcher"]
