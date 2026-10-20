import argparse
import json
import os
import hashlib
import re
import secrets
from pathlib import Path

from .auth import Credentials, initialize


def main():
    parser = argparse.ArgumentParser(description="MnemoGraph local memory service")
    parser.add_argument("command", choices=["init", "issue", "serve", "check"], nargs="?", default="serve")
    parser.add_argument("--backend", choices=["sqlite", "falkordb"], default=os.environ.get("MNEMO_BACKEND", "sqlite"))
    parser.add_argument("--data-dir", default=os.environ.get("MNEMO_DATA_DIR", ".local"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MNEMO_PORT", "8000")))
    parser.add_argument("--agent")
    parser.add_argument("--tenant", default="local")
    parser.add_argument("--project", default="mnemograph")
    parser.add_argument("--actions", nargs="+", choices=["read", "write", "coordinate"], default=["read", "write", "coordinate"])
    options = parser.parse_args()
    if options.command == "check":
        if not os.environ.get("MNEMO_TOKEN"):
            parser.error("Set MNEMO_TOKEN to the agent's workspace key before checking the connection")
        from .client import MemoryClient
        with MemoryClient() as client:
            client.connect("connection-check", "Transport test only; no model session")
            state = client.state()
            print(json.dumps({"status":"connected", "agent":state["agent"], "project":state["project"],
                              "storage":state["storage"], "model_session":False}))
        return
    directory = Path(options.data_dir).resolve()
    initialize(directory)
    if options.command == "init":
        print(f"Credentials: {directory / 'credentials.json'}\nPrivate API keys: {directory / 'keys.json'}")
        return
    if options.command == "issue":
        if not options.agent or not all(re.fullmatch(r"[\w-]{1,80}", value) for value in [options.agent, options.tenant, options.project]):
            parser.error("--agent, --tenant, and --project require 1-80 letters, numbers, underscores, or hyphens")
        auth_path, keys_path = directory / "credentials.json", directory / "keys.json"
        entries = json.loads(auth_path.read_text())
        identity = (options.tenant, options.project, options.agent)
        if any((entry["tenant"], entry["project"], entry["agent"]) == identity for entry in entries):
            parser.error("That agent identity already exists; choose a distinct agent ID")
        token = secrets.token_urlsafe(32)
        entries.append({"digest": hashlib.sha256(token.encode()).hexdigest(), "tenant": options.tenant,
                        "project": options.project, "agent": options.agent, "actions": options.actions})
        keys = json.loads(keys_path.read_text())
        label = "/".join(identity)
        keys[label] = token
        keys_path.write_text(json.dumps(keys, indent=2), encoding="utf-8")
        auth_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        print(f"Private key saved under '{label}' in {keys_path}. Restart the service to load the grant.")
        return
    credentials = Credentials(json.loads((directory / "credentials.json").read_text(encoding="utf-8")))
    if options.backend == "sqlite":
        from .store import SQLiteStore
        store = SQLiteStore(directory / "memory.db")
    else:
        from .falkor import FalkorStore
        store = FalkorStore(os.environ.get("MNEMO_FALKOR_URL", "redis://127.0.0.1:6379"))
    from .api import create_app
    import uvicorn
    print(f"Dashboard: http://127.0.0.1:{options.port}\nStorage: {store.name}\nAPI keys: {directory / 'keys.json'}")
    uvicorn.run(create_app(store, credentials), host="127.0.0.1", port=options.port)
