from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
from typing import Any

from .compat import PLUGIN_ROOT
from .errors import ValidationError


VENDOR_ROOT = PLUGIN_ROOT / "vendor" / "codex-with-chatgpt"
DIST_ENTRY = VENDOR_ROOT / "dist" / "cli" / "index.js"
LOCAL_BIN = PLUGIN_ROOT / "vendor" / "bin"
LOCAL_CLOUDFLARED = LOCAL_BIN / "cloudflared.exe"


def detect_environment() -> dict[str, Any]:
    return {
        "vendor_root": str(VENDOR_ROOT),
        "vendor_present": VENDOR_ROOT.exists(),
        "node": shutil.which("node"),
        "corepack": shutil.which("corepack"),
        "pnpm": shutil.which("pnpm"),
        "cloudflared": str(LOCAL_CLOUDFLARED) if LOCAL_CLOUDFLARED.exists() else shutil.which("cloudflared"),
        "built": DIST_ENTRY.exists(),
        "dist_entry": str(DIST_ENTRY),
    }


def _run(command: list[str], *, cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(command[0]) or command[0]
    normalized = [executable, *command[1:]]
    if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
        normalized = ["cmd.exe", "/d", "/c", executable, *command[1:]]
    return subprocess.run(normalized, cwd=str(cwd), text=True, check=False, timeout=timeout)


def build_bridge(*, timeout: int = 900) -> dict[str, Any]:
    env = detect_environment()
    if not env["vendor_present"]:
        raise ValidationError(f"vendored C2C bridge is missing: {VENDOR_ROOT}")
    if not env["node"] or not env["corepack"]:
        raise ValidationError("Node.js and corepack are required")
    install = _run(["corepack", "pnpm", "install", "--frozen-lockfile"], cwd=VENDOR_ROOT, timeout=timeout)
    if install.returncode != 0:
        raise ValidationError(f"pnpm install failed with exit code {install.returncode}")
    build = _run(["corepack", "pnpm", "build"], cwd=VENDOR_ROOT, timeout=timeout)
    if build.returncode != 0:
        raise ValidationError(f"pnpm build failed with exit code {build.returncode}")
    return {"ok": True, "dist_entry": str(DIST_ENTRY), "built": DIST_ENTRY.exists()}


def run_c2c(args: list[str], *, workspace: str | None = None, timeout: int | None = None) -> int:
    if not DIST_ENTRY.exists():
        raise ValidationError("C2C bridge is not built; run `ccw c2c build` first")
    command = ["node", str(DIST_ENTRY), *args]
    if workspace and not any(item in {"-w", "--workspace"} for item in args):
        command.extend(["--workspace", str(Path(workspace).resolve())])
    env = os.environ.copy()
    if LOCAL_BIN.exists():
        env["PATH"] = str(LOCAL_BIN) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(command, cwd=str(VENDOR_ROOT), text=True, check=False, timeout=timeout, env=env)
    return int(result.returncode)


