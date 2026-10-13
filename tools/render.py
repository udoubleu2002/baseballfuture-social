"""Render a BaseballFuture social graphic (1080x1080 PNG) from a JSON spec.

Look: near-black navy background, kelly-green accents, heavy slanted all-caps headline with a green
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
  visual    the picture on the right side (every post has one):
            "report"    the BaseballFuture scouting-report mockup (assets/visuals/report-mockup.png)
            "fitcard"   close-up of the report's "Athletic fit by level" bars (crisp vector);
                        uses "fit": ["D1|68", "D2|82", ...] or the bars items; "best": "D2" highlights a row
            "radar"     radar-gun readout; "stat": {"label": "Exit velocity", "value": "92.6", "unit": "MPH"}
            "stopwatch" stopwatch readout; "stat": {"label": "60-yard dash", "value": "6.85", "unit": "SEC"}
            "photo"     uses "photo" below
            Default: "fitcard" for bars, otherwise "photo" if a photo is given, otherwise "report".
            Numbers on visuals are labeled as a sample player.
  photo     path (relative to repo root) of a player photo in assets/photos/ (for visual "photo").
            It fills the right side and fades into the background on the left.
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

# Brand tokens (from the BaseballFuture reference posts)
BLACK = "#0a1524"   # deep end of the site navy
NAVY = "#0e1b2c"    # site background blue (baseballfuture.com)
PANEL = "rgba(22,40,64,.72)"
INK = "#ffffff"
SOFT = "#e6ebe6"
MUTED = "#a9b3a9"
GREEN = "#52b82f"     # brand kelly green (sampled from the logo)
GREEN_HI = "#6cc94a"  # lighter tint, used sparingly
GREEN_DK = "#2e7d23"  # deep green for fills
LINE = "rgba(255,255,255,.14)"
REPORT = ROOT / "assets" / "visuals" / "report-mockup.png"


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
 C170 28 90 31 14 36 Z" fill="{GREEN}"/>
</svg>"""

# Neon slashes and glow in the corners when there is no photo.
DECOR = f"""<svg class="decor" viewBox="0 0 1080 1080" width="1080" height="1080">
<defs><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>
<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .05 0"/></filter></defs>
<rect width="1080" height="1080" filter="url(#n)"/>
<path d="M1120 800 L990 1120 L1004 1120 L1134 800 Z" fill="{GREEN}" opacity=".75"/>
<path d="M1120 700 L956 1120 L962 1120 L1126 700 Z" fill="{GREEN}" opacity=".3"/>
</svg>"""

def logo(size):
    """BaseballFuture mark (ball with stitched seam and arrow), drawn as vector so it stays crisp."""
    return f"""<svg viewBox="0 0 100 100" width="{size}" height="{size}">
<circle cx="50" cy="50" r="41" fill="none" stroke="#f2f4f7" stroke-width="7"/>
<path d="M38 22 C22 40 24 66 34 82" fill="none" stroke="#6b7480" stroke-width="3"/>
<path d="M30 84 C42 70 56 50 72 22" fill="none" stroke="#f2f4f7" stroke-width="3"/>
<g stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
<path d="M33 72 l9 -2"/><path d="M40 62 l9 -2"/><path d="M47 52 l9 -2"/><path d="M54 42 l9 -2"/><path d="M61 32 l9 -2"/></g>
<path d="M66 18 L84 10 L80 30 Z" fill="{GREEN}"/></svg>"""


BARS_ICON = f"""<svg viewBox="0 0 60 60" width="64" height="64"><g fill="{GREEN}">
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


def fitcard(spec):
    rows = spec.get("fit") or (spec.get("items") if spec.get("style") == "bars" else None) \
        or ["D1|68", "D2|82", "NAIA|91", "JUCO|90", "D3|91"]
    best = spec.get("best", "")
    out = []
    for r in rows:
        label, _, score = r.partition("|")
        v = max(0, min(100, int(score or 0)))
        ok = v >= 70
        hl = " hl" if label.strip().upper() == best.upper() else ""
        out.append(f'<div class="fr{hl}"><b>{html.escape(label)}</b><div class="ft"><div class="ff {"ok" if ok else "near"}" '
                   f'style="width:{v}%"></div><i></i></div><span class="fs">{v}</span>'
                   f'<u class="{"ok" if ok else "near"}">{"IN RANGE" if ok else "NEAR RANGE"}</u></div>')
    return (f'<div class="fitwrap"><div class="pill">Sample player · fit score</div><div class="fitcard">'
            f'<div class="fh">Athletic fit by level &nbsp;·&nbsp; out of 100</div>{"".join(out)}</div></div>')


def gauge(kind, spec):
    st = spec.get("stat") or ({"label": "60-yard dash", "value": "6.85", "unit": "SEC"} if kind == "stopwatch"
                              else {"label": "Exit velocity", "value": "92.6", "unit": "MPH"})
    lab, val, unit = (html.escape(str(st.get(k, ""))) for k in ("label", "value", "unit"))
    if kind == "stopwatch":
        ticks = "".join(f'<line x1="200" y1="62" x2="200" y2="{80 if i % 5 == 0 else 72}" stroke="#9aa4b1" '
                        f'stroke-width="{4 if i % 5 == 0 else 2}" transform="rotate({i*6} 200 230)"/>' for i in range(60))
        return f"""<div class="gwrap"><div class="pill">Sample reading</div>
