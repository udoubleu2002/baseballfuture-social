"""Render a BaseballFuture social graphic (1080x1080 PNG) from a JSON spec.

Usage: python3 tools/render.py spec.json graphics/2026-10-13.png

Spec fields:
  kicker    small label above the headline, e.g. "For baseball parents"
  headline  main line in sentence case. Wrap words in *asterisks* to make them green.
  sub       optional supporting sentence under the headline
  items     list of short lines (3-5, under ~40 characters each)
  style     "list"      numbered rows (default)
            "dodont"    items start with "DO:" or "DON'T:"
            "poll"      lettered A/B/C options
            "versus"    exactly two items, option A vs option B
            "statement" big headline only (items ignored)
            "bars"      items are "Label|score" (0-100), like the report's fit bars
  photo     optional path (relative to repo root) of a photo in assets/photos/.
            The photo fills the top of the frame under a navy fade.
  tag       optional gold pill, e.g. "Parents, weigh in"
  footer    optional; on link days use "baseballfuture.com"
  hashtag   optional, shown bottom-right when there is no footer link

Exits with "OVERFLOW" if the content does not fit; shorten the copy and rerun.
"""
import base64, html, json, mimetypes, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# Brand tokens sampled from baseballfuture.com
BG_DEEP = "#060e19"
BG = "#0e1b2c"
INK = "#f2f4f7"
SOFT = "#c9d0da"
MUTED = "#8f99a8"
GREEN = "#52b82f"
GREEN_BAR = "#3ddc84"
GREEN_DARK = "#248840"
GREEN_PILL = "#143a26"
SKY = "#77c6fd"
GOLD = "#f5c518"


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).endswith(".otf"):
        mime = "font/otf"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def face(family, file, weight):
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url({data_uri(FONTS / file)})}}"


FACES = "".join([
    face("Anton", "Anton-Regular.ttf", 400),               # wordmark only
    face("Display", "InterDisplay-Medium.otf", 500),
    face("Display", "InterDisplay-SemiBold.otf", 600),
    face("Display", "InterDisplay-Bold.otf", 700),
    face("Text", "Inter-Regular.otf", 400),
    face("Text", "Inter-Medium.otf", 500),
    face("Text", "Inter-SemiBold.otf", 600),
    face("Text", "Inter-Bold.otf", 700),
])


def logo(size):
    return f"""<svg viewBox="0 0 100 100" width="{size}" height="{size}">
<circle cx="50" cy="50" r="41" fill="none" stroke="{INK}" stroke-width="7"/>
<path d="M38 22 C22 40 24 66 34 82" fill="none" stroke="#6b7480" stroke-width="3"/>
<path d="M30 84 C42 70 56 50 72 22" fill="none" stroke="{INK}" stroke-width="3"/>
<g stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
<path d="M33 72 l9 -2"/><path d="M40 62 l9 -2"/><path d="M47 52 l9 -2"/><path d="M54 42 l9 -2"/><path d="M61 32 l9 -2"/></g>
<path d="M66 18 L84 10 L80 30 Z" fill="{GREEN}"/></svg>"""


# Faint line-art baseball used when there is no photo.
BALL = f"""<svg class="ball" viewBox="0 0 600 600" width="820" height="820" fill="none">
<circle cx="300" cy="300" r="296" stroke="rgba(255,255,255,.06)" stroke-width="2"/>
<path d="M170 30 C60 170 60 430 170 570" stroke="rgba(82,184,47,.22)" stroke-width="2.5" stroke-dasharray="14 12"/>
<path d="M430 30 C540 170 540 430 430 570" stroke="rgba(82,184,47,.22)" stroke-width="2.5" stroke-dasharray="14 12"/>
</svg>"""

CHECK = f'<svg viewBox="0 0 24 24" width="22" height="22"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="{GREEN_BAR}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CROSS = f'<svg viewBox="0 0 24 24" width="18" height="18"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="{MUTED}" stroke-width="3" stroke-linecap="round"/></svg>'


def rich(text):
    return re.sub(r"\*(.+?)\*", r'<em>\1</em>', html.escape(text))


