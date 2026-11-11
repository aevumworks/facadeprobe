"""Create a file://-friendly viewer from the validated resource's real metadata."""

import argparse
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main(root):
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    validation=json.loads((root/"validation.json").read_text(encoding="utf-8"))
    if validation.get("passed") is not True:
        raise ValueError("The resource must pass geometry/label checks before building a viewer.")
    expected={(condition,view) for condition in ("clean","balcony","screen") for view in ("front","left","right","high")}
    if {(item["case"],item["view"]) for item in manifest["views"]}!=expected:
        raise ValueError("This viewer requires the complete default 3-condition x 4-camera fixture.")
    data={"manifest":manifest,"validation":validation,"frames":{}}
    for record in manifest["views"]:
        folder=root/record["path"]
        data["frames"][record["case"]+"/"+record["view"]]={"path":record["path"],"camera":json.loads((folder/"camera.json").read_text(encoding="utf-8")),"annotations":json.loads((folder/"annotations.json").read_text(encoding="utf-8"))}
    template=(ROOT/"viewer/template.html").read_text(encoding="utf-8")
    legend="".join(f'<span class="legend-item"><i style="background:rgb({",".join(map(str,c["color"]))})"></i>{escape(c["zh"])}</span>' for c in manifest["fixture"]["classes"] if c["id"])
    html=template.replace("__DATA__",json.dumps(data,ensure_ascii=False).replace("<","\\u003c")).replace("__LEGEND__",legend)
    (root/"index.html").write_text(html,encoding="utf-8")
    print("BUILT_VIEWER",len(data["frames"]))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root",type=Path)
    main(parser.parse_args().root.resolve())
