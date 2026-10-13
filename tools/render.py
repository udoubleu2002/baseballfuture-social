"""Render a BaseballFuture social graphic (1080x1080 PNG) from a JSON spec.

Look: black background, neon-green accents, heavy slanted all-caps headline with a green
brush stroke, the BaseballFuture logo lockup at the top, and a baseballfuture.com call-to-action
box at the bottom of EVERY graphic.

Usage: python3 tools/render.py spec.json graphics/2026-10-13.png

Spec fields:
  kicker    small label above the headline, e.g. "For baseball parents"
  headline  main line. Rendered in caps. Wrap words in *asterisks* to make them green.
  sub       optional supporting sentence under the headline (sentence case)
  items     list of short lines (3-4, under ~30 characters each; bars may have 5)
  style     "list"      numbered rows (default)
            "dodont"    items start with "DO:" or "DON'T:"
            "poll"      lettered A/B/C/D options
            "versus"    exactly two items, option A vs option B (big VS in the middle)
            "statement" big headline + sub only (items ignored)
            "bars"      items are "Label|score" (0-100), like the report's fit bars
  ask       optional bold question in a green-bordered box above the footer,
            e.g. "What's your choice? Reply A or B"; *asterisks* turn words green
  photo     optional path (relative to repo root) of a photo in assets/photos/.
            The photo fills the right side and fades into black on the left.
  cta       optional footer line above the URL (default "See what the numbers say at")
  hashtag   optional, shown under the footer box (default "#BaseballRecruiting")

The footer box with baseballfuture.com is always drawn; a PNG cannot carry a clickable link,
so the clickable URL goes in the caption (see PLAYBOOK.md).

Exits with "OVERFLOW" if the content does not fit; shorten the copy and rerun.
"""
import base64, html, json, mimetypes, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "brand" / "logo-lockup.png"

# Brand tokens (from the BaseballFuture reference posts)
BLACK = "#050705"
PANEL = "rgba(14,18,14,.86)"
INK = "#ffffff"
SOFT = "#e6ebe6"
MUTED = "#a9b3a9"
NEON = "#6fe32a"      # main green
NEON_HI = "#8cff3f"   # highlights / glow
NEON_DK = "#2f8f12"
LINE = "rgba(255,255,255,.14)"


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).endswith(".otf"):
        mime = "font/otf"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def face(family, file, weight):
    return f"@font-face{{font-family:'{family}';font-weight:{weight};src:url({data_uri(FONTS / file)})}}"


FACES = "".join([
    face("Anton", "Anton-Regular.ttf", 400),
    face("Barlow", "Barlow-Medium.ttf", 500),
    face("Barlow", "Barlow-SemiBold.ttf", 600),
    face("Barlow", "Barlow-Bold.ttf", 700),
    face("Barlow", "Barlow-ExtraBold.ttf", 800),
])

# Rough brush stroke used under the headline and behind "VS".
BRUSH = f"""<svg class="brush" viewBox="0 0 600 40" preserveAspectRatio="none">
<path d="M4 24 C60 14 140 12 230 13 C330 14 450 10 596 6 L590 15 C470 20 360 24 250 26
 C170 28 90 31 14 36 Z" fill="{NEON}"/>
<path d="M30 30 C120 24 260 22 420 20 L414 25 C280 28 150 31 40 34 Z" fill="{NEON_HI}" opacity=".55"/>
</svg>"""

# Neon slashes and glow in the corners when there is no photo.
DECOR = f"""<svg class="decor" viewBox="0 0 1080 1080" width="1080" height="1080">
<defs><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>
<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/></filter></defs>
<rect width="1080" height="1080" filter="url(#n)"/>
<path d="M-30 560 L36 330 L48 330 L-18 560 Z" fill="{NEON}" opacity=".9"/>
<path d="M-30 640 L44 380 L50 380 L-24 640 Z" fill="{NEON}" opacity=".4"/>
<path d="M1120 760 L980 1120 L1010 1120 L1150 760 Z" fill="{NEON}" opacity=".9"/>
<path d="M1120 640 L940 1120 L954 1120 L1134 640 Z" fill="{NEON}" opacity=".4"/>
</svg>"""

