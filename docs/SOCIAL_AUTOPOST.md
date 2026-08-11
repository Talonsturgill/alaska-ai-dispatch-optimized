# Autonomous posting: what each platform needs, and how to get the keys

Researched 2026-08-09, corrected 2026-08-11 after the owner pushed back on three points and was
right about one of them. Every claim below is now tied to a first-party doc where one exists.
Where a number came only from a third-party write-up it is marked **(verify at signup)**.

**What changed in the correction pass**, so the history is not lost:

- **Meta was wrong and is now fixed.** The first version said Instagram and Facebook needed App
  Review and Business Verification, 2 to 6 weeks. They do not, for what we are doing. Meta's own
  docs say apps in **Development mode** can use permissions with **no App Review** as long as the
  people involved have a role on the app. You own the app, the Page and the Instagram account, so
  you are a role user by definition. Meta moves from "weeks" to "same day".
- **The LinkedIn company-page section is gone.** It required a registered legal entity and we are
  not one, so it was dead weight.
- **X pricing stands, with a caveat I owe you.** The free tier really did end, but only in February,
  and existing accounts may be grandfathered. Check your dashboard before assuming you owe money.
- **YouTube and TikTok stand.** Both are quoted from the platform's own documentation below rather
  than paraphrased.

---

## The headline

Four of the five can be live the same day. One is a genuine wait.

| Platform | Can we post video? | Approval needed | Realistic time to live |
| --- | --- | --- | --- |
| **LinkedIn (your profile)** | Yes | **None. Self-serve.** | **Same day** |
| **Instagram (Reels)** | Yes | **None in Development mode** | **Same day** |
| **Facebook Page** | Yes | **None in Development mode** | **Same day** |
| **X / Twitter** | Yes | None, but likely **paid** | Same day once billing is sorted |
| **YouTube (Shorts)** | Yes | **Audit**, or uploads lock to private | Weeks |
| **TikTok** | Yes | **Audit**, or posts lock to private | Weeks |

**Recommended order: LinkedIn and Meta together first.** They cover the surfaces you care about
most, neither needs anyone's permission, and between them they prove the whole posting path. Start
the YouTube and TikTok audits the same week, since those are waiting rather than working, then wire
them up when the approvals land.

---

## 1. LinkedIn, your own profile

Posting video to your own profile uses the **Share on LinkedIn** product, which grants the
`w_member_social` scope. It is self-serve: you add the product in the developer portal and it is
enabled. No review, no legal entity, no screencast. Video is supported through the
`feedshare-video` upload recipe.

Rate limit is **150 requests per member per day**, which is enormous next to one Dispatch.

### What you do

1. Go to <https://www.linkedin.com/developers/apps> and click **Create app**.
2. It asks you to associate the app with a **LinkedIn Page** that you admin. Note that creating a
   LinkedIn Page is not the same thing as the Community Management API below: a Page needs a name
   and a website, not incorporation papers. This association only exists to create the app, and it
   does not mean you are posting to the Page.
