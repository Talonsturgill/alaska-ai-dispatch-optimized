# Launch checklist — Alaska.Ai Dispatch routine

Everything installable is automated by `scripts/setup_env.sh`. The ONLY things you set
by hand are the prompt and your own secret upload credential — secrets can't live in a
repo, by design. Five minutes, once.

1. **Create a routine** at [claude.ai/code/routines](https://claude.ai/code/routines).
   Repository: this repo (`alaska-ai-weekly`).

2. **Prompt:** paste the contents of [`docs/ROUTINE_SPEC.md`](ROUTINE_SPEC.md). Pick a model
   (Opus recommended for the producer/critic work).

3. **Environment > Setup script:** `bash scripts/setup_env.sh`
   Installs ffmpeg, pillow/numpy/scipy, edge-tts, kokoro, rclone. Fonts are committed.
   The result is cached, so it doesn't re-run every time.

4. **Environment > Variables** (OPTIONAL — links are already permanent via GitHub; you can skip this):
   - `RCLONE_CONFIG_B64` — base64 of an `rclone.conf` containing a remote named **`dispatch`**
     (Google Drive recommended). This is where the finished video is uploaded so the Gmail
     draft can link a one-click download. Make one locally with `rclone config`, then
     `base64 -w0 ~/.config/rclone/rclone.conf` and paste the result.
   - (Alternative: an S3/R2 public bucket — set `DISPATCH_PUBLIC_BASE` to its public URL.)
   - **You can skip this entirely.** With no secret, `scripts/upload_video.py` hosts the video on the
     repo's `dispatch-media` branch → a PERMANENT raw.githubusercontent.com link, no setup. rclone is
     only worth it if you'd rather not keep the mp4s in the repo.

5. **Connectors:** keep **Gmail** (creates the draft) and **GitHub** (audit PR). Remove the rest.

6. **Schedule:** weekly (Saturday morning). **Network:** Default (Trusted) is enough — cloud
   APIs and the rclone host are reachable.

7. **Run now** to test, then check the drafts in **docket@alaskaaihq.com** (the account the Gmail
   connector authenticates as) for a subject starting `ALASKA.AI · Dispatch ready`. Note the
   separator is a middot, not a dash, so searching for a dash finds nothing.

That's the whole setup. Deps = automated (step 3). Prompt = paste (step 2). Secret = yours (step 4).
The routine handles research → fact-check → produce → review/iterate → deliver on its own.
