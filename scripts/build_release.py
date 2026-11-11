"""Package only this original architectural resource and its source."""

import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION="0.1.0"


def main():
    data=ROOT/"data"
    checks=json.loads((data/"validation.json").read_text(encoding="utf-8"))
    imports=json.loads((data/"import-validation.json").read_text(encoding="utf-8"))
    if checks.get("passed") is not True or checks["view_count"]!=12 or imports.get("passed") is not True:
        raise ValueError("The full rendered/validated resource and import checks are required.")
    if not (data/"index.html").is_file():
        raise ValueError("Build the offline viewer first.")
    dist=ROOT/"dist";dist.mkdir(exist_ok=True)
    if not (dist/"preview.png").is_file():
        raise ValueError("Put the actual inspected viewer screenshot at dist/preview.png.")
    inputs=[ROOT/name for name in ("README.md","README.zh-CN.md","LICENSE","CHANGELOG.md","requirements.txt",".gitignore")]
    for directory in ("configs","scripts","viewer","docs","data"):
        inputs.extend(path for path in (ROOT/directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc",".blend1"))
    archive=dist/f"facadeprobe-{VERSION}-resource.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for path in sorted(inputs):
            output.write(path,f"facadeprobe-{VERSION}/{path.relative_to(ROOT).as_posix()}")
    artifacts=[archive,dist/"preview.png"]
    (dist/"SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in artifacts),encoding="utf-8")
    print(json.dumps({"version":VERSION,"resource_file_count":len(inputs),"artifacts":[{"name":path.name,"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()} for path in artifacts]},indent=2))


if __name__=="__main__":
    main()