def items_html(style, items):
    out = []
    if style == "dodont":
        for it in items:
            kind, _, txt = it.partition(":")
            good = kind.strip().upper() == "DO"
            out.append(f'<li class="{"do" if good else "dont"}"><b>{CHECK if good else CROSS}</b>'
                       f'<span>{rich(txt.strip())}</span></li>')
    elif style == "poll":
        for i, it in enumerate(items):
            out.append(f'<li class="poll"><b>{chr(65+i)}</b><span>{rich(it)}</span></li>')
    elif style == "bars":
        for it in items:
            label, _, score = it.partition("|")
            s = max(0, min(100, int(score or 0)))
            ok = s >= 70
            out.append(f'<li class="bar"><b>{html.escape(label)}</b><div class="track"><div class="fill" '
                       f'style="width:{s}%;background:{GREEN_BAR if ok else SKY}"></div><i></i></div>'
                       f'<span class="score">{s}</span><u class="{"in" if ok else "near"}">'
                       f'{"In range" if ok else "Near range"}</u></li>')
    else:
        for i, it in enumerate(items):
            out.append(f'<li class="num"><b>{i+1}</b><span>{rich(it)}</span></li>')
    return f'<ul class="{style}">{"".join(out)}</ul>'


def build(spec):
    style = spec.get("style", "list")
    items = spec.get("items", [])
    n = len(items)
    photo = spec.get("photo")
    head = spec["headline"]
    hl = len(head.replace("*", ""))

    if style == "statement":
        hsize = 116 if hl <= 30 else 100 if hl <= 48 else 86
    else:
        hsize = 100 if hl <= 22 else 90 if hl <= 32 else 80 if hl <= 44 else 70
        if n >= 5 or style == "bars" or photo:
            hsize = min(hsize, 84)
    isize = 38 if n <= 3 else 36 if n <= 4 else 33

    body = ""
    if style == "versus" and n == 2:
        body = (f'<div class="vs"><div class="vc a"><b>A</b><span>{rich(items[0])}</span></div>'
                f'<div class="vc b"><b>B</b><span>{rich(items[1])}</span></div></div>')
    elif style != "statement" and items:
        body = items_html(style, items)

    bg = (f'<div class="photo" style="background-image:url({data_uri(ROOT / photo)})"></div><div class="fade"></div>'
          if photo else BALL)
    tag = f'<div class="tag">{html.escape(spec["tag"])}</div>' if spec.get("tag") else ""
    kicker = f'<div class="kick">{html.escape(spec["kicker"])}</div>' if spec.get("kicker") else ""
    sub = f'<p class="sub">{rich(spec["sub"])}</p>' if spec.get("sub") else ""
    right = (f'<div class="url">{html.escape(spec["footer"])} <span>→</span></div>' if spec.get("footer")
             else f'<div class="hash">{html.escape(spec.get("hashtag", ""))}</div>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1080px;overflow:hidden;position:relative;color:{INK};font-family:Text,sans-serif;
 -webkit-font-smoothing:antialiased;
 background:radial-gradient(90% 70% at 85% 5%,#16304f 0%,rgba(14,27,44,0) 60%),
 radial-gradient(70% 60% at 0% 100%,rgba(36,136,64,.16) 0%,rgba(14,27,44,0) 60%),
 linear-gradient(180deg,{BG} 0%,{BG_DEEP} 100%)}}
.photo{{position:absolute;left:0;right:0;top:0;height:{"620px" if style!="statement" else "1080px"};
 background-size:cover;background-position:center 30%;filter:grayscale(1) contrast(1.1) brightness(.85)}}
.fade{{position:absolute;inset:0;background:
 linear-gradient(180deg,rgba(6,14,25,.6) 0%,rgba(14,27,44,.2) 20%,rgba(14,27,44,.5) 40%,{BG} {"57%" if style!="statement" else "80%"},{BG_DEEP} 100%),
 linear-gradient(100deg,rgba(36,136,64,.28),rgba(14,27,44,0) 50%)}}
.ball{{position:absolute;right:-300px;top:-260px}}
.frame{{position:absolute;inset:0;padding:68px 80px 0 80px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:14px;font:400 34px/1 Anton;letter-spacing:.035em}}
.brand span{{color:{GREEN}}}
.grow{{flex:1}}
.tag{{align-self:flex-start;font:700 21px/1 Text;letter-spacing:.02em;color:{BG_DEEP};background:{GOLD};
 padding:10px 18px;border-radius:999px;margin-bottom:26px}}
