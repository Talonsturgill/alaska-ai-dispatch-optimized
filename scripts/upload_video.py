"""Upload the finished Dispatch mp4 -> one-click DIRECT-download URL (last stdout line = URL).

Token-safe: bytes go over the network/git from the container, NEVER through the model as base64.

Order of preference (so delivery is PERMANENT by default with ZERO setup):
  1) rclone remote (PERMANENT) when RCLONE_CONFIG_B64 / RCLONE_CONFIG is set (Drive / S3 / R2 ...).
  2) GITHUB media branch (PERMANENT, default, no credentials): git-push the file to the
     `dispatch-media` branch of this repo -> a permanent raw.githubusercontent.com download URL.
     Keep each file < 100 MB (GitHub's hard push limit) — encode the hosted cut accordingly.
  3) NO-AUTH temporary host (tmpfiles.org, ~1h) — last resort if the git push fails.

Prints `HOST=permanent|temporary` to stderr and self-verifies the URL is an OPENABLE media link
(200 + correct extension + full content-length, not just any 200) before printing it. A --name
without an extension is auto-corrected to the source file's extension, so a hosted link can never
be an extensionless octet-stream blob that won't open.

Usage:
  python scripts/upload_video.py --file out/dispatch/dispatch.mp4 --name dispatch-2026-06-27.mp4
  # --name may omit the extension; it is appended from --file automatically.
"""
import argparse, base64, os, subprocess, sys, tempfile, re, json, shutil
from pathlib import Path

from canary_guard import require_action, require_canary_origin

def sh(cmd, **kw): return subprocess.run(cmd, capture_output=True, text=True, **kw)
def have_rclone(): return sh(["which", "rclone"]).returncode == 0
def rclone_configured(): return bool(os.environ.get("RCLONE_CONFIG_B64") or os.environ.get("RCLONE_CONFIG"))

def ensure_config():
    b64 = os.environ.get("RCLONE_CONFIG_B64")
    if b64:
        path = os.path.join(tempfile.gettempdir(), "rclone_dispatch.conf")
        open(path, "wb").write(base64.b64decode(b64)); os.environ["RCLONE_CONFIG"] = path
    return os.environ.get("RCLONE_CONFIG")

def to_direct(url):
    m = re.search(r"/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if "drive.google.com" in url and m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return url

def via_rclone(file, name):
    ensure_config()
    remote = os.environ.get("DISPATCH_REMOTE", "dispatch:"); dest = f"{remote}{name}"
    require_action("external_media_upload", dest)
    up = sh(["rclone", "copyto", file, dest, "--no-traverse"])
    if up.returncode != 0: raise RuntimeError("rclone upload failed: " + up.stderr[-400:])
    pub = os.environ.get("DISPATCH_PUBLIC_BASE")
    if pub: return f"{pub.rstrip('/')}/{name}"
    ln = sh(["rclone", "link", dest])
    if ln.returncode != 0: raise RuntimeError("rclone link failed: " + ln.stderr[-400:])
    return to_direct(ln.stdout.strip())

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
    if os.path.getsize(file) > 99 * 1024 * 1024:
        raise RuntimeError("file >99MB exceeds GitHub's push limit; encode smaller or use rclone")
    root = sh(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    if not root: raise RuntimeError("not inside a git repo")
    origin = sh(["git", "-C", root, "remote", "get-url", "origin"]).stdout.strip()
    m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", origin)
    if not m: raise RuntimeError("cannot parse owner/repo from origin: " + origin)
    owner, repo = m.group(1), m.group(2)
    require_canary_origin(Path(root))
    require_action("github_media_publish", f"{owner}/{repo}")
    branch = os.environ.get("DISPATCH_MEDIA_BRANCH", "dispatch-media")
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

def via_tmpfiles(file):
    require_action("external_media_upload", "https://tmpfiles.org")
    r = sh(["curl", "-sS", "--max-time", "300", "-F", f"file=@{file}", "https://tmpfiles.org/api/v1/upload"])
    if r.returncode != 0: raise RuntimeError("tmpfiles curl failed: " + (r.stderr or "")[-300:])
    try: u = json.loads(r.stdout)["data"]["url"]
    except Exception: raise RuntimeError("tmpfiles parse failed: " + (r.stdout or "")[:200])
    return u.replace("tmpfiles.org/", "tmpfiles.org/dl/")

def ensure_ext(name, file):
    """Force the hosted name to carry the SOURCE file's real extension. Without an extension,
    raw.githubusercontent serves the file as application/octet-stream with nosniff, so a browser
    downloads an extensionless blob that won't open in any player (the 2026-07-21 bug: a --name
    without '.mp4' shipped a dead link). If --name already ends with the right extension, keep it;
    otherwise append it (never silently host an extensionless or wrong-extension media file)."""
    ext = os.path.splitext(file)[1]  # e.g. ".mp4" / ".png"
    if ext and not name.lower().endswith(ext.lower()):
        name = name + ext
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
    ap.add_argument("--no-github", action="store_true", help="skip the GitHub media-branch host")
    a = ap.parse_args()
    name = ensure_ext(a.name or os.path.basename(a.file), a.file)
    url = None; kind = None; errs = []
    if rclone_configured() and have_rclone():
        try: url, kind = via_rclone(a.file, name), "permanent"
        except Exception as e: errs.append("rclone: " + str(e))
    if not url and not a.no_github:
        try: url, kind = via_github(a.file, name), "permanent"
        except Exception as e: errs.append("github: " + str(e))
    if not url:
        try: url, kind = via_tmpfiles(a.file), "temporary"
        except Exception as e: errs.append("tmpfiles: " + str(e))
    if not url:
        print("ERROR: all upload hosts failed:\n  " + "\n  ".join(errs), file=sys.stderr); sys.exit(1)
    if errs: print("(fell through: " + "; ".join(errs) + ")", file=sys.stderr)
    ok, detail = verify(url, a.file)
    print(f"HOST={kind} VERIFIED={'ok' if ok else 'FAILED'} ({detail})", file=sys.stderr)
    if not ok:
        print(f"WARNING: link is not a valid, openable media URL - do NOT put it in the draft. {detail}",
              file=sys.stderr); sys.exit(3)
    print(url)   # LAST line = the URL the routine captures

if __name__ == "__main__":
    main()
