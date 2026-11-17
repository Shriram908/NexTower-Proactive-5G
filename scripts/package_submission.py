"""Create a portable, checksummed submission from committed files and real Git history."""

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


def package(root: Path, output: Path, expected_commits: int | None = None):
    if git(root, "status", "--porcelain"):
        raise ValueError("commit all submission changes first; working tree must be clean")
    count = int(git(root, "rev-list", "--count", "HEAD"))
    if expected_commits is not None and count != expected_commits:
        raise ValueError(f"expected {expected_commits} commits, found {count}")
    output = output.resolve()
    checksum_path = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or checksum_path.exists():
        raise FileExistsError("choose a new ZIP path; existing submission files are preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoverai-submission-") as temporary:
        clone = Path(temporary) / "HandoverAI-Proactive-5G"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(root), str(clone)], check=True
        )
        subprocess.run(["git", "-C", str(clone), "remote", "remove", "origin"], check=True)
        subprocess.run(["git", "-C", str(clone), "gc", "--quiet"], check=True)
        subprocess.run(["git", "-C", str(clone), "fsck", "--full"], check=True, capture_output=True)
        for directory in (clone / ".git/hooks", clone / ".git/logs"):
            shutil.rmtree(directory, ignore_errors=True)
        names = git(clone, "ls-files").splitlines()
        manifest = {
            "project": clone.name,
            "version": "1.0.0",
            "commit_count": count,
            "head_commit": git(clone, "rev-parse", "HEAD"),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_history_included": True,
            "files": {
                name: hashlib.sha256((clone / name).read_bytes()).hexdigest() for name in names
            },
        }
        with zipfile.ZipFile(
            output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(clone.rglob("*")):
                if path.is_file():
                    archive.write(path, str(Path(clone.name) / path.relative_to(clone)))
            archive.writestr(
                "HandoverAI-Submission-Manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP checksum verification failed")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with checksum_path.open("x") as stream:
        stream.write(f"{digest}  {output.name}\n")
    print(
        json.dumps(
            {
                "zip": str(output),
                "bytes": output.stat().st_size,
                "commits": count,
                "sha256": digest,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("../HandoverAI-Proactive-5G-Submission.zip")
    )
    parser.add_argument("--expected-commits", type=int)
    args = parser.parse_args()
    try:
        package(Path(__file__).resolve().parents[1], args.output, args.expected_commits)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"package_submission: {exc}\n")


if __name__ == "__main__":
    main()
