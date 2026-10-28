"""Serve the newest published copy of each release archive."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path


def select_archives(releases):
    selected = {}
    for release in sorted(releases, key=lambda item: (item["published_at"] or "", item["id"]), reverse=True):
        if release["draft"] or release["prerelease"]:
            continue
        for asset in release["assets"]:
            name = asset["name"]
            if not name.endswith(".tar.gz"):
                continue
            root = name.removesuffix(".tar.gz")
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", root):
                raise ValueError(f"Invalid archive root: {name}")
            selected.setdefault(root, (release, asset))
    return selected


def extract_archive(archive, destination):
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"Archive must contain only files and directories: {member.name}")
            if Path(member.name).is_absolute() or ".." in Path(member.name).parts:
                raise ValueError(f"Archive path escapes its root: {member.name}")
        bundle.extractall(destination, filter="data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args()
    if not args.repo:
        parser.error("Pass --repo or set GITHUB_REPOSITORY")
    pages = json.loads(subprocess.check_output([
        "gh", "api", "--paginate", "--slurp", f"repos/{args.repo}/releases",
    ]))
    args.output.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as temporary:
        for root, (release, asset) in select_archives([release for page in pages for release in page]).items():
            print(f"/{root}/ ← {release['tag_name']} ({release['published_at']})", flush=True)
            subprocess.run([
                "gh", "release", "download", release["tag_name"], "--repo", args.repo,
                "--pattern", asset["name"], "--dir", temporary,
            ], check=True)
            archive = Path(temporary) / asset["name"]
            if asset.get("digest"):
                with archive.open("rb") as file:
                    digest = "sha256:" + hashlib.file_digest(file, "sha256").hexdigest()
                if digest != asset["digest"]:
                    raise ValueError(f"Checksum mismatch: {asset['name']}")
            extract_archive(archive, args.output / root)
    (args.output / ".nojekyll").touch()


if __name__ == "__main__":
    main()
