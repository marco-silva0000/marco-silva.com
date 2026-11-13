"""Application version and git commit hash resolution."""

import os
import subprocess
from pathlib import Path

# Base version counter incremented across homelab deployments
VERSION_COUNTER = 142


def get_git_commit_hash(base_dir: str = None) -> str:
    """Retrieve git short commit hash, reading .git directly or invoking git CLI."""
    if not base_dir:
        base_dir = str(Path(__file__).resolve().parent.parent)

    # 1. Direct .git inspection (works in containers without git CLI installed)
    git_dir = os.path.join(base_dir, ".git")
    if os.path.exists(git_dir):
        try:
            head_path = os.path.join(git_dir, "HEAD")
            if os.path.exists(head_path):
                with open(head_path, "r", encoding="utf-8") as f:
                    ref = f.read().strip()
                if ref.startswith("ref:"):
                    ref_rel = ref.split()[1]
                    ref_path = os.path.join(git_dir, ref_rel)
                    if os.path.exists(ref_path):
                        with open(ref_path, "r", encoding="utf-8") as f:
                            return f.read().strip()[:7]
                    # Packed-refs fallback
                    packed_path = os.path.join(git_dir, "packed-refs")
                    if os.path.exists(packed_path):
                        with open(packed_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#") and line.endswith(ref_rel):
                                    return line.split()[0][:7]
                elif len(ref) >= 7:
                    return ref[:7]
        except Exception:
            pass

    # 2. Try git CLI if available
    try:
        res = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=base_dir,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if res:
            return res[:7]
    except Exception:
        pass

    # 3. Read VERSION file if present
    version_file = os.path.join(base_dir, "VERSION")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                parts = f.read().strip().split("-")
                if len(parts) > 1:
                    return parts[-1][:7]
        except Exception:
            pass

    return "unknown"


def get_commit_count(base_dir: str = None) -> int:
    """Retrieve total commit count from git or default counter."""
    if not base_dir:
        base_dir = str(Path(__file__).resolve().parent.parent)

    try:
        res = (
            subprocess.check_output(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=base_dir,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if res and res.isdigit():
            return int(res)
    except Exception:
        pass

    # Check VERSION file for fallback count
    version_file = os.path.join(base_dir, "VERSION")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                content = f.read().strip().lstrip("v")
                count_str = content.split("-")[0]
                if count_str.isdigit():
                    return int(count_str)
        except Exception:
            pass

    return VERSION_COUNTER


def get_version_info(base_dir: str = None) -> dict:
    """Return dictionary with version counter, commit hash, and display string."""
    commit = get_git_commit_hash(base_dir)
    count = get_commit_count(base_dir)
    return {
        "version": f"v{count}",
        "commit": commit,
        "display": f"v{count} ({commit})",
    }
