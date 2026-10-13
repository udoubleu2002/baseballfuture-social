"""Render a BaseballFuture social graphic (1080x1080 PNG) from a JSON spec.

Usage: python3 tools/render.py spec.json graphics/2026-10-13.png

Spec fields:
  kicker    small letter-spaced label, e.g. "For baseball parents"
  headline  main line, set in caps. Wrap words in *asterisks* to make them green.
  sub       optional supporting sentence under the headline
  items     list of short lines (3-5, under ~40 characters each)
  style     "list"      numbered rows 01, 02, 03 (default)
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
MUTED = "#a1aab7"
GREEN = "#52b82f"
GREEN_BAR = "#3ddc84"
GREEN_DARK = "#248840"
GREEN_PILL = "#143a26"
SKY = "#77c6fd"
GOLD = "#f5c518"


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def face(family, file, weight):
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url({data_uri(FONTS / file)}) format('truetype')}}")


FACES = "".join([
    face("Anton", "Anton-Regular.ttf", 400),
    face("Barlow", "Barlow-Medium.ttf", 500),
    face("Barlow", "Barlow-SemiBold.ttf", 600),
    face("Barlow", "Barlow-Bold.ttf", 700),
    face("Barlow", "Barlow-ExtraBold.ttf", 800),
])


def logo(size):
    return f"""<svg viewBox="0 0 100 100" width="{size}" height="{size}">
<circle cx="50" cy="50" r="41" fill="none" stroke="{INK}" stroke-width="7"/>
<path d="M38 22 C22 40 24 66 34 82" fill="none" stroke="#6b7480" stroke-width="3"/>
<path d="M30 84 C42 70 56 50 72 22" fill="none" stroke="{INK}" stroke-width="3"/>
<g stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
<path d="M33 72 l9 -2"/><path d="M40 62 l9 -2"/><path d="M47 52 l9 -2"/><path d="M54 42 l9 -2"/><path d="M61 32 l9 -2"/></g>
<path d="M66 18 L84 10 L80 30 Z" fill="{GREEN}"/></svg>"""


# Large stitched-ball illustration used when there is no photo.
BALL = f"""<svg class="ball" viewBox="0 0 600 600" width="760" height="760">
<defs><radialGradient id="bg" cx="40%" cy="35%" r="70%">
<stop offset="0" stop-color="#1b2f4c"/><stop offset="1" stop-color="{BG}"/></radialGradient></defs>
<circle cx="300" cy="300" r="290" fill="url(#bg)" stroke="rgba(255,255,255,.08)" stroke-width="3"/>
<path d="M150 40 C40 180 40 420 150 560" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="4"/>
<path d="M450 40 C560 180 560 420 450 560" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="4"/>
<g stroke="{GREEN}" stroke-opacity=".55" stroke-width="7" stroke-linecap="round">
{''.join(f'<path d="M{x1} {y} l-26 -14"/><path d="M{x2} {y} l26 -14"/>' for (x1, x2, y) in
          [(118, 482, 110), (98, 502, 170), (88, 512, 235), (86, 514, 300), (88, 512, 365), (98, 502, 430), (118, 482, 490)])}
