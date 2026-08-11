# Autonomous posting: what each platform needs, and how to get the keys

Research done 2026-08-09. Everything below was checked against current docs rather than memory,
because these APIs change constantly. Where a number came from a third-party write-up rather than
the platform's own docs it is marked **(verify at signup)** — treat those as directionally right
and confirm on the day.

---

## The headline

**The platforms are not remotely equal in effort, and the order matters.** Two of them we can turn
on this week. Three need an approval process measured in weeks. One now costs money per post.

| Platform | Can we post video? | Approval needed | Realistic time to live |
| --- | --- | --- | --- |
| **LinkedIn (your personal profile)** | Yes | **None. Self-serve.** | **Same day** |
| **X / Twitter** | Yes | None, but **paid** | Same day once billing is on |
| **TikTok** | Yes, but see below | **Audit** for public posts | 2 to 6 weeks |
| **YouTube (Shorts)** | Yes, but see below | **Audit** or uploads lock private | 2 to 6 weeks |
| **Instagram (Reels)** | Yes | **Meta App Review + Business Verification** | 2 to 6 weeks |
| **Facebook Page** | Yes | Same Meta review as above | Same submission as Instagram |
| **LinkedIn company page** | Yes | **Community Management API**, two-tier review | Longest of all |

**My recommendation: do LinkedIn personal first, alone.** It is the platform you actually care
about most, it needs no permission from anyone, and it will prove the whole posting path end to
end before we spend weeks in review queues. Then submit the three audits in parallel, since they
all take weeks of waiting rather than weeks of work.

---

## 1. LinkedIn, personal profile — the easy win

**This is the one that surprised me and it is genuinely good news.** Posting *video* to your own
profile uses the `Share on LinkedIn` product, which grants the `w_member_social` scope. It is
listed as self-serve: you add the product in the developer portal and it is enabled, with no
review, no legal-entity check, and no screencast. Video is explicitly supported through the
`feedshare-video` upload recipe.

Rate limit is **150 requests per member per day**, which is enormous next to one Dispatch.

### What you do

1. Go to <https://www.linkedin.com/developers/apps> and click **Create app**.
2. It will ask you to associate the app with a **LinkedIn Page**. You need one, and you need to be
   an admin of it. This is only to create the app; it does not mean you are posting to the Page.
