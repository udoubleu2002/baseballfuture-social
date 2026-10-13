"""Render a BaseballFuture social graphic (1080x1080 PNG) from a JSON spec.

Usage: python3 tools/render.py spec.json graphics/2026-10-13.png

Spec fields:
  kicker    small letter-spaced label above the headline, e.g. "Recruiting tips"
  headline  the main line (set in caps). Wrap words in *asterisks* to make them green.
  items     list of short lines (keep to 3-5, under ~45 characters each)
  style     "list"      green checkmarks (default)
            "dodont"    items start with "DO:" or "DON'T:"
            "poll"      lettered A/B/C options
            "versus"    exactly two items, shown as option A vs option B
            "statement" big headline only, items ignored; "sub" adds one line under it
            "bars"      items are "Label|score" (0-100), drawn like the report's fit bars
  sub       optional supporting sentence under the headline
  tag       optional pill above the kicker, e.g. "Debate", "Poll", "Unpopular opinion"
  footer    optional; on link days use "baseballfuture.com"
"""
import base64, html, json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# Brand tokens sampled from baseballfuture.com screenshots.
BG_DEEP = "#07101e"
BG = "#0e1b2c"
PANEL = "#13223a"
LINE = "rgba(255,255,255,.10)"
INK = "#f2f4f7"
MUTED = "#a1aab7"
GREEN = "#52b82f"      # wordmark / hero green
GREEN_BAR = "#3ddc84"  # fit-bar green
GREEN_DARK = "#248840" # button green
GREEN_PILL = "#143a26"
SKY = "#77c6fd"        # light-blue accent
GOLD = "#f5c518"       # "Most popular" pill


def font_face(family, file, weight):
    data = base64.b64encode((FONTS / file).read_bytes()).decode()
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/ttf;base64,{data}) format('truetype')}}")


FACES = "".join([
    font_face("Anton", "Anton-Regular.ttf", 400),
    font_face("Barlow", "Barlow-Regular.ttf", 400),
    font_face("Barlow", "Barlow-Medium.ttf", 500),
    font_face("Barlow", "Barlow-SemiBold.ttf", 600),
    font_face("Barlow", "Barlow-Bold.ttf", 700),
    font_face("Barlow", "Barlow-ExtraBold.ttf", 800),
])

LOGO = f"""<svg viewBox="0 0 100 100" width="76" height="76">
<circle cx="50" cy="50" r="41" fill="none" stroke="{INK}" stroke-width="7"/>
<path d="M38 22 C22 40 24 66 34 82" fill="none" stroke="#6b7480" stroke-width="3"/>
<path d="M30 84 C42 70 56 50 72 22" fill="none" stroke="{INK}" stroke-width="3"/>
<g stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
<path d="M33 72 l9 -2"/><path d="M40 62 l9 -2"/><path d="M47 52 l9 -2"/><path d="M54 42 l9 -2"/><path d="M61 32 l9 -2"/></g>
<path d="M66 18 L84 10 L80 30 Z" fill="{GREEN}"/></svg>"""


def rich(text):
    t = html.escape(text)
    return re.sub(r"\*(.+?)\*", r'<span class="g">\1</span>', t)


def rows_html(style, items):
    out = []
    if style == "poll":
        for i, it in enumerate(items):
            out.append(f'<li class="opt"><b>{chr(65+i)}</b><span>{rich(it)}</span></li>')
    elif style == "dodont":
        for it in items:
            kind, _, txt = it.partition(":")
            good = kind.strip().upper() == "DO"
            out.append(f'<li class="{"do" if good else "dont"}"><i>{"✓" if good else "✕"}</i>'
                       f'<span>{rich(txt.strip())}</span></li>')
    elif style == "bars":
        for it in items:
            label, _, score = it.partition("|")
            s = max(0, min(100, int(score or 0)))
            ok = s >= 70
            out.append(f'<li class="bar"><b>{html.escape(label)}</b><div class="track"><div class="fill" '
                       f'style="width:{s}%;background:{GREEN_BAR if ok else SKY}"></div><div class="tick"></div></div>'
                       f'<em>{s}</em><u class="{"in" if ok else "near"}">{"IN RANGE" if ok else "NEAR RANGE"}</u></li>')
    else:
        for it in items:
            out.append(f'<li><i class="ck">✓</i><span>{rich(it)}</span></li>')
    return "".join(out)


