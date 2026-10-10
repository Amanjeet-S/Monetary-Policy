"""Check local Markdown targets and retained source hashes without network access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    names = set(filter(None, subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")))
    targets = names | {parent.as_posix() for name in names for parent in Path(name).parents}
    failures = []
    links_checked = 0
    for name in sorted(names):
        path = ROOT / name
        if path.suffix != ".md":
            continue
        text = path.read_text()
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            links_checked += 1
            if (not destination.is_relative_to(ROOT) or not destination.exists()
                    or destination.relative_to(ROOT).as_posix() not in targets):
                failures.append(f"{name}: missing or external local target {target}")

    snapshot = ROOT / "data/raw/2026-09-15"
    manifest = json.loads((snapshot / "manifest.json").read_text())
    for entry in manifest["sources"]:
        if hashlib.sha256((snapshot / entry["file"]).read_bytes()).hexdigest() != entry["sha256"]:
            failures.append(f"Germany source checksum differs: {entry['file']}")
    migration = json.loads((ROOT / "migration.json").read_text())
    for entry in migration["raw_files"]:
        if hashlib.sha256((ROOT / entry["destination_path"]).read_bytes()).hexdigest() != entry["sha256"]:
            failures.append(f"Migrated snapshot checksum differs: {entry['destination_path']}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Verified {links_checked} case-sensitive tracked Markdown targets, five source hashes and the migrated snapshot.")


if __name__ == "__main__":
    main()
