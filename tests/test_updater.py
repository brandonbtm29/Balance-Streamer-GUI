"""The updater: reading GitHub's answer, and moving a git copy to a release tag."""

import io
import json
import os
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


REAL_RELEASE_SIGNED = updater.release_signed


@pytest.fixture
def copies(tmp_path, monkeypatch):
    """An 'upstream' repo with releases v1.0.0 and v1.1.0, and a clone sitting at v1.0.0. These
    throwaway releases aren't signed, so the signature check passes them here; the tests at the end
    use the real one."""
    monkeypatch.setattr(updater, "release_signed", lambda root, ref: "")
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


# --- git's environment ---------------------------------------------------------------------


def test_git_and_pip_run_without_the_callers_git_variables(monkeypatch, tmp_path):
    """GIT_CONFIG_* can make git run commands and GIT_DIR points it at another repo: none come along."""
    for name, value in {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "evil",
        "git_dir": "/elsewhere",
        "GIT_SSH_COMMAND": "evil",
    }.items():
        monkeypatch.setenv(name, value)
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(updater.subprocess, "run", fake_run)
    updater._run(["git", "status"], str(tmp_path))
    env = seen["env"]
    assert not [k for k in env if k.upper().startswith("GIT_") and k != "GIT_TERMINAL_PROMPT"]
    assert env["GIT_TERMINAL_PROMPT"] == "0" and "PATH" in {k.upper() for k in env}
    assert seen["stdin"] == subprocess.DEVNULL


# --- signed releases -------------------------------------------------------------------------


def _signers_file(folder, text='me@example.com namespaces="git" ssh-ed25519 AAAA\n'):
    (folder / ".github").mkdir(parents=True, exist_ok=True)
    (folder / ".github" / "allowed_signers").write_text(text)


@pytest.mark.parametrize(
    ("letter", "code", "words"),
    [
        ("N", 0, "isn't signed"),
        ("U", 0, "key that isn't on the trusted list"),
        ("B", 0, "bad signature"),
        ("E", 0, "couldn't be checked"),
        ("R", 0, "revoked key"),
        ("", 0, "couldn't be checked"),  # git printed nothing
        ("G", 128, "couldn't be checked"),  # git failed
    ],
)
def test_only_good_signatures_pass(tmp_path, monkeypatch, letter, code, words):
    _signers_file(tmp_path)
    monkeypatch.setattr(updater, "_ssh_keygen", lambda: "/usr/bin/ssh-keygen")
    calls = []

    def fake_git(root, *args, timeout=120):
        calls.append(args)
        return subprocess.CompletedProcess(args, code, stdout=letter + "\n", stderr="")

    monkeypatch.setattr(updater, "_git", fake_git)
    why = updater.release_signed(str(tmp_path), "abc123")
    assert words in why and "allowed_signers" in why and "wasn't installed" in why
    args = calls[0]
    assert args[0] == "-c" and args[-1] == "abc123" and "--format=%G?" in args
    assert f"gpg.ssh.allowedSignersFile={tmp_path / '.github' / 'allowed_signers'}" in args  # this copy's own
    assert "gpg.ssh.program=/usr/bin/ssh-keygen" in args

    monkeypatch.setattr(
        updater, "_git", lambda root, *args, timeout=120: subprocess.CompletedProcess(args, 0, "G\n", "")
    )
    assert updater.release_signed(str(tmp_path), "abc123") == ""


def test_no_list_or_no_ssh_keygen_means_no_update(tmp_path, monkeypatch):
    def fake_git(root, *args, timeout=120):
        raise AssertionError("git shouldn't run")

    monkeypatch.setattr(updater, "_git", fake_git)
    assert "has no .github/allowed_signers" in updater.release_signed(str(tmp_path), "abc123")
    _signers_file(tmp_path)
    monkeypatch.setattr(updater, "_ssh_keygen", lambda: None)
    assert "ssh-keygen isn't installed" in updater.release_signed(str(tmp_path), "abc123")


