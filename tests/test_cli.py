import json
import subprocess
import sys

from mnemograph.auth import Credentials


def test_provision_scoped_identity_and_preserve_initial_keys(tmp_path):
    def run(*args):
        return subprocess.run([sys.executable,"-m","mnemograph",*args,"--data-dir",str(tmp_path)],
                              capture_output=True,text=True)
    assert run("init").returncode == 0
    original = json.loads((tmp_path / "keys.json").read_text())
    assert run("init").returncode == 0
    assert json.loads((tmp_path / "keys.json").read_text()) == original
    result = run("issue","--agent","auditor","--project","atlas","--actions","read")
    assert result.returncode == 0, result.stderr
    keys = json.loads((tmp_path / "keys.json").read_text())
    assert all(keys[name] == value for name,value in original.items())
    token = keys["local/atlas/auditor"]
    assert token not in result.stdout
    scope = Credentials(json.loads((tmp_path / "credentials.json").read_text())).authorize(token)
    assert scope.project == "atlas" and scope.actions == frozenset({"read"})
    assert run("issue","--agent","auditor","--project","atlas").returncode != 0


def test_provision_rejects_invalid_identity(tmp_path):
    result = subprocess.run([sys.executable,"-m","mnemograph","issue","--agent","../bad","--data-dir",str(tmp_path)],
                            capture_output=True,text=True)
    assert result.returncode != 0


def test_connection_check_requires_token_without_creating_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("MNEMO_TOKEN", raising=False)
    result = subprocess.run([sys.executable, "-m", "mnemograph", "check", "--data-dir", str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "Set MNEMO_TOKEN" in result.stderr
    assert not list(tmp_path.iterdir())
