from __future__ import annotations

import json
from pathlib import Path
import re
import sys


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(root: Path) -> list[str]:
    issues: list[str] = []
    manifest_path = root / ".codex-plugin" / "plugin.json"
    if not manifest_path.exists():
        return [f"missing manifest: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    name = manifest.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        issues.append("plugin name must be kebab-case")
    if root.name != name:
        issues.append("plugin folder name must match manifest name")
    for field in ("version", "description", "author", "interface"):
        if field not in manifest:
            issues.append(f"missing manifest field: {field}")
    interface = manifest.get("interface", {})
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category", "capabilities", "defaultPrompt"):
        if field not in interface:
            issues.append(f"missing interface field: {field}")
    if "[TODO:" in manifest_path.read_text(encoding="utf-8"):
        issues.append("manifest contains TODO placeholder")
    skills = root / str(manifest.get("skills", "./skills/"))
    if not skills.exists():
        issues.append("skills directory is missing")
    else:
        skill_files = sorted(skills.glob("*/SKILL.md"))
        if not skill_files:
            issues.append("no skill directories found")
        for skill_file in skill_files:
            text = skill_file.read_text(encoding="utf-8")
            if not text.startswith("---"):
                issues.append(f"{skill_file}: missing YAML frontmatter")
                continue
            frontmatter = text.split("---", 2)[1]
            for field in ("name:", "description:"):
                if field not in frontmatter:
                    issues.append(f"{skill_file}: missing {field}")
    return issues


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    issues = validate(root)
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print(f"Plugin validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
