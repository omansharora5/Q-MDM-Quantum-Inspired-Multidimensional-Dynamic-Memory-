"""Two independent processes, one shared memory. Requires the running service."""
import json
import subprocess
import sys
from pathlib import Path

from mnemograph.client import MemoryClient
from mnemograph.demo import SAMPLES
from mnemograph.models import Memory


def main():
    keys = json.loads(Path(".local/keys.json").read_text())
    if len(sys.argv) == 1:
        for role in ("researcher", "developer"):
            result = subprocess.run([sys.executable, __file__, role], check=True, capture_output=True, text=True)
            print(result.stdout.strip())
        return
    role = sys.argv[1]
    with MemoryClient(keys[role]) as client:
        client.connect("independent-python-process", "Camera architecture handoff")
        if role == "researcher":
            title, kind, content, cues = SAMPLES[2]
            memory = Memory(title=title,kind=kind,content=content,cues=cues,status="accepted",synthetic=True,dataset="camera-lab",
                            source={"title":"Synthetic bench note","text":content})
            receipt = client.remember(memory.model_dump(mode="json"),"cross-agent-demo-v2")
            client.handoff("Implement camera capture","developer","Continue using the sourced four-camera decision.",
                           [receipt["id"]],"cross-agent-handoff-v2")
            print("Researcher saved a sourced memory and handed off the capture task.")
        else:
            packet = client.recall("hardware constraints", dataset="camera-lab")
            assert packet["handles"], packet
            evidence = [client.expand(h["id"], h["version"]) for h in packet["handles"]]
            assert any("four" in e["payload"]["content"].lower() for e in evidence)
            assert any(task["payload"]["target_agent"] == role for task in client.state()["tasks"])
            print(f"Developer recalled {len(packet['handles'])} handles and verified the original evidence and handoff in a separate process.")


if __name__ == "__main__":
    main()