@needs_git
def test_update_refuses_a_release_that_is_not_signed(copies, monkeypatch):
    _, clone = copies
    monkeypatch.setattr(updater, "release_signed", REAL_RELEASE_SIGNED)  # this clone has no allowed_signers
    result = updater.update_to("v1.1.0", root=str(clone), install_command=OK)
    assert not result.ok and "has no .github/allowed_signers" in result.message
    monkeypatch.setattr(
        updater, "release_signed", lambda root, ref: "The release isn't signed, so it wasn't installed."
    )
    result = updater.update_to("v1.1.0", root=str(clone), install_command=OK)
    assert not result.ok and result.message.startswith("Release v1.1.0 isn't signed")
    assert (clone / "app.txt").read_text() == "version 1.0.0\n"


def _key(tmp_path, name):
    key = tmp_path / name
    subprocess.run(  # noqa: S603 - fixed arguments
        [updater._ssh_keygen(), "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)],
        check=True,
        capture_output=True,
    )
    return key


def _signed_release(up, version, key, signers_text=None):
    """A release whose commit is signed with `key` (and may change allowed_signers)."""
    (up / "app.txt").write_text(f"version {version}\n")
    if signers_text is not None:
        _signers_file(up, signers_text)
    git(up, "add", "-A")
    sign = [
        "-c",
        "gpg.format=ssh",
        "-c",
        f"user.signingkey={key}",
        "-c",
        f"gpg.ssh.program={updater._ssh_keygen()}",
    ]
    result = subprocess.run(  # noqa: S603, S607 - fixed arguments
        ["git", *GIT_ID, *sign, "commit", "-S", "-q", "-m", version], cwd=up, capture_output=True, text=True
    )
    if result.returncode and os.name == "nt":
        pytest.skip(f"can't sign a test commit here: {result.stderr.strip()[:200]}")
    assert result.returncode == 0, result.stderr
    git(up, "tag", "-a", f"v{version}", "-m", version)


def _unsigned_release(up, version):
    (up / "app.txt").write_text(f"version {version}\n")
    git(up, "commit", "-q", "-am", version)
    git(up, "tag", "-a", f"v{version}", "-m", version)


@needs_git
@pytest.mark.skipif(updater._ssh_keygen() is None, reason="OpenSSH's ssh-keygen not installed")
def test_real_signatures(tmp_path):
    """Signed with a listed key: installs. Unsigned, signed by an unlisted key, or a release that lists its
    own new key: refused, because the check uses this copy's list, not the downloaded one."""
    trusted, stranger = _key(tmp_path, "trusted"), _key(tmp_path, "stranger")
    line = 'me@example.com namespaces="git" {}'.format
    trusted_line = line((tmp_path / "trusted.pub").read_text().strip())
    stranger_line = line((tmp_path / "stranger.pub").read_text().strip())
    up = tmp_path / "upstream"
    up.mkdir()
    git(up, "init", "-q")
    _signed_release(up, "1.0.0", trusted, signers_text=trusted_line + "\n")
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(up), str(clone))

    _signed_release(up, "1.1.0", trusted)
    result = updater.update_to("v1.1.0", root=str(clone), install_command=OK)
    assert result.ok, result.message

    _unsigned_release(up, "1.2.0")
    result = updater.update_to("v1.2.0", root=str(clone), install_command=OK)
    assert not result.ok and "Release v1.2.0 isn't signed" in result.message

    _signed_release(up, "1.3.0", stranger)
    result = updater.update_to("v1.3.0", root=str(clone), install_command=OK)
    assert not result.ok and "isn't on the trusted list" in result.message

    # A release that adds its own key to the list is still checked against this copy's list
    _signed_release(up, "1.4.0", stranger, signers_text=trusted_line + "\n" + stranger_line + "\n")
    result = updater.update_to("v1.4.0", root=str(clone), install_command=OK)
    assert not result.ok and "isn't on the trusted list" in result.message
    assert (clone / "app.txt").read_text() == "version 1.1.0\n"