BARS_ICON = f"""<svg viewBox="0 0 60 60" width="64" height="64"><g fill="{NEON}">
<rect x="4" y="38" width="12" height="18" rx="2"/><rect x="24" y="24" width="12" height="32" rx="2"/>
<rect x="44" y="8" width="12" height="48" rx="2"/></g></svg>"""

CHECK = f'<svg viewBox="0 0 24 24" width="34" height="34"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="{BLACK}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CROSS = f'<svg viewBox="0 0 24 24" width="28" height="28"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="#ff5a5a" stroke-width="3.4" stroke-linecap="round"/></svg>'


def rich(text):
    return re.sub(r"\*(.+?)\*", r'<em>\1</em>', html.escape(text))


def slanted(text):
    """Headline words as slanted inline-blocks, so every line leans the same way."""
    out, green = [], False
    for part in re.split(r"(\*)", text):
        if part == "*":
            green = not green
            continue
        for w in part.split():
            cls = ' class="g"' if green else ""
            out.append(f"<span{cls}>{html.escape(w)}</span>")
    return " ".join(out)


def items_html(style, items, isize):
    out = []
    if style == "dodont":
        for it in items:
            kind, _, txt = it.partition(":")
            good = kind.strip().upper() == "DO"
            out.append(f'<li class="{"do" if good else "dont"}"><b>{CHECK if good else CROSS}</b>'
                       f'<span>{rich(txt.strip())}</span></li>')
    elif style == "poll":
        for i, it in enumerate(items):
            out.append(f'<li class="poll"><b><i>{chr(65+i)}</i></b><span>{rich(it)}</span></li>')
    elif style == "bars":
        for it in items:
            label, _, score = it.partition("|")
            s = max(0, min(100, int(score or 0)))
            out.append(f'<li class="bar"><b>{html.escape(label)}</b><div class="track"><div class="fill" '
                       f'style="width:{s}%;opacity:{1 if s >= 70 else .55}"></div></div>'
                       f'<span class="score">{s}</span></li>')
    else:
        for i, it in enumerate(items):
            out.append(f'<li class="num"><b><i>{i+1}</i></b><span>{rich(it)}</span></li>')
    return f'<ul class="{style}" style="--is:{isize}px">{"".join(out)}</ul>'