def build(spec):
    style = spec.get("style", "list")
    items = spec.get("items", [])
    n = len(items)
    head = spec["headline"]
    hl = len(re.sub(r"\*", "", head))
    if style == "statement":
        hsize = 150 if hl <= 30 else 124 if hl <= 50 else 104
    else:
        hsize = 112 if hl <= 22 else 96 if hl <= 34 else 82 if hl <= 48 else 70
        if n >= 5:
            hsize = min(hsize, 84)
    isize = 46 if n <= 3 else 42 if n <= 4 else 38

    body = ""
    if style == "versus" and n == 2:
        body = (f'<div class="vs"><div class="vcard"><b>A</b><span>{rich(items[0])}</span></div>'
                f'<div class="vmid">VS</div><div class="vcard"><b>B</b><span>{rich(items[1])}</span></div></div>')
    elif style != "statement" and items:
        body = f'<div class="panel"><ul class="{style}">{rows_html(style, items)}</ul></div>'

    sub = f'<p class="sub">{rich(spec["sub"])}</p>' if spec.get("sub") else ""
    tag = f'<div class="tag">{html.escape(spec["tag"].upper())}</div>' if spec.get("tag") else ""
    kicker = f'<div class="kick">{html.escape(spec.get("kicker","").upper())}</div>' if spec.get("kicker") else ""
    foot = (f'<div class="url">{html.escape(spec["footer"])} <span>→</span></div>'
            if spec.get("footer") else "")

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1080px;overflow:hidden;color:{INK};font-family:Barlow,sans-serif;
 background:radial-gradient(110% 80% at 100% 0%,#13243b 0%,{BG} 38%,{BG_DEEP} 100%);position:relative}}
.diamond{{position:absolute;right:-180px;bottom:-180px;width:560px;height:560px;transform:rotate(45deg);
 border:2px dashed rgba(255,255,255,.07)}}
.diamond:after{{content:"";position:absolute;inset:90px;border:2px solid rgba(255,255,255,.05)}}
.wrap{{position:absolute;inset:72px 76px 70px 76px;display:flex;flex-direction:column}}
.top{{display:flex;align-items:center;gap:20px}}
.word{{font:400 46px/1 Anton;letter-spacing:.02em}} .word span{{color:{GREEN}}}
.tag{{align-self:flex-start;margin-bottom:6px;font:800 22px/1 Barlow;letter-spacing:.12em;color:{BG_DEEP};
 background:{GOLD};padding:10px 18px;border-radius:999px}}
.kick{{margin-top:{"18" if tag else "0"}px;font:700 24px/1 Barlow;letter-spacing:.2em;color:{MUTED}}}
h1{{font:400 {hsize}px/.98 Anton;text-transform:uppercase;letter-spacing:.005em;margin-top:22px;max-width:930px}}
.g{{color:{GREEN}}}
.sub{{font:500 {38 if style=="statement" else 32}px/1.3 Barlow;color:{MUTED};margin-top:26px;max-width:880px}}
.panel{{margin-top:38px;background:rgba(19,34,58,.85);border:2px solid {LINE};border-radius:22px;padding:34px 38px}}
ul{{list-style:none;display:flex;flex-direction:column;gap:{20 if n>4 else 24}px}}
li{{display:flex;align-items:center;gap:22px;font:600 {isize}px/1.2 Barlow}}
.ck{{font-style:normal;color:{GREEN_BAR};font-weight:800;font-size:{isize+4}px;width:{isize}px;flex:none}}
li.do i,li.dont i{{flex:none;font-style:normal;font-weight:800;width:{isize+10}px;height:{isize+10}px;border-radius:10px;
 display:grid;place-items:center;font-size:{isize-6}px}}
li.do i{{background:{GREEN_PILL};color:{GREEN_BAR}}}
li.dont i{{background:rgba(255,255,255,.06);color:{MUTED}}}
li.dont span{{color:{MUTED}}}
li.opt b{{flex:none;min-width:{isize+24}px;height:{isize+18}px;border-radius:12px;border:2px solid rgba(255,255,255,.22);
 display:grid;place-items:center;font:800 {isize-4}px/1 Barlow;letter-spacing:.06em;color:{INK}}}
li.opt:first-child b{{background:{GREEN_DARK};border-color:{GREEN_DARK}}}
li.bar{{gap:22px;font-size:34px}} li.bar b{{width:110px;font-weight:800}}
.track{{flex:1;height:22px;border-radius:11px;background:rgba(255,255,255,.08);position:relative;overflow:visible}}
.fill{{height:100%;border-radius:11px}} .tick{{position:absolute;left:70%;top:-6px;bottom:-6px;width:3px;background:{MUTED}}}
li.bar em{{font-style:normal;width:56px;text-align:right;color:{MUTED};font-weight:500}}
li.bar u{{width:172px;white-space:nowrap;text-align:center;flex:none;text-decoration:none;font:800 20px/1 Barlow;letter-spacing:.06em;padding:9px 14px;border-radius:999px}}
u.in{{background:{GREEN_PILL};color:{GREEN_BAR}}} u.near{{background:rgba(119,198,253,.14);color:{SKY}}}
.vs{{margin-top:44px;display:flex;align-items:stretch;gap:20px}}
.vcard{{flex:1;min-height:250px;background:rgba(19,34,58,.85);border:2px solid {LINE};border-radius:22px;padding:30px;
 display:flex;flex-direction:column;gap:18px;font:600 40px/1.2 Barlow}}
.vcard b{{font:400 54px/1 Anton;color:{GREEN}}} .vcard:last-child b{{color:{SKY}}}
.vmid{{align-self:center;font:400 44px/1 Anton;color:{MUTED}}}
.spacer{{flex:1}}
.bottom{{display:flex;align-items:center;justify-content:space-between}}
.url{{font:700 30px/1 Barlow;color:{SKY};border:2px solid {SKY};border-radius:999px;padding:16px 28px;letter-spacing:.02em}}
.url span{{color:{GREEN}}}
.hash{{font:600 26px/1 Barlow;color:{MUTED}}}
</style></head><body><div class="diamond"></div><div class="wrap">
<div class="top">{LOGO}<div class="word">BASEBALL<span>FUTURE</span></div></div>
<div class="spacer"></div>{tag}{kicker}<h1>{rich(head)}</h1>{sub}{body}
<div class="spacer"></div>
<div class="bottom">{foot}<div class="hash">{html.escape(spec.get("hashtag",""))}</div></div>
</div></body></html>"""


def main(spec_path, out_path):
    spec = json.loads(Path(spec_path).read_text())
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        pg.set_content(build(spec))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        pg.screenshot(path=out_path, type="png")
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
