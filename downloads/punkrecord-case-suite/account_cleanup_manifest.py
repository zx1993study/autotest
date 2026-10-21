"""Build a precise allowlist from recorded remote test fixtures, not name scans."""
import json
from pathlib import Path
import re
from uuid import UUID


HERE = Path(__file__).resolve().parent
KEEP_RUN = "team-headed-replay-20261019_144610.json"


def build_manifest(root=HERE):
    users = {}
    for path in sorted(root.glob("*.json")):
        if not (path.name.startswith("case-suite-results") or path.name.startswith("case-headed-results")
                or path.name.startswith("team-headed-replay-")):
            continue
        run = json.loads(path.read_text(encoding="utf-8"))
        assert run["target"].rstrip("/") == "http://14.103.229.153:15173"
        prefix = run["run_prefix"]
        assert re.fullmatch(r"CASE_\d{8}_\d{6}", prefix)
        for item in run.get("fixtures", []):
            if item["type"] != "user" or item.get("reused"):
                continue
            actor = item["username"].rsplit("_", 1)[-1]
            assert actor in {"manager", "employee", "other"}
            assert item["username"] == prefix.lower() + "_" + actor
            assert item["name"] == prefix + " " + actor
            user_id = str(UUID(item["id"]))
            record = {"id": user_id, "username": item["username"], "display_name": item["name"],
                      "actor": actor, "run_prefix": prefix}
            assert user_id not in users or users[user_id] == record
            users[user_id] = record
    latest = json.loads((root / KEEP_RUN).read_text(encoding="utf-8"))
    keep_ids = {str(UUID(u["id"])) for u in latest["fixtures"] if u["type"] == "user"}
    assert len(keep_ids) == 3 and keep_ids <= users.keys()
    return {"target": "http://14.103.229.153:15173", "expected_database": "punkrecord_local",
            "keep": [users[k] for k in sorted(keep_ids)],
            "delete": [u for k, u in sorted(users.items()) if k not in keep_ids],
            "source": "Recorded fixtures only; delete inactive accounts and owned dependent test rows"}


if __name__ == "__main__":
    manifest = build_manifest()
    path = HERE / "test-account-cleanup-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(path), "keep_count": len(manifest["keep"]),
                      "delete_count": len(manifest["delete"]),
                      "kept_usernames": [u["username"] for u in manifest["keep"]]}, ensure_ascii=False))