def build(spec):
    style = spec.get("style", "list")
    items = spec.get("items", [])
    n = len(items)
    photo = spec.get("photo")
    head = spec["headline"]
    hl = len(head.replace("*", ""))
    wide = not photo
    has_body = style != "statement" and items

    # Headline size: Anton is condensed, so it can run large.
    if style == "statement":
        hsize = 150 if hl <= 24 else 128 if hl <= 40 else 110
    elif has_body:
        hsize = 116 if hl <= 18 else 100 if hl <= 28 else 88 if hl <= 40 else 78
    else:
        hsize = 120
    if not wide:
        hsize = int(hsize * .82)
    if style == "bars" or n >= 5:
        hsize = min(hsize, 84)
    if style == "versus":
        hsize = min(hsize, 104)
    isize = 44 if n <= 3 else 41 if n <= 4 else 36

    body = ""
    if style == "versus" and n == 2:
        body = (f'<div class="vs"><div class="vc"><b><i>A</i></b><span>{rich(items[0])}</span></div>'
                f'<div class="vsmark"><span>VS</span></div>'
                f'<div class="vc"><b><i>B</i></b><span>{rich(items[1])}</span></div></div>')
    elif has_body:
        body = items_html(style, items, isize)

    bg = (f'<div class="photo" style="background-image:url({data_uri(ROOT / photo)})"></div><div class="fade"></div>'
          if photo else "")
    kicker = f'<div class="kick">{html.escape(spec["kicker"])}</div>' if spec.get("kicker") else ""
    sub = f'<p class="sub">{rich(spec["sub"])}</p>' if spec.get("sub") else ""
    ask = f'<div class="ask">{rich(spec["ask"])}</div>' if spec.get("ask") else ""
    cta = html.escape(spec.get("cta", "See what the numbers say at"))
    hashtag = html.escape(spec.get("hashtag", "#BaseballRecruiting"))
    center = style in ("versus", "statement") and wide

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1080px;overflow:hidden;position:relative;color:{INK};font-family:Barlow,sans-serif;
 -webkit-font-smoothing:antialiased;
 background:radial-gradient(60% 45% at 50% 38%,rgba(111,227,42,.10) 0%,rgba(5,7,5,0) 70%),
 radial-gradient(50% 40% at 100% 0%,rgba(111,227,42,.10) 0%,rgba(5,7,5,0) 70%),
 linear-gradient(180deg,#0b0f0b 0%,{BLACK} 100%)}}
.decor{{position:absolute;inset:0}}
.photo{{position:absolute;right:0;top:0;bottom:0;width:640px;background-size:cover;background-position:center 25%}}
.fade{{position:absolute;inset:0;background:linear-gradient(90deg,{BLACK} 38%,rgba(5,7,5,.75) 52%,rgba(5,7,5,0) 75%),
 linear-gradient(0deg,{BLACK} 0%,rgba(5,7,5,0) 30%)}}
.frame{{position:absolute;inset:0;padding:44px 64px 0;display:flex;flex-direction:column}}
.brand{{display:flex;justify-content:{"center" if center else "flex-start"}}}
.brand img{{height:76px}}
.mid{{flex:1;display:flex;flex-direction:column;justify-content:center;{"align-items:center;text-align:center" if center else ""};
 max-width:{"100%" if wide else "560px"}}}
.kick{{font:700 30px/1 Barlow;letter-spacing:.12em;text-transform:uppercase;color:{NEON};margin-bottom:14px}}
h1{{font:400 {hsize}px/.98 Anton;text-transform:uppercase;letter-spacing:.005em;text-shadow:0 4px 0 rgba(0,0,0,.35)}}
h1 span{{display:inline-block;transform:skewX(-9deg)}}
h1 .g{{font-style:normal;color:{NEON};text-shadow:0 0 28px rgba(111,227,42,.35)}}
.brush{{display:block;width:{"78%" if center else "70%"};height:26px;margin:16px 0 0;{"align-self:center" if center else ""}}}
.sub{{font:600 36px/1.25 Barlow;color:{SOFT};margin-top:20px;max-width:900px}}
.sub em{{font-style:normal;color:{NEON};font-weight:800}}
ul{{list-style:none;margin-top:30px;display:flex;flex-direction:column;gap:12px;align-self:stretch;text-align:left}}
li{{display:flex;align-items:center;gap:22px;font:700 var(--is)/1.15 Barlow;color:{INK};
 background:{PANEL};border:1.5px solid {LINE};border-left:6px solid {NEON};padding:14px 22px;transform:skewX(-6deg)}}
li>*{{transform:skewX(6deg)}}
li em{{font-style:normal;color:{NEON}}}
li b{{flex:none;width:56px;height:56px;display:grid;place-items:center;background:{NEON};color:{BLACK};
 font:400 34px/1 Anton}}
li b i{{font-style:normal;transform:skewX(-6deg)}}
li.dont{{border-left-color:#ff5a5a}} li.dont b{{background:rgba(255,90,90,.12);border:2px solid #ff5a5a}}
li.dont span{{color:{SOFT}}}
li.bar{{gap:20px;padding:8px 22px}} li.bar b{{width:110px;background:none;color:{INK};font:400 40px/1 Anton;justify-content:start}}
.track{{flex:1;height:24px;background:rgba(255,255,255,.08)}}
.fill{{height:100%;background:linear-gradient(90deg,{NEON_DK},{NEON_HI})}}
.score{{width:62px;text-align:right;font:400 38px/1 Anton;color:{NEON}}}
.vs{{margin-top:34px;display:grid;grid-template-columns:1fr 120px 1fr;align-items:center;align-self:stretch}}
.vc{{background:{PANEL};border:2px solid {NEON};padding:30px 28px 32px;display:flex;flex-direction:column;
 align-items:flex-start;gap:18px;text-align:left;font:800 40px/1.12 Barlow;text-transform:uppercase;min-height:260px;
 transform:skewX(-6deg)}}
.vc>*{{transform:skewX(6deg)}} .vc em{{font-style:normal;color:{NEON}}}
.vc b{{width:70px;height:70px;display:grid;place-items:center;background:{NEON};color:{BLACK};font:400 48px/1 Anton}}
.vc b i{{font-style:normal}}
.vsmark{{display:grid;place-items:center}}
.vsmark span{{font:400 84px/1 Anton;transform:skewX(-10deg);color:{INK};
 text-shadow:0 0 0 {NEON},4px 4px 0 {NEON_DK}}}
.ask{{margin-top:28px;align-self:stretch;text-align:center;font:400 52px/1.05 Anton;text-transform:uppercase;
 transform:skewX(-8deg);padding:16px 20px;border:2.5px solid {NEON};background:rgba(0,0,0,.6)}}
.ask em{{font-style:normal;color:{NEON}}}
.foot{{margin:26px 0 0;display:flex;align-items:center;gap:26px;padding:18px 34px;border:3px solid {NEON};
 border-radius:22px;background:rgba(0,0,0,.78);box-shadow:0 0 30px rgba(111,227,42,.25),inset 0 0 24px rgba(111,227,42,.10)}}
.foot .div{{width:2px;align-self:stretch;background:{NEON};opacity:.8}}
.foot .t{{display:flex;flex-direction:column;gap:6px}}
.foot .c{{font:700 30px/1 Barlow;color:{INK}}}
.foot .u{{font:400 66px/1 Anton;color:{NEON};transform:skewX(-9deg);transform-origin:left bottom;
 text-shadow:0 0 24px rgba(111,227,42,.35)}}
.hash{{display:flex;align-items:center;gap:22px;margin:16px 0 26px;font:700 22px/1 Barlow;letter-spacing:.32em;color:{MUTED}}}
.hash:before,.hash:after{{content:"";flex:1;height:1.5px;background:linear-gradient(90deg,rgba(111,227,42,0),{NEON})}}
.hash:after{{background:linear-gradient(90deg,{NEON},rgba(111,227,42,0))}}
</style></head><body>
{DECOR if not photo else ""}{bg}
<div class="frame">
 <div class="brand"><img src="{data_uri(LOGO)}" alt=""></div>
 <div class="mid">{kicker}<h1>{slanted(head)}</h1>{BRUSH}{sub}{body}{ask}</div>
 <div class="foot">{BARS_ICON}<div class="div"></div><div class="t"><div class="c">{cta}</div>
  <div class="u">BaseballFuture.com</div></div></div>
 <div class="hash">{hashtag.upper()}</div>
</div></body></html>"""


def main(spec_path, out_path):
    spec = json.loads(Path(spec_path).read_text())
    spec = spec.get("graphic", spec)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        pg.set_content(build(spec))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        over = pg.evaluate("""(() => {
          const m = document.querySelector('.mid');
          const kids = [...m.children];
          const top = Math.min(...kids.map(k => k.getBoundingClientRect().top));
          const brand = document.querySelector('.brand').getBoundingClientRect().bottom;
          const h = document.querySelector('.hash').getBoundingClientRect().bottom;
          const wide = [...document.querySelectorAll('h1,li span,.vc span,.ask,.sub')]
            .some(e => e.scrollWidth > e.clientWidth + 30);
          return top < brand + 8 || h > 1080 || wide;
        })()""")
        pg.screenshot(path=out_path, type="png")
        b.close()
    if over:
        sys.exit("OVERFLOW: content is too long for the frame; shorten headline or items")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
