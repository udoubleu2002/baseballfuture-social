# BaseballFuture daily social post: playbook

Each run creates ONE post for today (Pacific time) and schedules it in Buffer to publish at
**1:00 PM and 4:00 PM America/Los_Angeles** on X, Instagram and Facebook, with a branded graphic.

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

## The angle: what do the numbers say?

Lean into BaseballFuture's core idea whenever it fits the day's theme: **see what the numbers say about
your player's best college baseball fit.** Tie the topic back to measurable things (exit velo, 60 time,
velocity, pop time, arm strength, grades) and how they compare with typical ranges by level (D1, D2, D3,
NAIA, JUCO). Frame it as finding the right fit, not chasing the highest level. Keep it honest: numbers are
one part of the picture, fit scores are estimates, and nothing guarantees a roster spot.
Good hooks: "Do you know where his numbers stack up?", "What do the numbers say?", "Best fit beats biggest name."

## The link rule

**Every post links to `https://baseballfuture.com`.**
- Every graphic shows the BaseballFuture logo at the top and the "See what the numbers say at
  BaseballFuture.com" footer box at the bottom. `tools/render.py` draws both automatically.
- An image can't be clicked, so the clickable link lives in the caption:
  - **X and Facebook:** end the caption with a short next step and the full URL on its own line,
    e.g. `See what the numbers say about your player's best fit:\nhttps://baseballfuture.com`
    (both platforms make it a clickable link).
  - **Instagram:** caption links are not clickable there, so replace the URL line with
    `Tap the link in our bio to see what the numbers say. 👆` (the bio link must point to baseballfuture.com).

## Caption

One caption for X and Facebook (the X account is Premium, so long posts are fine); the Instagram copy is the same except for the link line.
- 400 to 900 characters. Hook line first. End with a question or a clear next step, then the link line
  (see the link rule; Instagram gets the "link in our bio" line instead of the URL).
- 1 to 3 hashtags at the end, from: #BaseballRecruiting #CollegeBaseball #BaseballParents
  #StudentAthlete #Pitching #PlayerDevelopment #HighSchoolBaseball.

## Graphic

1. Write a spec JSON to `posts/YYYY-MM-DD.json` under a `"graphic"` key (see the docstring at the top of
   `tools/render.py` for fields; samples are in `examples/`). The look is bold and sporty: near-black navy background,
   kelly green (#52b82f, from the logo) used as an accent, not a fill; slanted all-caps headline. Keep it short:
   headline under ~40 characters (it renders in caps), 3 to 4 items under ~30 characters each (bars may have 5).
   Wrap 1 to 3 words of the headline in *asterisks* for the green highlight.
   For debates and polls, add an `"ask"` line such as `"No wrong answer. *What's your choice?*"`.
   The logo and the BaseballFuture.com footer are always drawn; there is no footer field to set.
2. If `assets/photos/` contains photos, use one on roughly every other post (`"photo": "assets/photos/<file>"`),
   choosing one not used in the last 10 posts.
3. Render: `python3 tools/render.py <spec-only json> graphics/YYYY-MM-DD.png`
   - If it prints OVERFLOW, shorten the copy and render again.
   - Look at the PNG (Read tool) and check it reads cleanly before posting.
4. Commit `graphics/YYYY-MM-DD.png` and `posts/YYYY-MM-DD.json` and push to `main`.
   Image URL: `https://raw.githubusercontent.com/udoubleu2002/baseballfuture-social/main/graphics/YYYY-MM-DD.png`

## Scheduling in Buffer

Times: **1:00 PM and 4:00 PM America/Los_Angeles**, one post per channel per time. Buffer rejects
identical text close together, so the 4:00 PM post uses a lightly reworded caption with the same graphic.

Organization "My organization" (`6acd4ccb5a6386563b0c6d2c`). Channels:
- X `_baseballfuture`: `6acd4d92778b240e2fecf366`
- Instagram `baseball.future` (business): `6acd546b778b240e2fed4650`, metadata `{"instagram":{"type":"post","shouldShareToFeed":true}}`
- Facebook page `BaseballFuture`: `6acd54ca778b240e2fed48f5`, metadata `{"facebook":{"type":"post"}}`

For each channel call `create_post` with `mode: "customScheduled"`, `schedulingType: "automatic"`,
`dueAt` = today 13:00 (and 16:00) with the correct Pacific offset (-07:00 during daylight time, -08:00 otherwise),
the caption as `text`, and the image as an asset with descriptive `altText`.

Before creating, call `list_posts` for today's date range and skip any channel that already has a
post due today at that time (prevents duplicates if a run repeats). If the time has already passed,
do not post; report it instead. If a channel errors, still post to the others and report the error.

## Log

Write `posts/YYYY-MM-DD.json` with: date, theme, headline, caption, include_url, photo, graphic spec,
and the Buffer post IDs per channel. Commit and push after scheduling.
