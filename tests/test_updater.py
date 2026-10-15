"""The updater: reading GitHub's answer, and moving a git copy to a release tag."""

import io
import json
import shutil
import ssl
import subprocess
import sys
import urllib.error

import pytest

from balance_streamer import updater


@pytest.mark.parametrize(
    ("text", "expected"),
    [("v1.2.3", (1, 2, 3)), ("1.2", (1, 2, 0)), ("v1.2.0-rc1", None), ("latest", None)],
)
def test_parse_version(text, expected):
    assert updater.parse_version(text) == expected


def test_is_newer():
    assert updater.is_newer("v1.10.0", "1.9.9")
    assert not updater.is_newer("v1.0.0", "1.0.0")
    assert not updater.is_newer("nightly", "1.0.0")


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_latest_release_reads_github_answer():
    body = {"tag_name": "v9.8.7", "name": "Balance Streamer 9.8.7", "body": "Notes", "html_url": "https://x"}
    release = updater.latest_release(
        opener=lambda req, timeout, context: _Response(json.dumps(body).encode())
    )
    assert release == updater.Release("9.8.7", "v9.8.7", "Balance Streamer 9.8.7", "Notes", "https://x")


def test_latest_release_explains_errors():
    def no_releases(req, timeout, context):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    def offline(req, timeout, context):
        raise urllib.error.URLError("no network")

    with pytest.raises(LookupError, match="No releases"):
        updater.latest_release(opener=no_releases)

    def bad_certificate(req, timeout, context):
        raise urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed"))

    with pytest.raises(LookupError, match="Couldn't reach GitHub"):
        updater.latest_release(opener=offline)
    with pytest.raises(LookupError, match="secure connection"):
        updater.latest_release(opener=bad_certificate)


# --- updating a real (temporary) git copy --------------------------------------------------

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
GIT_ID = ["-c", "user.name=Test", "-c", "user.email=test@example.com"]
GIT_ID += ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]


def git(cwd, *args):
    result = subprocess.run(["git", *GIT_ID, *args], cwd=cwd, capture_output=True, text=True)  # noqa: S603, S607
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def copies(tmp_path):
    """An 'upstream' repo with releases v1.0.0 and v1.1.0, and a clone sitting at v1.0.0."""
    up = tmp_path / "upstream"
    up.mkdir()
    git(up, "init", "-q")
    (up / "app.txt").write_text("version 1.0.0\n")
    git(up, "add", "app.txt")
    git(up, "commit", "-q", "-m", "1.0.0")
    git(up, "tag", "-a", "v1.0.0", "-m", "1.0.0")
    (up / "app.txt").write_text("version 1.1.0\n")
    git(up, "commit", "-q", "-am", "1.1.0")
    git(up, "tag", "-a", "v1.1.0", "-m", "1.1.0")
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(up), str(clone))
    git(clone, "reset", "-q", "--hard", "v1.0.0")
    return up, clone


OK = [sys.executable, "-c", "pass"]
FAILS = [sys.executable, "-c", "import sys; sys.exit('pip broke')"]


@needs_git
def test_update_moves_to_the_release(copies):
    _, clone = copies
    assert updater.update_readiness(str(clone)).ok
    result = updater.update_to("v1.1.0", root=str(clone), install_command=OK)
    assert result.ok, result.message
    assert (clone / "app.txt").read_text() == "version 1.1.0\n"


@needs_git
def test_failed_install_rolls_back(copies):
    _, clone = copies
    result = updater.update_to("v1.1.0", root=str(clone), install_command=FAILS)
    assert not result.ok
    assert "old version" in result.message
    assert (clone / "app.txt").read_text() == "version 1.0.0\n"


@needs_git
def test_local_commits_are_never_overwritten(copies):
    _, clone = copies
    (clone / "mine.txt").write_text("my work\n")
    git(clone, "add", "mine.txt")
    git(clone, "commit", "-q", "-m", "local work")
    result = updater.update_to("v1.1.0", root=str(clone), install_command=OK)
    assert not result.ok
    assert (clone / "mine.txt").exists()
    assert (clone / "app.txt").read_text() == "version 1.0.0\n"


@needs_git
def test_edited_files_block_the_update(copies):
    _, clone = copies
    (clone / "app.txt").write_text("edited by hand\n")
    ready = updater.update_readiness(str(clone))
    assert not ready.ok
    assert "app.txt" in ready.reason


def test_zip_copies_cannot_update(tmp_path):
    ready = updater.update_readiness(str(tmp_path))
    assert not ready.ok
    assert "release page" in ready.reason


def test_update_panel_builds(window):
    panel = window.tabs.widget(0).update_panel
    assert panel.btn_check.text() == "Check for Updates"
