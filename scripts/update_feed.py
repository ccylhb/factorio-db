#!/usr/bin/env python3
"""Update-feed + data-diff manager for DB sites.

Usage (run from anywhere; ROOT is resolved relative to this file):
  python scripts/update_feed.py init                 # snapshot current src/data/*.json
  python scripts/update_feed.py diff                 # item-level changes vs snapshot (then refresh snapshot)
  python scripts/update_feed.py add "Text" [/href]   # prepend a dated entry to updates.json (dedupe, keep 8)
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"
SNAP = DATA / ".snapshot.json"
UPDATES = DATA / "updates.json"


def data_files():
    return sorted(
        p for p in DATA.glob("*.json")
        if p.name not in ("updates.json",) and not p.name.startswith(".")
    )


def item_key(it):
    return (
        it.get("name")
        or it.get("title")
        or it.get("slug")
        or json.dumps(it, sort_keys=True)
    )


def load_array(path):
    try:
        arr = json.load(open(path, encoding="utf-8"))
        return arr if isinstance(arr, list) else []
    except Exception:
        return []


def fingerprint():
    fp = {}
    for p in data_files():
        arr = load_array(p)
        keys = [str(item_key(x)) for x in arr if isinstance(x, dict)]
        fp[p.name] = {
            "count": len(keys),
            "keys": keys,
            "sha": hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()[:12],
        }
    return fp


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def cmd_init():
    fp = fingerprint()
    SNAP.write_text(json.dumps(fp, ensure_ascii=False), encoding="utf-8")
    print(f"snapshot initialized: {len(fp)} data files, {sum(v['count'] for v in fp.values())} items")


def cmd_diff():
    old = load_json(SNAP)
    new = fingerprint()
    if not old:
        print("no snapshot yet - run: python scripts/update_feed.py init")
        return
    total_changes = 0
    for name in sorted(set(old) | set(new)):
        o, n = old.get(name), new.get(name)
        if o is None:
            print(f"[{name}] FILE REMOVED")
            total_changes += 1
            continue
        if n is None:
            print(f"[{name}] NEW FILE ({o['count']} items)")
            total_changes += 1
            continue
        added = [k for k in n["keys"] if k not in set(o["keys"])]
        removed = [k for k in o["keys"] if k not in set(n["keys"])]
        if added or removed or o["sha"] != n["sha"]:
            total_changes += 1
            print(f"[{name}] {o['count']} -> {n['count']} items (was {o['sha']}, now {n['sha']})")
            if added:
                print("   ADDED: " + ", ".join(added[:10]) + (" ..." if len(added) > 10 else ""))
            if removed:
                print("   REMOVED: " + ", ".join(removed[:10]) + (" ..." if len(removed) > 10 else ""))
            if not added and not removed and o["count"] == n["count"]:
                print("   (same items - value changes only)")
    SNAP.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    if total_changes == 0:
        print("no data changes")
    else:
        print(f"{total_changes} data file(s) changed - snapshot refreshed")


def cmd_add(args):
    if not args:
        print("usage: update_feed.py add \"Text\" [/href]")
        sys.exit(1)
    text = args[0]
    href = args[1] if len(args) > 1 else ""
    entries = load_array(UPDATES) if UPDATES.exists() else []
    today = date.today().isoformat()
    # dedupe by normalized text
    norm = " ".join(text.split())
    entries = [e for e in entries if " ".join(e.get("text", "").split()) != norm]
    entry = {"date": today, "text": norm}
    if href:
        entry["href"] = href
    entries.insert(0, entry)
    entries = entries[:8]
    UPDATES.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"added entry ({today}): {norm}" + (f" -> {href}" if href else ""))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        cmd_init()
    elif cmd == "diff":
        cmd_diff()
    elif cmd == "add":
        cmd_add(sys.argv[2:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
