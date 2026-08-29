"""Upload the finished Dispatch mp4 -> one-click DIRECT-download URL (last stdout line = URL).

Token-safe: bytes go over the network/git from the container, NEVER through the model as base64.

The canary has exactly one upload destination: the `dispatch-media` branch of
`Talonsturgill/alaska-ai-dispatch-optimized`. There is no rclone, Drive, R2,
S3, temporary-host, or production-repository fallback. A failed canary push is
a failed upload and remains local.

Prints `HOST=permanent` to stderr and self-verifies the URL is an OPENABLE media link
(200 + correct extension + full content-length, not just any 200) before printing it. A --name
without an extension is auto-corrected to the source file's extension, so a hosted link can never
be an extensionless octet-stream blob that won't open.

Usage:
  python scripts/upload_video.py --file out/dispatch/dispatch.mp4 --name dispatch-2026-06-27.mp4
  # --name may omit the extension; it is appended from --file automatically.
"""
import argparse, os, subprocess, sys, tempfile, re, shutil
from pathlib import Path

from canary_guard import require_action, require_canary_origin

MEDIA_BRANCH = "dispatch-media"
MEDIA_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

def sh(cmd, **kw): return subprocess.run(cmd, capture_output=True, text=True, **kw)

def media_email():
    """The owner's commit email, from git config. Never an assistant/Anthropic address."""
    e = sh(["git", "config", "user.email"]).stdout.strip()
    if not e or "anthropic.com" in e.lower():
        raise RuntimeError(
            "upload_video: git config user.email is unset or is an Anthropic address "
            f"({e!r}). CLAUDE.md forbids authoring this repo's commits as Claude/Anthropic. "
            "Set it to the owner's address before uploading media.")
    return e


def via_github(file, name):
    """git-push the file to the dispatch-media branch; return its permanent raw URL."""
    if "DISPATCH_MEDIA_BRANCH" in os.environ:
        raise RuntimeError(
            "DISPATCH_MEDIA_BRANCH overrides are forbidden; the canary branch is fixed"
        )
    name = media_name(name, file)
    root_path = Path(__file__).resolve().parent.parent
    repository = require_canary_origin(root_path)
    require_action("github_media_publish", repository)
    if os.path.getsize(file) > 99 * 1024 * 1024:
        raise RuntimeError("file >99MB exceeds GitHub's push limit; encode a smaller canary artifact")
    root = str(root_path)
    owner, repo = repository.split("/", 1)
    branch = MEDIA_BRANCH
    wt = tempfile.mkdtemp(prefix="media_wt_")
    try:
        sh(["git", "-C", root, "fetch", "origin", branch])
        exists = sh(["git", "-C", root, "rev-parse", "--verify", f"origin/{branch}"]).returncode == 0
        sh(["git", "-C", root, "worktree", "add", "--force", "--detach", wt])
        if exists:
            sh(["git", "-C", wt, "checkout", "-B", branch, f"origin/{branch}"])
        else:
            sh(["git", "-C", wt, "checkout", "--orphan", branch]); sh(["git", "-C", wt, "rm", "-rf", "."])
        os.makedirs(os.path.join(wt, "media"), exist_ok=True)
        shutil.copyfile(file, os.path.join(wt, "media", name))
        sh(["git", "-C", wt, "add", "media/" + name])
        # THE OWNER'S IDENTITY, NOT THE ASSISTANT'S. CLAUDE.md is explicit and permanent:
        # never set a commit author or committer to Claude or any Anthropic identity, in any
        # commit in this repo. This line had noreply@anthropic.com hardcoded, so every media
        # commit on dispatch-media has been authored by an Anthropic address. Read from git
        # config rather than hardcoding again, so the identity lives in one place.
        c = sh(["git", "-C", wt, "-c", f"user.email={media_email()}", "-c", "user.name=Alaska.Ai routine",
                "commit", "-m", f"dispatch media: {name}"])
        if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
            raise RuntimeError("git commit failed: " + (c.stderr or c.stdout)[-300:])
        p = sh(["git", "-C", wt, "push", "-u", "origin", branch])
        if p.returncode != 0: raise RuntimeError("git push failed: " + p.stderr[-300:])
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/media/{name}"
    finally:
        sh(["git", "-C", root, "worktree", "remove", "--force", wt])

