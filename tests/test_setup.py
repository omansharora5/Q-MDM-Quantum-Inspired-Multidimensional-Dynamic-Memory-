from pathlib import Path

from test_contract import environment, headers


def test_setup_is_scoped_and_does_not_return_keys(environment):
    client, _, _ = environment
    assert client.get("/api/setup").status_code == 401
    response = client.get("/api/setup",headers=headers())
    assert response.status_code == 200
    data = response.json()
    assert data["agents"] == ["developer","reader","researcher"]
    assert data["tenant"] == "tenant-a" and data["url"] == "http://testserver"
    assert Path(data["python"]).is_absolute()
    assert "token" not in data and "keys" not in data
    assert client.get("/api/setup",headers=headers("c")).json()["agents"] == ["outsider"]