3. On the **Products** tab, add:
   - **Share on LinkedIn** (grants `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (needed to resolve your Person URN)
4. On the **Auth** tab, copy the **Client ID** and **Client Secret**, and add a redirect URL. Use
   `http://localhost:8080/callback`, since we only need it once to mint a token.
5. Send me the Client ID and Secret. I will write a one-time script that opens the consent URL, you
   approve in the browser, and it exchanges the code for a token.

### The one real catch

LinkedIn member access tokens last **60 days**, and refresh tokens are not granted to every app by
default. So this needs re-authorising periodically. I will have the routine detect an expiring
token and email you a re-auth link well before it dies, rather than discovering it at post time.

**Not doing:** the LinkedIn **Community Management API**, which is what posting as an Alaska.Ai
*company page* would require. It needs a registered legal entity, so it is off the table until that
changes. Noting it here only so a future run does not rediscover it and think it is an option.

---

## 2 and 3. Instagram Reels and Facebook Page, one Meta app covers both

**This is the section I got wrong the first time.** I described the path a company takes to ship a
product other people use, which is not what we are doing. We are one person posting to accounts he
owns, and Meta has an explicit lane for that.

From Meta's own documentation: apps in **Development mode** can request permissions from **role
users** with standard or advanced access, and **App Review is not required** for that. A role user
is anyone listed on the app as an admin, developer or tester. You will be the admin of your own
app, and the Page and Instagram account are yours, so every permission we need is available
immediately.

What this means in practice:

- **No App Review.** No screencast, no submission, no wait.
- **No Business Verification.** That gates advanced access and Live mode, which we do not need to
  post to our own accounts. **(verify at signup, since Meta occasionally moves which tier a given
  permission sits in)**
- The tradeoff is that a Development-mode app only works for accounts with a role on it. That is
  a real limit for a product with users, and precisely zero limit for us.

**Requirements:**
- A **Facebook Page** for Alaska.Ai
- An **Instagram Professional** account (Business or Creator) **linked to that Page**
- A Meta developer app, left in Development mode

**Permissions to request:**
- Instagram: `instagram_business_content_publish` (this replaced the older `instagram_basic` and
  `instagram_content_publish`, deprecated 2025-01-27)
- Facebook Page: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`

**Two limits worth knowing now:**
- Instagram allows **100 API-published posts per rolling 24 hours**. Fine for one a day.
- **Instagram's music library is not reachable through the API.** Any music has to be embedded in
  the file. We already embed ours, so this costs us nothing, but it does mean we can never attach a
  trending sound programmatically.

### What you do

1. <https://developers.facebook.com> → create an app. **Leave it in Development mode.**
2. Add the **Instagram Graph API** and **Facebook Login for Business** products.
3. Confirm your Instagram account is Professional and linked to the Alaska.Ai Page.
4. Generate a token with the permissions above through the Graph API Explorer, with your own
   account as the role user.
5. Send me the **App ID**, **App Secret**, **Page ID** and **Instagram Business Account ID**.

Meta Page tokens can be exchanged for long-lived ones and then for a permanent Page token, so this
ends up lower-maintenance than LinkedIn.

---

## 4. X / Twitter

X moved to pay-per-use pricing and **discontinued the free tier for new developers on 2026-02-06**.
Reported rates **(verify at signup)**:

- **$0.015 per post created**
- **$0.20 per post if it contains a link**
- $0.005 per post read

**Check your own account first.** The change is six months old, and accounts that already had free
or Basic access before February may still have it. If you have posted programmatically from an
existing X app, sign into <https://developer.x.com> and look at what tier that project is on before
adding a card. Your memory of this being easy is accurate, it is just about a world that changed in
February.

**A useful accident:** the credits work we shipped puts `alaskaaihq.com` inside the video rather
than in the post text. If the post body carries no URL we pay $0.015 instead of $0.20, a 13x
difference. Worth deliberately keeping links out of the X copy.

At one Dispatch a day with no link, that is about **$0.45 a month**.

### What you do

1. <https://developer.x.com>, sign in as the Alaska.Ai account. Check the tier on any existing
   project before creating a new one.
2. Create a Project and an App if you do not have one.
3. Set app permissions to **Read and Write** *before* generating the access token. A token minted
   under read-only permissions stays read-only and has to be regenerated.
4. From **Keys and tokens**, generate **API Key**, **API Key Secret**, **Access Token**, **Access
   Token Secret**.
5. Send me all four.

X tokens do not expire the way LinkedIn's do, which makes this the lowest-maintenance platform once
it is on.

---

## 5. YouTube Shorts

Uploading is easy (Data API v3 `videos.insert`). The audit is not optional, and this is Google's own
wording from the Data API revision history:

> All videos uploaded via the `videos.insert` endpoint from unverified API projects created after
> 28 July 2020 will be restricted to private viewing mode.

It applies to your own channel. The restriction is on the API project, not the account, so owning
the channel does not exempt it. Lifting it requires the **YouTube API compliance audit**.

Quota: the upload cost was reduced from roughly 1600 units to roughly 100, against a default
10,000/day. **(verify at signup)** Either way one video a day is nowhere near the cap.

### What you do

1. <https://console.cloud.google.com>, create a project.
2. Enable **YouTube Data API v3**.
3. Configure the **OAuth consent screen**. It wants a privacy policy URL on a real domain.
   `alaskaaihq.com` qualifies, we just need a privacy page on it, which I can add to the site build.
4. Create an **OAuth client ID** of type *Desktop app* and download the JSON.
5. Submit the project for the **compliance audit**, linked from the API dashboard.
6. Send me the client JSON.

We can wire the upload up before the audit lands and let it post privately, then flip to public the
day it clears. Google refresh tokens are long-lived, so once authorised it tends to stay authorised.

---

## 6. TikTok

TikTok has two posting modes:

- **`video.upload`** puts the file in the creator's TikTok inbox as a draft. You still tap publish.
  Available without audit.
- **`video.publish`** posts directly and publicly. Requires passing the Content Posting audit.

TikTok's own documentation on unaudited clients:

> All content posted by unaudited clients will be restricted to private viewing mode.

So an unaudited direct-post integration is not autonomous, it is a faster manual workflow. The audit
is a form and a review, not a legal-entity check, so it is a wait rather than a wall.

### What you do

1. Register at <https://developers.tiktok.com> and create an app.
2. Add the **Content Posting API** product and request the `video.publish` scope.
3. Submit for audit. It wants to see that your flow is compliant, notably that the creator sees and
   confirms the content and that the required disclosures are displayed.
4. In the meantime we can ship `video.upload`, which lands a draft you tap once.

**One honest note on the application:** TikTok's audit is written around apps where a human user
publishes their own content through your tool. Ours is a routine publishing on your behalf, on your
own account. That is a legitimate case and people do get approved for it, but it is worth describing
accurately rather than dressing it up as a consumer app. Better to be rejected once and resubmit
than approved on a description that does not match what we do.

---

## What I need from you, in one list

| Platform | Credentials |
| --- | --- |
| LinkedIn | Client ID, Client Secret |
| Meta (IG + FB) | App ID, App Secret, Page ID, IG Business Account ID |
| X | API Key, API Key Secret, Access Token, Access Token Secret |
| YouTube | OAuth client JSON (Desktop app) |
| TikTok | Client Key, Client Secret |

## How we store them

**Environment variables in the routine environment, never in the repo.** The routine environment at
claude.ai/code/routines already holds `GEMINI_API_KEY` this way, which is the pattern to copy.

`scripts/social_keys_check.py` will report which platforms are configured and which are missing at
the start of a run, so a run never discovers a dead credential at post time. It discovers it when
there is still time to do something.

If a key ever does end up in the repo by accident, treat it as burned and rotate it. Deleting the
commit is not enough.

---

## One thing to decide before we build it

Right now the Gmail draft is the last point where a human sees a Dispatch before it goes out.
Autonomous posting removes that, which is the entire point, and I am not arguing against it. But it
does mean **the ship gate becomes the only thing between a bad cut and your audience.**

The 2026-08-09 run is the argument for taking that seriously. The panel passed a cut at 7.61, and
later rounds surfaced two narration lines making claims the record did not support. They were caught
because there was still a human step. Under autopost they would have been public.

Two cheap mitigations worth building alongside:

1. **A hold window.** Post on a delay, say 30 minutes, with the email arriving first, so you have a
   real chance to kill it. A `SCRUB` reply or a file in the repo aborts the post.
2. **Hard blockers post nothing, ever.** The ship gate already refuses on a hard blocker. Autopost
   inherits that refusal rather than reimplementing it.

Say the word if you would rather skip the hold window and go straight through. Your call, and it is
easy either way.

---

## Sources

- [Share on LinkedIn (self-serve, `w_member_social`, video upload, rate limits)](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- [Meta: App Development mode and role users (no App Review required)](https://developers.facebook.com/docs/development/build-and-test/app-modes/)
- [Meta: Publish Content using the Instagram Platform](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Meta: Facebook Pages API](https://developers.facebook.com/docs/pages-api/)
- [Meta: Permissions Reference](https://developers.facebook.com/docs/permissions/)
- [YouTube Data API revision history (unverified projects restricted to private)](https://developers.google.com/youtube/v3/revision_history)
- [TikTok Content Posting API (unaudited clients restricted to private)](https://developers.tiktok.com/doc/content-sharing-guidelines/)
- [X API pricing 2026 (pay-per-use)](https://postproxy.dev/blog/x-api-pricing-2026/)
- [Instagram Reels API publishing guide](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/)
