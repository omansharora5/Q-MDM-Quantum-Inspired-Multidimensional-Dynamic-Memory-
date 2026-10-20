"""Build a review bundle without local databases, credentials or imported chats."""
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTED = {"research-proposal.md", "research-synthesis-v2.md"}


def package_files(root=ROOT):
    paths = [root/name for name in ("README.md","pyproject.toml","start.ps1","compose.yaml",".gitignore")]
    for directory in ("mnemograph","examples","tests","benchmarks","docs"):
        paths += [p for p in (root/directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix in (".py",".md",".html",".css",".js",".svg",".png",".tsv")
                  and p.name not in IMPORTED]
    paths += [p for p in (root/"artifacts"/"benchmarks").glob("*") if p.suffix in (".json",".csv",".md",".png",".svg")]
    paths += [root/"artifacts"/name for name in ("mnemograph-v2-walkthrough.mp4","walkthrough-manifest.json",
                                               "ui-responsive-check.json","restart-v2.json")]
    paths += list((root/"artifacts"/"demo-frames").glob("*.png"))
    paths = sorted(set(paths))
    for path in paths:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Invalid bundle path: {path.name}")
    return paths


def main():
    paths = package_files()
    keys = []
    for path in (ROOT/".local").glob("**/keys.json"):
        keys += [value.encode() for value in json.loads(path.read_text()).values() if isinstance(value,str) and len(value)>20]
    manifest = []
    for path in paths:
        data = path.read_bytes()
        if any(key in data for key in keys):
            raise ValueError(f"Local credential detected in {path.relative_to(ROOT)}; bundle not created")
        manifest.append({"path":path.relative_to(ROOT).as_posix(),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    destination = ROOT/"artifacts"/"mnemograph-v2-review-bundle.zip"
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path,path.relative_to(ROOT).as_posix())
        archive.writestr("bundle-manifest.json",json.dumps({"files":manifest,
            "note":"Local review bundle. SQLite demonstration; real FalkorDB runtime and public submission remain unverified. Imported user conversation/research files and local credentials/databases are excluded."},indent=2))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert not any(".local/" in name or "__pycache__/" in name or name.endswith(".db") for name in archive.namelist())
        assert {"README.md","docs/v2/system-spec.md","docs/blog-medium.md","mnemograph/web/app.js"} <= set(archive.namelist())
    print(json.dumps({"file":destination.name,"files":len(paths),"bytes":destination.stat().st_size,
                      "sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),"integrity":"passed","local_key_scan":"passed"}))


if __name__ == "__main__":
    main()
