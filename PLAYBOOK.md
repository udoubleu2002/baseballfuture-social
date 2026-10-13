# BaseballFuture daily social post: playbook

Each run creates ONE post for today (Pacific time) and schedules it in Buffer to publish at
**1:00 PM America/Los_Angeles** on X, Instagram and Facebook, with a branded graphic.

## Audience and voice

- Write to **parents of high school baseball players, roughly 40 to 55 years old**.
- Every post is about **college baseball recruiting**: levels (D1, D2, D3, NAIA, JUCO), evaluation,
  showcases, coach contact, video, academics, cost, timelines and fit.
- Speak to the parent about "your player" (or "he/him" for the player). Plain, warm, confident and practical.
  No slang, no hype, no fear-mongering, no guarantees about scholarships or roster spots.
- Short lines, generous line breaks, emoji used sparingly as bullets (⚾ ✅ ❌ 👇).
- Never invent statistics, NCAA rules or dates. Keep claims general and true.
- BaseballFuture facts you may use: free best-fit preview; full report compares a player's numbers with
  typical recruiting ranges for D1, D2, D3, NAIA and JUCO; school target list; 90-day plan; PDFs for coaches.
  Fit scores are estimates, not a coach's evaluation and not a prediction of being recruited.

## Weekly rotation (by day of week, Pacific time)

| Day | Theme | Graphic style that usually fits |
|---|---|---|
| Monday | Shareable myth-buster or "know your level" idea | statement or list |
| Tuesday | Recruiting education (what coaches evaluate, by position or topic) | list |
| Wednesday | Debate or would-you-rather for parents | versus |
| Thursday | Recruiting tips (do/don't, how-to) | dodont or list |
| Friday | BaseballFuture promotion (evaluation, best-fit preview, target list) | bars or list |
| Saturday | Player development or a shareable discussion ("unpopular opinion") | list or statement |
| Sunday | Parent engagement or audience research question (poll) | poll |

Use the original post ideas in `examples/source-ideas.md` as inspiration and write fresh variations.
**Do not repeat a topic or headline used in the last 30 posts**; check `posts/` first.

## The link rule

Include `https://baseballfuture.com` on **every third post only**, counted from the first post on
2026-10-13: include it when `(today - 2026-10-13).days % 3 == 0` (Oct 13, 16, 19, 22, ...).
On link days, also set `"footer": "baseballfuture.com"` in the graphic spec.
On all other days, the caption and graphic must not contain the URL. On a Friday promotion without
the link, say "Search BaseballFuture" or "Link in our bio" instead.

## Caption

One caption, used on all three channels (the X account is Premium, so long posts are fine).
- 400 to 900 characters. Hook line first. End with a question or a clear next step.
- 1 to 3 hashtags at the end, from: #BaseballRecruiting #CollegeBaseball #BaseballParents
  #StudentAthlete #Pitching #PlayerDevelopment #HighSchoolBaseball.

## Graphic

1. Write a spec JSON to `posts/YYYY-MM-DD.json` under a `"graphic"` key (see the docstring at the top of
   `tools/render.py` for fields; samples are in `examples/`). Keep it short:
   headline under ~40 characters, 3 to 4 items under ~32 characters each (bars may have 5).
   Use sentence case. Wrap 1 to 3 words of the headline in *asterisks* for the green highlight.
2. If `assets/photos/` contains photos, use one on roughly every other post (`"photo": "assets/photos/<file>"`),
   choosing one not used in the last 10 posts.
3. Render: `python3 tools/render.py <spec-only json> graphics/YYYY-MM-DD.png`
   - If it prints OVERFLOW, shorten the copy and render again.
   - Look at the PNG (Read tool) and check it reads cleanly before posting.
4. Commit `graphics/YYYY-MM-DD.png` and `posts/YYYY-MM-DD.json` and push to `main`.
   Image URL: `https://raw.githubusercontent.com/udoubleu2002/baseballfuture-social/main/graphics/YYYY-MM-DD.png`

## Scheduling in Buffer

Organization "My organization" (`6acd4ccb5a6386563b0c6d2c`). Channels:
- X `_baseballfuture`: `6acd4d92778b240e2fecf366`
- Instagram `baseball.future` (business): `6acd546b778b240e2fed4650`, metadata `{"instagram":{"type":"post","shouldShareToFeed":true}}`
- Facebook page `BaseballFuture`: `6acd54ca778b240e2fed48f5`, metadata `{"facebook":{"type":"post"}}`

For each channel call `create_post` with `mode: "customScheduled"`, `schedulingType: "automatic"`,
`dueAt` = today 13:00 with the correct Pacific offset (-07:00 during daylight time, -08:00 otherwise),
the caption as `text`, and the image as an asset with descriptive `altText`.

Before creating, call `list_posts` for today's date range and skip any channel that already has a
post due today at 1:00 PM (prevents duplicates if a run repeats). If the time has already passed,
do not post; report it instead. If a channel errors, still post to the others and report the error.

## Log

Write `posts/YYYY-MM-DD.json` with: date, theme, headline, caption, include_url, photo, graphic spec,
and the Buffer post IDs per channel. Commit and push after scheduling.