<div class="watch"><svg viewBox="0 0 400 460" width="430" height="494">
<rect x="176" y="0" width="48" height="34" rx="6" fill="#c9d1db"/><rect x="186" y="30" width="28" height="22" fill="#9aa4b1"/>
<rect x="292" y="40" width="34" height="22" rx="5" fill="#9aa4b1" transform="rotate(40 309 51)"/>
<circle cx="200" cy="230" r="186" fill="#1a2533" stroke="#c9d1db" stroke-width="14"/>
<circle cx="200" cy="230" r="164" fill="#0b121b"/>{ticks}
<circle cx="200" cy="230" r="174" fill="none" stroke="{GREEN}" stroke-width="8" stroke-linecap="round"
 stroke-dasharray="{2*3.1416*174*.68:.0f} 2000" transform="rotate(-90 200 230)"/></svg>
<div class="wv"><div class="gl">{lab}</div><div class="gn">{val}</div><div class="gu">{unit}</div></div></div></div>"""
    return f"""<div class="gwrap"><div class="pill">Sample reading</div>
<div class="radar"><div class="rscreen"><div class="gl">{lab}</div><div class="gn">{val}</div><div class="gu">{unit}</div></div>
<div class="rlens"></div></div><div class="rhandle"></div></div>"""


def visual_html(spec, kind):
    if kind == "photo" and spec.get("photo"):
        return (f'<div class="photo" style="background-image:url({data_uri(ROOT / spec["photo"])})"></div>'
                f'<div class="fade"></div>')
    if kind == "fitcard":
        inner = fitcard(spec)
    elif kind in ("radar", "stopwatch"):
        inner = gauge(kind, spec)
    else:
        inner = f'<img class="report" src="{data_uri(REPORT)}" alt="">'
    return f'<div class="vis v-{kind}">{inner}</div>'


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
    vkind = spec.get("visual") or ("fitcard" if style == "bars" else "photo" if photo else "report")
    wide = False  # every post carries a visual on the right; text sits in the left column
    has_body = style not in ("statement", "bars") and items

    # Headline size: Anton is condensed, so it can run large.
    if style == "statement":
        hsize = 150 if hl <= 24 else 128 if hl <= 40 else 110
    elif has_body:
        hsize = 116 if hl <= 18 else 100 if hl <= 28 else 88 if hl <= 40 else 78
    else:
        hsize = 120
    if style in ("statement", "bars"):
        hsize = 92 if hl <= 24 else 84 if hl <= 34 else 74
    else:
        hsize = 84 if hl <= 18 else 76 if hl <= 28 else 68 if hl <= 40 else 62
    if style == "versus":
        hsize = min(hsize, 76)
    isize = 36 if n <= 3 else 34 if n <= 4 else 31

    body = ""
    if style == "versus" and n == 2:
        body = (f'<div class="vs"><div class="vc"><b><i>A</i></b><span>{rich(items[0])}</span></div>'
                f'<div class="vsmark"><span>VS</span></div>'
                f'<div class="vc"><b><i>B</i></b><span>{rich(items[1])}</span></div></div>')
    elif has_body:
        body = items_html(style, items, isize)

    bg = visual_html(spec, vkind)
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
 background:radial-gradient(90% 70% at 85% 5%,#16304f 0%,rgba(14,27,44,0) 60%),
 linear-gradient(180deg,{NAVY} 0%,{BLACK} 100%)}}
.decor{{position:absolute;inset:0}}
.vis{{position:absolute;right:0;top:132px;width:460px;height:740px;display:grid;place-items:center;z-index:1}}
.vis.v-report{{right:-150px;width:720px}}
.report{{width:720px;transform:rotate(-2deg);
 -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 16%,#000 100%)}}
.pill{{position:relative;z-index:2;align-self:flex-start;margin:0 0 -18px 22px;background:{GREEN};color:#fff;
 font:800 19px/1 Barlow;letter-spacing:.1em;text-transform:uppercase;padding:11px 18px;border-radius:999px;border:3px solid #fff}}
.fitwrap,.gwrap{{display:flex;flex-direction:column;transform:rotate(-3deg)}}
.gwrap{{transform:rotate(-3deg) scale(.86)}}
.fitcard{{width:436px;background:#fff;border:6px solid {GREEN};border-radius:26px;padding:38px 18px 18px;color:#13243b;
 box-shadow:0 30px 60px rgba(0,0,0,.55)}}
.fh{{font:700 15px/1 Barlow;letter-spacing:.1em;text-transform:uppercase;color:#4c5b6e;margin:0 0 14px 8px}}
.fr{{display:flex;align-items:center;gap:10px;padding:10px 8px;border-radius:8px}}
.fr.hl{{background:#e6f3e8}}
.fr b{{width:60px;font:800 25px/1 Barlow;color:#13243b}}
.ft{{flex:1;height:18px;border-radius:9px;background:#e1e6ec;position:relative}}
.ff{{height:100%;border-radius:9px}} .ff.ok{{background:#2b8c47}} .ff.near{{background:#2f7fd6}}
.ft i{{position:absolute;left:70%;top:-5px;bottom:-5px;width:2.5px;background:#13243b}}
.fs{{width:34px;text-align:right;font:600 22px/1 Barlow;color:#5b6878}}
.fr u{{width:104px;text-align:right;text-decoration:none;font:800 16px/1 Barlow;letter-spacing:.04em}}
.fr u.ok{{color:#2b8c47}} .fr u.near{{color:#2f7fd6}}
.gwrap{{align-items:center}} .gwrap .pill{{margin:0 0 -16px 0;align-self:center}}
.radar{{width:460px;height:330px;border-radius:40px;background:linear-gradient(160deg,#3a4250,#161b22 70%);padding:26px;
 display:flex;gap:18px;box-shadow:0 30px 60px rgba(0,0,0,.6),inset 0 2px 0 rgba(255,255,255,.15)}}
.rscreen{{flex:1;border-radius:22px;background:#04090b;border:3px solid #232a33;display:flex;flex-direction:column;
 align-items:center;justify-content:center;gap:4px}}
.rlens{{width:70px;border-radius:18px;background:radial-gradient(circle at 40% 35%,#56606e,#0d1117 70%)}}
.rhandle{{width:110px;height:170px;margin-top:-6px;border-radius:0 0 30px 30px;background:linear-gradient(90deg,#14181e,#2b323c,#14181e)}}
.gl{{font:700 26px/1 Barlow;letter-spacing:.08em;text-transform:uppercase;color:#d7dde4}}
.gn{{font:400 130px/1 Anton;color:{GREEN};letter-spacing:.02em}}
.gu{{font:700 24px/1 Barlow;letter-spacing:.12em;color:#d7dde4}}
.watch{{position:relative}} .wv{{position:absolute;left:0;right:0;top:150px;display:flex;flex-direction:column;align-items:center;gap:6px}}
.watch .gn{{font-size:120px}} .watch .gl{{font-size:22px}}
.photo{{position:absolute;right:0;top:0;bottom:0;width:640px;background-size:cover;background-position:center 25%}}
.fade{{position:absolute;inset:0;background:linear-gradient(90deg,{BLACK} 38%,rgba(10,21,36,.75) 52%,rgba(10,21,36,0) 75%),
 linear-gradient(0deg,{BLACK} 0%,rgba(10,21,36,0) 30%)}}
.frame{{position:absolute;inset:0;padding:44px 64px 0;display:flex;flex-direction:column}}
.brand{{display:flex;justify-content:{"center" if center else "flex-start"}}}
.brand{{align-items:center;gap:18px}}
.wm{{font:400 50px/1 Anton;letter-spacing:.02em;color:#f2f4f7}} .wm span{{color:{GREEN}}}
.mid{{flex:1;padding-right:0;display:flex;flex-direction:column;justify-content:center;{"align-items:center;text-align:center" if center else ""};
 max-width:500px;position:relative;z-index:2}}
.kick{{font:700 26px/1.15 Barlow;letter-spacing:.1em;text-transform:uppercase;color:{GREEN};margin-bottom:14px}}
h1{{font:400 {hsize}px/.98 Anton;text-transform:uppercase;letter-spacing:.005em;text-shadow:0 4px 0 rgba(0,0,0,.35)}}
h1 span{{display:inline-block;transform:skewX(-9deg)}}
h1 .g{{font-style:normal;color:{GREEN}}}
.brush{{display:block;width:{"78%" if center else "86%"};height:26px;margin:16px 0 0;{"align-self:center" if center else ""}}}
.sub{{font:600 33px/1.25 Barlow;color:{SOFT};margin-top:20px}}
.sub em{{font-style:normal;color:{GREEN};font-weight:800}}
ul{{list-style:none;margin-top:30px;display:flex;flex-direction:column;gap:12px;align-self:stretch;text-align:left}}
li{{display:flex;align-items:center;gap:18px;font:700 var(--is)/1.15 Barlow;color:{INK};
 background:{PANEL};border:1.5px solid {LINE};border-left:4px solid {GREEN};padding:12px 18px;transform:skewX(-6deg)}}
li>*{{transform:skewX(6deg)}}
li em{{font-style:normal;color:{GREEN}}}
li b{{flex:none;width:50px;height:50px;display:grid;place-items:center;background:{GREEN};color:{BLACK};
 font:400 34px/1 Anton}}
li b i{{font-style:normal;transform:skewX(-6deg)}}
li.dont{{border-left-color:#ff5a5a}} li.dont b{{background:rgba(255,90,90,.12);border:2px solid #ff5a5a}}
li.dont span{{color:{SOFT}}}
li.bar{{gap:20px;padding:8px 22px}} li.bar b{{width:110px;background:none;color:{INK};font:400 40px/1 Anton;justify-content:start}}
.track{{flex:1;height:24px;background:rgba(255,255,255,.08)}}
.fill{{height:100%;background:{GREEN}}}
.score{{width:62px;text-align:right;font:400 38px/1 Anton;color:{INK}}}
.vs{{margin-top:26px;display:flex;flex-direction:column;align-self:stretch}}
.vc{{background:{PANEL};border:2px solid {LINE};border-top:4px solid {GREEN};padding:30px 28px 32px;display:flex;flex-direction:column;
 flex-direction:row;align-items:center;gap:20px;padding:18px 22px;text-align:left;font:800 32px/1.12 Barlow;text-transform:uppercase;
 transform:skewX(-6deg)}}
.vc>*{{transform:skewX(6deg)}} .vc em{{font-style:normal;color:{GREEN}}}
.vc b{{flex:none;width:58px;height:58px;display:grid;place-items:center;background:{GREEN};color:{BLACK};font:400 48px/1 Anton}}
.vc b i{{font-style:normal}}
.vsmark{{display:grid;place-items:center;margin:4px 0}}
.vsmark span{{font:400 60px/1 Anton;transform:skewX(-10deg);color:{INK};
 text-shadow:4px 4px 0 {GREEN_DK}}}
.ask{{margin-top:24px;align-self:stretch;text-align:center;font:400 40px/1.05 Anton;text-transform:uppercase;
 transform:skewX(-8deg);padding:16px 20px;border:2px solid {LINE};background:rgba(0,0,0,.45)}}
.ask em{{font-style:normal;color:{GREEN}}}
.foot{{margin:22px 0 0;align-self:flex-start;display:flex;align-items:center;gap:18px;padding:12px 26px;
 border:2px solid {GREEN};border-radius:16px;background:rgba(6,14,25,.6)}}
.foot svg{{width:40px;height:40px}}
.foot .div{{width:2px;align-self:stretch;background:{LINE}}}
.foot .t{{display:flex;flex-direction:column;gap:4px}}
.foot .c{{font:700 21px/1 Barlow;color:{INK}}}
.foot .u{{font:400 42px/1 Anton;color:{GREEN};transform:skewX(-9deg);transform-origin:left bottom}}
.bottom{{display:flex;align-items:center;justify-content:space-between;gap:24px;margin:22px 0 40px}}
.bottom .foot{{margin:0}}
.hash{{font:700 20px/1 Barlow;letter-spacing:.24em;color:{MUTED};margin-right:70px}}
</style></head><body>
{DECOR if vkind != "photo" else ""}{bg}
<div class="frame">
 <div class="brand">{logo(80)}<div class="wm">BASEBALL<span>FUTURE</span></div></div>
 <div class="mid">{kicker}<h1>{slanted(head)}</h1>{BRUSH}{sub}{body}{ask}</div>
 <div class="bottom"><div class="foot">{BARS_ICON}<div class="div"></div><div class="t"><div class="c">{cta}</div>
  <div class="u">BaseballFuture.com</div></div></div>
 <div class="hash">{hashtag.upper()}</div></div>
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