3. On the app's **Products** tab, add:
   - **Share on LinkedIn** (this grants `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (needed to resolve your Person URN)
4. On the **Auth** tab, copy the **Client ID** and **Client Secret**, and add a redirect URL. Use
   `http://localhost:8080/callback` — we only need it once, to mint a token.
5. Send me the Client ID and Secret. I will write a one-time script that opens the consent URL,
   you approve it in the browser, and it exchanges the code for a token.

### The one catch

LinkedIn member access tokens last **60 days** and refresh tokens are **not** granted to every
app by default. So this will need re-authorising periodically. I will make the routine detect an
expiring token and email you a re-auth link well before it dies, rather than discovering it at
post time.

### If you want it on the Alaska.Ai *company page* instead

Different product entirely: **Community Management API**. It is a vetted product requiring a
registered legal entity (LLC, corp, non-profit — not an individual), a verified Page, a
super-admin of that Page approving the request, a business email verification, and a **two-tier**
review where Standard Tier requires a screencast demonstrating each use case. Development Tier
comes first with lower limits (500 requests/app, 100/member).

Worth doing eventually. Not worth blocking the first working version on.

---

## 2. X / Twitter — works immediately, but now costs per post

X moved to **pay-per-use pricing in February 2026** and **discontinued the free tier**.
**(verify at signup)** Current rates reported:

- **$0.015 per post created**
- **$0.20 per post if it contains a link**
- $0.005 per post read

Legacy Basic ($200/mo) and Pro ($5,000/mo) remain only for people already subscribed.

**A useful accident:** the credits work we just shipped puts `alaskaaihq.com` *inside the video*
rather than in the post text. If the post body carries no URL, we pay $0.015 instead of $0.20 — a
13x difference. Worth deliberately keeping links out of the X copy.

At one Dispatch a day with no link, this is roughly **$0.45/month**. Trivial.

### What you do

1. Go to <https://developer.x.com>, sign in as the Alaska.Ai account, create a Project and an App.
2. Add a payment method — there is no free tier to fall back on.
3. In the app's **Keys and tokens**, generate: **API Key**, **API Key Secret**, **Access Token**,
   **Access Token Secret**. Set app permissions to **Read and Write** *before* generating the
   access token, otherwise the token is read-only and you will have to regenerate it.
4. Send me all four.

X tokens do not expire the way LinkedIn's do, which makes this the lowest-maintenance platform.

---

## 3. TikTok — the audit is the whole story

TikTok has two posting modes and the difference is severe:

- **`video.upload`** — lands in the creator's TikTok inbox as a draft. You still tap to publish.
  Available without audit.
- **`video.publish`** — posts directly, publicly. **Requires passing TikTok's Content Posting
  audit.**

**Until the audit passes, direct posts are forced to `SELF_ONLY`** — visible to nobody but you.
So an unaudited integration is not autonomous; it is a slightly faster manual workflow.
**(verify at signup)**

### What you do

1. Register at <https://developers.tiktok.com>, create an app.
2. Add the **Content Posting API** product and request the `video.publish` scope.
3. Submit for audit. It wants a demonstration that your flow is compliant — notably that the
   creator sees and confirms the content, and that you display the required disclosures.
4. Expect weeks.

**Honest read:** TikTok's audit is designed around apps where a *human user* is publishing their
own content through your tool. Ours is a routine publishing on your behalf. That is a legitimate
use case and people do get approved for it, but be ready to describe it accurately in the
application rather than dressing it up as a consumer app. I would rather we get rejected once and
resubmit honestly than get approved on a description that does not match what we do.

---

## 4. YouTube Shorts — same shape of problem as TikTok

Uploading is technically easy (Data API v3 `videos.insert`). The catch is identical in spirit:

**Videos uploaded via an unverified API project are locked to private**, and the creator gets an
email saying so. Lifting it requires a **compliance audit** of the project.

Quota: the docs note the cost of an upload was **reduced from ~1600 units to ~100 units**, against
a default 10,000/day. **(verify at signup)** Either way one video a day is nowhere near the cap.

### What you do

1. Go to <https://console.cloud.google.com>, create a project.
2. Enable **YouTube Data API v3**.
3. Configure the **OAuth consent screen** — you will need a privacy policy URL on a real domain.
   `alaskaaihq.com` already qualifies, we just need a privacy page on it.
4. Create an **OAuth client ID** of type *Desktop app*. Download the JSON.
5. Submit the project for the **YouTube API compliance audit** (linked from the consent screen /
   API dashboard).
6. Send me the client JSON.

Google refresh tokens are long-lived, so once this is authorised it tends to stay authorised.

---

## 5 & 6. Instagram Reels and Facebook Page — one Meta submission covers both

These share an app, a review, and a verification, so treat them as a single project.

**Requirements:**
- A **Facebook Page** for Alaska.Ai
- An **Instagram Professional** (Business or Creator) account, **linked to that Page**
- A Meta developer app
- **Business Verification** through Meta Business Manager — legal entity documents, domain
  verification, sometimes a phone call
- **App Review** with a screencast, typically **2 to 4 weeks per submission** **(verify at signup)**

**Permissions to request:**
- Instagram: `instagram_business_content_publish` (this *replaced* the older `instagram_basic` and
  `instagram_content_publish`, which were deprecated 2025-01-27)
- Facebook Page: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`

**Two limits worth knowing now:**
- Instagram allows **100 API-published posts per rolling 24 hours**. Fine for us.
- **You cannot attach Instagram's music library via the API.** Any music must be embedded in the
  file. We already embed ours, so this costs us nothing — but it means we can never use a
  trending sound programmatically.

### What you do

1. <https://developers.facebook.com> → create an app of type **Business**.
2. In **Meta Business Manager**, complete **Business Verification** first. It gates everything and
   it is the slowest part, so start it before you need it.
3. Add the **Instagram Graph API** and **Facebook Login for Business** products.
4. Request the four permissions above, submit the screencast, wait.
5. Send me the **App ID**, **App Secret**, and the **Page ID** / **Instagram Business Account ID**.

---

## What I need from you, in one list

Nothing here should ever be pasted into a chat message or committed. See the next section.

| Platform | Credentials |
| --- | --- |
| LinkedIn | Client ID, Client Secret |
| X | API Key, API Key Secret, Access Token, Access Token Secret |
| TikTok | Client Key, Client Secret |
| YouTube | OAuth client JSON (Desktop app) |
| Meta (IG + FB) | App ID, App Secret, Page ID, IG Business Account ID |

## How we store them

**Environment variables in the routine environment, never in the repo.** The routine environment
at claude.ai/code/routines already holds `GEMINI_API_KEY` this way, which is the pattern to copy.
I will add a `scripts/social_keys_check.py` that reports which platforms are configured and which
are missing, so a run never discovers a dead credential at post time — it discovers it at the
start, when there is still time to do something.

If a key ever does end up in the repo by accident, treat it as burned and rotate it. Do not just
delete the commit.

---

## One thing I want to flag before we build it

Right now the Gmail draft is the last point where a human sees the Dispatch before it goes out.
Autonomous posting removes that. That is the point, and I am not arguing against it — but it means
**the ship gate becomes the only thing standing between a bad cut and your audience.**

Today's run is the argument for taking that seriously: the panel passed a cut at 7.61, and later
rounds surfaced two narration lines making claims the record did not support. Those were caught
because there was still a human step and time to fix them. Under autopost they would have been
public.

Two cheap mitigations I would build in alongside:

1. **A hold window.** Post on a delay (say 30 minutes) with the email arriving first, so you have a
   real chance to kill it. A `SCRUB` reply or a file in the repo aborts the post.
2. **Hard blockers post nothing, ever.** The ship gate already refuses on a hard blocker. Autopost
   must inherit that refusal rather than reimplement it.

Say the word if you would rather skip the hold window and go straight through. Your call, and it is
easy either way — I just do not want it to be an accident.

---

## Sources

- [Share on LinkedIn (self-serve, `w_member_social`, video upload flow, rate limits)](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- [LinkedIn Community Management API overview (tiers, screencast, eligibility)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview?view=li-lms-2026-05)
- [Meta: Publish Content using the Instagram Platform](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Meta: Facebook Pages API](https://developers.facebook.com/docs/pages-api/)
- [Meta: Permissions Reference](https://developers.facebook.com/docs/permissions/)
- [YouTube Data API revision history (upload quota change)](https://developers.google.com/youtube/v3/revision_history)
- [TikTok Content Posting API: direct post and audit](https://www.postpeer.dev/blog/best-tiktok-posting-api)
- [TikTok Direct Post Audit](https://docs.mixpost.app/services/social/tik-tok/direct-post-audit/)
- [X API pricing 2026 (pay-per-use)](https://postproxy.dev/blog/x-api-pricing-2026/)
- [Instagram Reels API publishing guide](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/)