def media_name(name, file):
    """Return one conservative media basename with the source extension.

    Separators, traversal markers, absolute paths, control characters, Unicode,
    shell punctuation, and oversized names are refused before any repository or
    filesystem operation. Without an extension,
    raw.githubusercontent serves the file as application/octet-stream with nosniff, so a browser
    downloads an extensionless blob that won't open in any player (the 2026-07-21 bug: a --name
    without '.mp4' shipped a dead link). If --name already ends with the right extension, keep it;
    otherwise append it (never silently host an extensionless or wrong-extension media file)."""
    if not isinstance(name, str) or not name or name != name.strip():
        raise ValueError("media name must be a non-empty canonical basename")
    if name in {".", ".."} or ".." in name or "/" in name or "\\" in name:
        raise ValueError("media name may not contain separators or traversal markers")
    if os.path.isabs(name) or re.match(r"^[A-Za-z]:", name):
        raise ValueError("media name may not be absolute")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in name):
        raise ValueError("media name may not contain control characters")
    ext = os.path.splitext(file)[1]  # e.g. ".mp4" / ".png"
    if ext and not name.lower().endswith(ext.lower()):
        name = name + ext
    if not MEDIA_NAME_RE.fullmatch(name):
        raise ValueError(
            "media name must be 1 to 128 ASCII letters, numbers, dots, underscores, or hyphens"
        )
    return name

def verify(url, file):
    """A link is only 'good' if it will actually OPEN as the media file, which HTTP 200 alone does
    not prove. Check three things off the response headers: (1) 200, (2) the URL path ends with the
    source file's extension (so it downloads/plays as .mp4/.png, not an extensionless blob), and
    (3) the served Content-Length equals the local file size (the whole file is really there, and it
    is not a small HTML error page). Returns (ok, detail)."""
    ext = os.path.splitext(file)[1].lower()
    if ext and not url.lower().split("?")[0].endswith(ext):
        return False, f"URL does not end with '{ext}' (would download as an unopenable file): {url}"
    r = sh(["curl", "-sSLI", "--max-time", "180", url])
    if r.returncode != 0:
        return False, "HEAD request failed: " + (r.stderr or "")[-200:]
    head = r.stdout
    codes = re.findall(r"HTTP/\d(?:\.\d)?\s+(\d{3})", head)
    if not codes or codes[-1] != "200":
        return False, f"HTTP status {codes[-1] if codes else '?'} (expected 200)"
    if re.search(r"(?im)^content-type:\s*text/html", head):
        return False, "served as text/html (looks like an error page, not the media file)"
    m = re.search(r"(?im)^content-length:\s*(\d+)", head)
    if m:
        remote, local = int(m.group(1)), os.path.getsize(file)
        if remote != local:
            return False, f"content-length {remote} != local file size {local} (truncated/wrong upload)"
    return True, "ok"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True); ap.add_argument("--name", default=None)
    ap.add_argument("--no-github", action="store_true",
                    help="disable the sole canary publisher and keep the file local")
    a = ap.parse_args()
    try:
        name = media_name(a.name or os.path.basename(a.file), a.file)
    except ValueError as exc:
        print(f"REFUSING MEDIA NAME: {exc}", file=sys.stderr)
        return 2
    if a.no_github:
        print("CANARY: upload disabled by --no-github; file remains local", file=sys.stderr)
        return 1
    try:
        url, kind = via_github(a.file, name), "permanent"
    except Exception as exc:
        print(f"ERROR: canary GitHub upload failed; no fallback was attempted:\n  {exc}",
              file=sys.stderr)
        return 1
    ok, detail = verify(url, a.file)
    print(f"HOST={kind} VERIFIED={'ok' if ok else 'FAILED'} ({detail})", file=sys.stderr)
    if not ok:
        print(f"WARNING: link is not a valid, openable media URL - do NOT put it in the draft. {detail}",
              file=sys.stderr); sys.exit(3)
    print(url)   # LAST line = the URL the routine captures

if __name__ == "__main__":
    raise SystemExit(main())
