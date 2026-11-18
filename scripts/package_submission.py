"""Package NexTower source and Git history, optionally including an uncommitted working snapshot."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def package(root: Path, output: Path, expected_commits: int | None = None, *, working_tree=False):
    status = git(root, "status", "--porcelain")
    if status and not working_tree:
        raise ValueError(
            "working tree has changes; use --working-tree to include them without committing"
        )
    head = git(root, "rev-parse", "HEAD")
    count = int(git(root, "rev-list", "--count", "HEAD"))
    if expected_commits is not None and count != expected_commits:
        raise ValueError(f"expected {expected_commits} commits, found {count}")
    output = output.resolve()
    checksum_path = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or checksum_path.exists():
        raise FileExistsError("choose a new ZIP path; existing submission files are preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nextower-submission-") as temporary:
        clone = Path(temporary) / "NexTower-Proactive-5G"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(root), str(clone)], check=True
        )
        subprocess.run(["git", "-C", str(clone), "remote", "remove", "origin"], check=True)
        subprocess.run(["git", "-C", str(clone), "gc", "--quiet"], check=True)
        subprocess.run(["git", "-C", str(clone), "fsck", "--full"], check=True, capture_output=True)
        if working_tree:
            # A clean clone supplies only the existing history. Overlay source files separately;
            # this deliberately leaves modifications/deletions/new files uncommitted in the ZIP.
            for name in git(clone, "ls-files").splitlines():
                if not (root / name).exists():
                    (clone / name).unlink(missing_ok=True)
            names = sorted(
                set(
                    git(root, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
                )
            )
            for name in names:
                source = root / name
                if source.is_file():
                    target = clone / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        for directory in (clone / ".git/hooks", clone / ".git/logs"):
            shutil.rmtree(directory, ignore_errors=True)
        files = sorted(
            p for p in clone.rglob("*") if p.is_file() and ".git" not in p.relative_to(clone).parts
        )
        source_hash = hashlib.sha256()
        for path in sorted(
            p for p in (clone / "src/nextower").iterdir() if p.suffix in (".py", ".html")
        ):
            source_hash.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
        manifest = {
            "project": "NexTower",
            "version": "1.0.0",
            "commit_count": count,
            "committed_base": head,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_history_included": True,
            "working_tree_snapshot": working_tree,
            "uncommitted_changes_included": bool(working_tree and status),
            "source_sha256": source_hash.hexdigest(),
            "files": {
                str(p.relative_to(clone)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
            },
        }
        with zipfile.ZipFile(
            output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(clone.rglob("*")):
                if path.is_file():
                    archive.write(path, str(Path(clone.name) / path.relative_to(clone)))
            archive.writestr(
                "NexTower-Submission-Manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP checksum verification failed")
    if git(root, "rev-parse", "HEAD") != head:
        raise ValueError("Git HEAD changed during packaging")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with checksum_path.open("x") as stream:
        stream.write(f"{digest}  {output.name}\n")
    print(
        json.dumps(
            {
                "zip": str(output),
                "bytes": output.stat().st_size,
                "commits": count,
                "uncommitted_snapshot": working_tree,
                "sha256": digest,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("../NexTower-Proactive-5G-Submission.zip")
    )
    parser.add_argument("--expected-commits", type=int)
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Include current tracked and nonignored new files without committing",
    )
    args = parser.parse_args()
    try:
        package(
            Path(__file__).resolve().parents[1],
            args.output,
            args.expected_commits,
            working_tree=args.working_tree,
        )
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"package_submission: {exc}\n")


if __name__ == "__main__":
    main()