.kick{{font:600 23px/1 Text;letter-spacing:.14em;text-transform:uppercase;color:{GREEN_BAR}}}
h1{{font:700 {hsize}px/1.02 Display;letter-spacing:-.035em;margin-top:20px;max-width:920px}}
em{{font-style:normal;color:{GREEN}}}
.sub{{font:400 32px/1.35 Text;color:{SOFT};margin-top:24px;max-width:860px;letter-spacing:-.005em}}
ul{{list-style:none;margin-top:44px;display:flex;flex-direction:column}}
li{{display:flex;align-items:center;gap:24px;font:500 {isize}px/1.2 Text;letter-spacing:-.012em;
 padding:{17 if n>4 else 20}px 0;border-top:1px solid rgba(255,255,255,.12)}}
li:last-child{{border-bottom:1px solid rgba(255,255,255,.12)}}
li.num b{{flex:none;width:46px;height:46px;border-radius:50%;display:grid;place-items:center;
 font:600 22px/1 Display;color:{GREEN_BAR};background:{GREEN_PILL}}}
li.do b,li.dont b{{flex:none;width:46px;height:46px;border-radius:50%;display:grid;place-items:center}}
li.do b{{background:{GREEN_PILL}}} li.dont b{{background:rgba(255,255,255,.07)}}
li.dont span{{color:{MUTED}}}
li.poll b{{flex:none;width:50px;height:50px;border-radius:12px;display:grid;place-items:center;
 font:600 24px/1 Display;border:1.5px solid rgba(255,255,255,.3)}}
li.bar{{gap:20px;padding:15px 0}} li.bar b{{width:96px;font:700 30px/1 Display}}
.track{{flex:1;height:16px;border-radius:8px;background:rgba(255,255,255,.08);position:relative}}
.fill{{height:100%;border-radius:8px}} .track i{{position:absolute;left:70%;top:-6px;bottom:-6px;width:2px;background:{MUTED}}}
.score{{width:48px;text-align:right;color:{SOFT};font:500 28px/1 Text}}
li.bar u{{flex:none;width:150px;text-align:center;white-space:nowrap;text-decoration:none;font:600 19px/1 Text;
 padding:10px 0;border-radius:999px}}
u.in{{background:{GREEN_PILL};color:{GREEN_BAR}}} u.near{{background:rgba(119,198,253,.14);color:{SKY}}}
.vs{{margin-top:44px;display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.vc{{padding:32px 32px 36px;border-radius:22px;display:flex;flex-direction:column;gap:22px;
 font:500 36px/1.22 Text;letter-spacing:-.012em;background:rgba(255,255,255,.035);border:1.5px solid rgba(255,255,255,.12)}}
.vc b{{width:52px;height:52px;border-radius:50%;display:grid;place-items:center;font:700 26px/1 Display}}
.vc.a b{{background:{GREEN_PILL};color:{GREEN_BAR}}} .vc.b b{{background:rgba(119,198,253,.14);color:{SKY}}}
.bottom{{margin:46px -80px 0;padding:28px 80px 34px;border-top:1px solid rgba(255,255,255,.10);
 display:flex;align-items:center;justify-content:space-between;position:relative}}
.bottom:before{{content:"";position:absolute;left:80px;top:-2px;width:72px;height:3px;background:{GREEN};border-radius:2px}}
.foot-l{{font:500 22px/1 Text;color:{MUTED};letter-spacing:.01em}}
.url{{font:600 26px/1 Text;color:{INK};background:{GREEN_DARK};border-radius:999px;padding:15px 26px}}
.url span{{color:#c4f5d2}}
.hash{{font:500 22px/1 Text;color:{SKY}}}
</style></head><body>
{bg}
<div class="frame">
 <div class="brand">{logo(54)}<div>BASEBALL<span>FUTURE</span></div></div>
 <div class="grow"></div>
 {tag}{kicker}<h1>{rich(head)}</h1>{sub}{body}
 <div class="bottom"><div class="foot-l">College baseball recruiting, made clear</div>{right}</div>
</div></body></html>"""


def main(spec_path, out_path):
    spec = json.loads(Path(spec_path).read_text())
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        pg.set_content(build(spec))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        over = pg.evaluate("document.querySelector('.bottom').getBoundingClientRect().bottom > 1081")
        pg.screenshot(path=out_path, type="png")
        b.close()
    if over:
        sys.exit("OVERFLOW: content is too long for the frame; shorten headline or items")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
