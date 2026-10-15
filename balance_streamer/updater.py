"""Check GitHub for a newer release and update a git copy of the app to it.

Checking asks GitHub's public API for the latest *release* of this repository (no
account needed, nothing about you is sent beyond a normal web request). It only
happens when you press "Check for Updates".

Updating works for copies made with ``git clone``: it fetches the release tag,
moves this folder to it (fast-forward only, so local work is never overwritten),
then reinstalls the requirements. If reinstalling fails, the folder is moved back.
Unreleased work on ``main`` is never pulled in. Standalone (PyInstaller) builds and
ZIP downloads can't update themselves; they get a link to the release page.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import __version__
from .paths import REPO_DIR

log = logging.getLogger(__name__)

REPO = "brandonbtm29/Balance-Streamer-GUI"
API = "https://api.github.com/repos/{repo}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
_VERSION = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")


def parse_version(text):
    """'v1.2.0' -> (1, 2, 0). Pre-releases ('1.2.0-rc1') and other tags give None."""
    m = _VERSION.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def is_newer(candidate, current=__version__):
    a, b = parse_version(candidate), parse_version(current)
    return a is not None and b is not None and a > b


@dataclass
class Release:
    version: str  # "1.1.0"
    tag: str  # "v1.1.0"
    name: str
    notes: str
    url: str


def latest_release(repo=REPO, timeout=10, opener=urllib.request.urlopen):
    """The newest published release on GitHub. Raises LookupError with a plain message."""
    request = urllib.request.Request(  # noqa: S310 - fixed https:// URL
        API.format(repo=repo),
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"BalanceStreamer/{__version__}"},
    )
    try:
        with opener(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise LookupError("No releases have been published on GitHub yet.") from e
        if e.code == 403:
            raise LookupError("GitHub is limiting requests right now. Try again in an hour.") from e
        raise LookupError(f"GitHub answered with an error ({e.code}).") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LookupError("Couldn't reach GitHub. Check the internet connection.") from e
    except ValueError as e:
        raise LookupError("GitHub sent an answer that couldn't be read.") from e

    tag = str(data.get("tag_name") or "")
    version = parse_version(tag)
    if version is None:
        raise LookupError(f"The latest release tag {tag!r} isn't a version number.")
    return Release(
        version=".".join(map(str, version)),
        tag=tag,
        name=str(data.get("name") or tag),
        notes=str(data.get("body") or ""),
        url=str(data.get("html_url") or RELEASES_PAGE),
    )


# --- updating a git copy ---------------------------------------------------------------


def _run(cmd, cwd, timeout=120):
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: no console pops up
    return subprocess.run(  # noqa: S603 - fixed commands, no shell
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        **kwargs,
    )


def _git(root, *args, timeout=120):
    return _run(["git", *args], root, timeout)


@dataclass
class Readiness:
    ok: bool
    reason: str = ""


def update_readiness(root=REPO_DIR):
    """Can this copy update itself? If not, say why in plain words."""
    if getattr(sys, "frozen", False):
        return Readiness(False, "This is a standalone build. Download the new version from the release page.")
    if not os.path.isdir(os.path.join(root, ".git")):
        return Readiness(
            False,
            "This copy wasn't downloaded with git (for example it came from a ZIP file), so it "
            "can't update itself. Download the new version from the release page.",
        )
    if shutil.which("git") is None:
        return Readiness(False, "Git isn't installed on this computer, so the app can't update itself.")
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        return Readiness(False, "This folder's git information looks broken:\n" + status.stderr.strip()[:300])
    if status.stdout.strip():
        changed = ", ".join(line[3:] for line in status.stdout.splitlines()[:5])
        return Readiness(
            False,
            "Some of the app's own files were changed in this folder, so updating could overwrite "
            f"them ({changed}). Commit or undo those changes first.",
        )
    return Readiness(True)


@dataclass
class UpdateResult:
    ok: bool
    message: str


def default_install_command():
    return [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"]


def update_to(tag, root=REPO_DIR, install_command=None, progress=None):
    """Move this git copy to release ``tag`` and reinstall its requirements.

    Rolls back to the previous version if any step after moving fails.
    ``progress`` is called with short status messages.
    """
    say = progress or (lambda _msg: None)
    install_command = install_command or default_install_command()

    old = _git(root, "rev-parse", "HEAD")
    if old.returncode != 0:
        return UpdateResult(False, "Couldn't read this folder's current version:\n" + old.stderr.strip())
    old_head = old.stdout.strip()

    say("Downloading from GitHub…")
    fetch = _git(root, "fetch", "--tags", "--force", "origin", timeout=300)
    if fetch.returncode != 0:
        return UpdateResult(False, "Couldn't download the update:\n" + fetch.stderr.strip()[:500])
    if _git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}").returncode != 0:
        return UpdateResult(False, f"The release tag {tag} wasn't found on the remote.")

    say(f"Switching to {tag}…")
    merge = _git(root, "merge", "--ff-only", tag)
    if merge.returncode != 0:
        return UpdateResult(
            False,
            "This copy has commits that aren't in the release, so it can't move to it without "
            "losing them. Update it with git yourself.\n\n" + merge.stderr.strip()[:500],
        )

    say("Installing requirements… (this can take a minute)")
    try:
        install = _run(install_command, root, timeout=900)
        failed = install.returncode != 0
        detail = (install.stderr or install.stdout).strip()[-800:]
    except (OSError, subprocess.TimeoutExpired) as e:
        failed, detail = True, str(e)
    if failed:
        log.error("Installing requirements failed; going back to %s:\n%s", old_head, detail)
        back = _git(root, "reset", "--keep", old_head)
        note = "" if back.returncode == 0 else "\n\nGoing back also failed: " + back.stderr.strip()
        return UpdateResult(
            False,
            "Installing the new requirements failed, so the app was left on the old version."
            + note
            + "\n\n"
            + detail,
        )

    log.info("Updated from %s to %s", old_head[:10], tag)
    return UpdateResult(True, f"Updated to {tag}.")