</g></svg>"""


def rich(text):
    return re.sub(r"\*(.+?)\*", r'<em>\1</em>', html.escape(text))


def items_html(style, items, isize):
    out = []
    if style == "dodont":
        for it in items:
            kind, _, txt = it.partition(":")
            good = kind.strip().upper() == "DO"
            out.append(f'<li class="{"do" if good else "dont"}"><b>{"DO" if good else "DON&#39;T"}</b>'
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
                       f'{"IN RANGE" if ok else "NEAR RANGE"}</u></li>')
    else:
        for i, it in enumerate(items):
            out.append(f'<li class="num"><b>{i+1:02d}</b><span>{rich(it)}</span></li>')
    return f'<ul class="{style}">{"".join(out)}</ul>'


def build(spec):
    style = spec.get("style", "list")
    items = spec.get("items", [])
    n = len(items)
    photo = spec.get("photo")
    head = spec["headline"]
    hl = len(head.replace("*", ""))

    if style == "statement":
        hsize = 168 if hl <= 24 else 140 if hl <= 40 else 116
    else:
        hsize = 132 if hl <= 18 else 116 if hl <= 26 else 100 if hl <= 36 else 86
        if n >= 5 or style in ("bars",):
            hsize = min(hsize, 96)
        if photo:
            hsize = min(hsize, 104)
    isize = 44 if n <= 3 else 40 if n <= 4 else 36

    body = ""
    if style == "versus" and n == 2:
        body = (f'<div class="vs"><div class="vc a"><b>A</b><span>{rich(items[0])}</span></div>'
                f'<div class="vmid">OR</div><div class="vc b"><b>B</b><span>{rich(items[1])}</span></div></div>')
    elif style != "statement" and items:
        body = items_html(style, items, isize)

    bg = (f'<div class="photo" style="background-image:url({data_uri(ROOT / photo)})"></div><div class="fade"></div>'
          if photo else BALL)
    tag = f'<div class="tag">{html.escape(spec["tag"].upper())}</div>' if spec.get("tag") else ""
    kicker = f'<div class="kick"><span></span>{html.escape(spec["kicker"].upper())}</div>' if spec.get("kicker") else ""
    sub = f'<p class="sub">{rich(spec["sub"])}</p>' if spec.get("sub") else ""
    right = (f'<div class="url">{html.escape(spec["footer"])}<span>→</span></div>' if spec.get("footer")
             else f'<div class="hash">{html.escape(spec.get("hashtag", ""))}</div>')

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1080px;overflow:hidden;position:relative;color:{INK};font-family:Barlow,sans-serif;
 background:linear-gradient(160deg,#12233a 0%,{BG} 45%,{BG_DEEP} 100%)}}
.photo{{position:absolute;left:0;right:0;top:0;height:{"640px" if style!="statement" else "1080px"};
 background-size:cover;background-position:center 30%;filter:grayscale(1) contrast(1.15) brightness(.8)}}
.fade{{position:absolute;inset:0;background:
 linear-gradient(180deg,rgba(6,14,25,.55) 0%,rgba(14,27,44,.25) 22%,rgba(14,27,44,.55) 42%,{BG} {"58%" if style!="statement" else "78%"},{BG_DEEP} 100%),
 linear-gradient(90deg,rgba(36,136,64,.30),rgba(14,27,44,0) 55%)}}
.ball{{position:absolute;right:-250px;top:-210px;opacity:.95}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),
 linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:54px 54px}}
.frame{{position:absolute;inset:0;padding:64px 72px 0 72px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;gap:16px;font:400 40px/1 Anton;letter-spacing:.03em}}
.brand span{{color:{GREEN}}}
.grow{{flex:1}}
.tag{{align-self:flex-start;font:800 22px/1 Barlow;letter-spacing:.14em;color:{BG_DEEP};background:{GOLD};
 padding:11px 18px;border-radius:999px;margin-bottom:22px}}
.kick{{display:flex;align-items:center;gap:16px;font:800 24px/1 Barlow;letter-spacing:.22em;color:{GREEN_BAR}}}
.kick span{{width:44px;height:4px;background:{GREEN};border-radius:2px}}
h1{{font:400 {hsize}px/.94 Anton;text-transform:uppercase;letter-spacing:.004em;margin-top:20px;max-width:940px;
 text-shadow:0 4px 30px rgba(0,0,0,.35)}}
h1 em,.sub em,li em,.vc em{{font-style:normal;color:{GREEN}}}
.sub{{font:500 34px/1.3 Barlow;color:#c9d0da;margin-top:22px;max-width:860px}}
ul{{list-style:none;margin-top:38px;display:flex;flex-direction:column}}
li{{display:flex;align-items:center;gap:26px;font:600 {isize}px/1.15 Barlow;padding:{16 if n>4 else 19}px 0;
 border-top:2px solid rgba(255,255,255,.09)}}
li:last-child{{border-bottom:2px solid rgba(255,255,255,.09)}}
li.num b{{font:400 {isize+8}px/1 Anton;color:{GREEN};width:{isize+30}px;flex:none}}
li.do b,li.dont b{{flex:none;width:118px;text-align:center;font:800 20px/1 Barlow;letter-spacing:.12em;padding:12px 0;border-radius:999px}}
li.do b{{background:{GREEN_PILL};color:{GREEN_BAR}}}
li.dont b{{background:rgba(255,255,255,.07);color:{MUTED}}}
li.dont span{{color:{MUTED};text-decoration:line-through;text-decoration-color:rgba(161,170,183,.5);text-decoration-thickness:3px}}
li.poll b{{flex:none;width:{isize+26}px;height:{isize+26}px;border-radius:14px;display:grid;place-items:center;
 font:400 {isize}px/1 Anton;border:2px solid rgba(255,255,255,.25)}}
li.poll:first-child b{{background:{GREEN_DARK};border-color:{GREEN_DARK}}}
li.bar{{gap:22px;font-size:34px;padding:14px 0}} li.bar b{{width:104px;font:800 34px/1 Barlow}}
.track{{flex:1;height:22px;border-radius:11px;background:rgba(255,255,255,.08);position:relative}}
.fill{{height:100%;border-radius:11px}} .track i{{position:absolute;left:70%;top:-7px;bottom:-7px;width:3px;background:{MUTED}}}
.score{{width:52px;text-align:right;color:{MUTED};font-weight:600}}
li.bar u{{flex:none;width:172px;text-align:center;white-space:nowrap;text-decoration:none;font:800 20px/1 Barlow;
 letter-spacing:.08em;padding:10px 0;border-radius:999px}}
u.in{{background:{GREEN_PILL};color:{GREEN_BAR}}} u.near{{background:rgba(119,198,253,.15);color:{SKY}}}
.vs{{margin-top:40px;display:flex;align-items:stretch;gap:0}}
.vc{{flex:1;padding:34px 34px 38px;border-radius:24px;display:flex;flex-direction:column;gap:20px;font:600 40px/1.18 Barlow;
 background:rgba(255,255,255,.04);border:2px solid rgba(255,255,255,.10)}}
.vc b{{font:400 74px/1 Anton}} .vc.a b{{color:{GREEN}}} .vc.b b{{color:{SKY}}}
.vc.a{{border-color:rgba(82,184,47,.45)}} .vc.b{{border-color:rgba(119,198,253,.4)}}
.vmid{{align-self:center;width:84px;text-align:center;font:400 40px/1 Anton;color:{MUTED}}}
.bottom{{margin:40px -72px 0;padding:26px 72px 30px;border-top:6px solid {GREEN};background:rgba(6,14,25,.85);
 display:flex;align-items:center;justify-content:space-between}}
.foot-l{{font:700 24px/1 Barlow;letter-spacing:.2em;color:{MUTED}}}
.url{{font:700 30px/1 Barlow;color:{INK};background:{GREEN_DARK};border-radius:999px;padding:16px 30px;display:flex;gap:14px}}
.url span{{color:#b9f5c9}}
.hash{{font:700 26px/1 Barlow;color:{SKY}}}
</style></head><body>
{bg}<div class="grid"></div>
<div class="frame">
 <div class="brand">{logo(64)}<div>BASEBALL<span>FUTURE</span></div></div>
 <div class="grow"></div>
 {tag}{kicker}<h1>{rich(head)}</h1>{sub}{body}
 <div class="bottom"><div class="foot-l">COLLEGE BASEBALL RECRUITING</div>{right}</div>
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
        # Fail loudly if content overflows the frame so a run can shorten copy and retry.
        over = pg.evaluate("document.querySelector('.bottom').getBoundingClientRect().bottom > 1081")
        pg.screenshot(path=out_path, type="png")
        b.close()
    if over:
        sys.exit("OVERFLOW: content is too long for the frame; shorten headline or items")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
