"""Vercel entrypoint.

Vercel's Python runtime loads ``app`` from this file and routes every request to
it. The deployment uses an ephemeral SQLite database under /tmp, because Vercel
Functions have a read-only filesystem apart from /tmp. Data is per-instance and
resets on cold starts; this is a public demo, not durable hosted storage.

Set MNEMO_DEMO_KEY to replace the public demo key, MNEMO_DATA_DIR to move the
database, or MNEMO_AUTOSEED=0 to skip the sample memories.
"""

import hashlib
import json
import os
from pathlib import Path

from mnemograph.api import create_app
from mnemograph.auth import Credentials
from mnemograph.demo import seed
from mnemograph.store import SQLiteStore

# Public credential for the deployed demo. It is intentionally published in the
# repository description and README. Set MNEMO_DEMO_KEY to rotate it.
DEMO_KEY = os.environ.get("MNEMO_DEMO_KEY", "qmdm-demo-aDr9oE5I8I4utiyPlIpTeOYJDCYD43FU7CPXMt7COFg")
DATA_DIR = Path(os.environ.get("MNEMO_DATA_DIR", "/tmp/mnemograph"))

credentials = Credentials([{
    "digest": hashlib.sha256(DEMO_KEY.encode()).hexdigest(),
    "tenant": "local",
    "project": "mnemograph",
    "agent": "operator",
    "actions": ["read", "write", "coordinate"],
}])

store = SQLiteStore(DATA_DIR / "memory.db")
app = create_app(store, credentials, allowed_hosts=["*"])

if os.environ.get("MNEMO_AUTOSEED", "1") != "0":
    seed(app.state.service, credentials.authorize(DEMO_KEY))
