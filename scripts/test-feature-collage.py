"""Check the feature collage.

The collage is absolutely positioned by percentage, and the pills hang off the
photographs they belong to. Both of those are ways to end up wider than the
screen without noticing, so the measurements that matter here are about what
escapes: pills past the edge of the page, and the page itself gaining a
sideways scroll.

Phone widths are measured inside an iframe. Headless Chromium will not open a
window under 500px, and 500px is wide enough to hide a 390px overflow.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'feature-collage.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

PROBE = """
function bx(el) {
  if (!el) return null;
  var r = el.getBoundingClientRect();
  return { l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top),
           b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) };
}
function snap(doc, win) {
  var photos = [].map.call(doc.querySelectorAll('.hp-fc__photo'), function (p) {
    var inner = p.querySelector('img') || p.querySelector('.hp-fc__ph');
    return { box: bx(p), z: win.getComputedStyle(p).zIndex,
             shot: win.getComputedStyle(p.querySelector('.hp-fc__shot')).transform,
             shadow: inner ? win.getComputedStyle(inner).boxShadow : null };
  });
  var pills = [].map.call(doc.querySelectorAll('.hp-fc__pill'), function (p) {
    return { text: p.textContent.trim(), box: bx(p),
             op: win.getComputedStyle(p).opacity,
             owner: p.parentElement.className };
  });
  var cards = [].map.call(doc.querySelectorAll('.hp-fc__card'), function (c) {
    return { box: bx(c), col: win.getComputedStyle(c).gridColumnStart,
             title: (c.querySelector('.hp-fc__card-title') || {}).textContent };
  });
  var stage = doc.querySelector('.hp-fc__stage');
  var collage = doc.querySelector('.hp-fc__collage');
  var body = doc.querySelector('.hp-fc__card-body p') || doc.querySelector('.hp-fc__card-body');
  return {
    photos: photos, pills: pills, cards: cards,
    stage: bx(stage), collage: bx(collage),
    bodySize: body ? win.getComputedStyle(body).fontSize : null,
    bodyText: body ? body.textContent.trim().slice(0, 20) : null,
    iconRow: (function () {
      var c = doc.querySelector('.hp-fc__card');
      if (!c) return null;
      var tile = c.querySelector('.hp-fc__tile'), txt = c.querySelector('.hp-fc__text');
      if (!tile || !txt) return null;
      return { tileLeft: bx(tile).l, textLeft: bx(txt).l,
               tileTop: bx(tile).t, textTop: bx(txt).t };
    })(),
    mirror: (function () {
      var c = doc.querySelectorAll('.hp-fc__card')[1];
      if (!c) return null;
      var tile = c.querySelector('.hp-fc__tile'), txt = c.querySelector('.hp-fc__text');
      var cs = win.getComputedStyle(c);
      return { dir: cs.flexDirection, align: cs.textAlign,
               tileLeft: tile ? bx(tile).l : null,
               textLeft: txt ? bx(txt).l : null };
    })(),
    cardBorder: (function () {
      var c = doc.querySelector('.hp-fc__card');
      return c ? win.getComputedStyle(c).borderTopWidth : null;
    })(),
    docW: doc.documentElement.scrollWidth,
    winW: win.innerWidth
  };
}
"""


def run(name, width=1400, overrides=None, script=''):
    page = TMP / f'fc-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True, capture_output=True)
    html = page.read_text(encoding='utf-8').replace('</body>',
        '<script>' + PROBE + script +
        "\nsetTimeout(function(){document.title='RESULT'+JSON.stringify("
        "snap(document, window));}, 400);</script></body>")
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1000', '--virtual-time-budget=6000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


def framed(name, width=390, overrides=None):
    """A real phone width, through an iframe of that width."""
    inner = TMP / f'fc-{name}-inner.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(inner)], check=True, capture_output=True)
    inner.write_text(inner.read_text(encoding='utf-8').replace(
        '</body>', '<script>' + PROBE + '</script></body>'), encoding='utf-8')
    wrap = TMP / f'fc-{name}-wrap.html'
    wrap.write_text(
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:1400px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>'
        'setTimeout(function(){'
        'var f=document.querySelector("iframe");'
        'document.title="RESULT"+JSON.stringify('
        'f.contentWindow.snap(f.contentDocument, f.contentWindow));}, 600);'
        '</script>', encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 300},1500',
        '--virtual-time-budget=6000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


# ------------------------------------------------------------- the shape ----
d = run('base')
check('three photographs in the collage',
      len(d['photos']) == 3, f"{len(d['photos'])} photos")
check('and four cards around it',
      len(d['cards']) == 4, f"{len(d['cards'])} cards")
check('the cards alternate either side of the collage',
      [c['col'] for c in d['cards']] == ['1', '3', '1', '3'],
      f"columns {[c['col'] for c in d['cards']]}")
check('and the collage sits between them',
      d['collage']['l'] > d['cards'][0]['box']['r'] - 2
      and d['collage']['r'] < d['cards'][1]['box']['l'] + 2,
      f"collage {d['collage']['l']}-{d['collage']['r']}, "
      f"left card ends {d['cards'][0]['box']['r']}, "
      f"right card starts {d['cards'][1]['box']['l']}")

# --------------------------------------------------------- the photographs --
check('they overlap rather than sit in a row',
      d['photos'][0]['box']['r'] > d['photos'][1]['box']['l'],
      f"first ends {d['photos'][0]['box']['r']}, second starts {d['photos'][1]['box']['l']}")
check('each is tilted by its own setting',
      len({p['shot'] for p in d['photos']}) == 3,
      f"{len({p['shot'] for p in d['photos']})} different transforms")
# Set deliberately against the source order, or the check proves nothing when
# the preset's own layers happen to run 1, 2, 3.
stack = run('stacking', overrides={'blocks': [
    {'type': 'photo', 'settings': {'pos_x': 0, 'width': 40, 'layer': 3}},
    {'type': 'photo', 'settings': {'pos_x': 25, 'width': 40, 'layer': 1}},
    {'type': 'photo', 'settings': {'pos_x': 50, 'width': 40, 'layer': 2}},
]})
check('the stacking order is the one set, not the source order',
      [p['z'] for p in stack['photos']] == ['3', '1', '2'],
      f"z-index {[p['z'] for p in stack['photos']]} for layers 3, 1, 2")

front = run('front', script="document.querySelectorAll('.hp-fc__photo')[0]"
                            ".setAttribute('data-front','');")
check('bringing one to the front lifts it over the others',
      int(front['photos'][0]['z']) > max(int(p['z']) for p in front['photos'][1:]),
      f"z-index {[p['z'] for p in front['photos']]}")
check('and nothing else moves when it does',
      [p['box']['l'] for p in front['photos']] == [p['box']['l'] for p in d['photos']],
      "every photo is in the same place as before")

# --------------------------------------------------------------- the pills --
check('each pill belongs to a photograph, not to the collage',
      all('hp-fc__photo' in p['owner'] for p in d['pills']),
      f"{len(d['pills'])} pills, all inside a photo")
check('and they are placed apart rather than stacked',
      len({(p['box']['l'], p['box']['t']) for p in d['pills']}) == len(d['pills']),
      f"{len(d['pills'])} pills in {len({(p['box']['l'], p['box']['t']) for p in d['pills']})} places")

# ------------------------------------------------- nothing escapes the page --
for w in (1400, 1100, 900, 750, 500):
    r = run(f'w{w}', width=w)
    out = [p['text'] for p in r['pills']
           if p['box']['l'] < 0 or p['box']['r'] > r['winW']]
    check(f'no pill hangs off the page at {w}px',
          not out and r['docW'] <= r['winW'],
          f"document {r['docW']}px in {r['winW']}px"
          + (f", escaping: {out}" if out else ""))

ph = framed('phone390')
esc = [p['text'] for p in ph['pills']
       if p['box']['l'] < 0 or p['box']['r'] > ph['winW']]
check('no pill hangs off a 390px phone',
      not esc, f"escaping: {esc}" if esc else "every pill is inside the screen")
check('and the page gains no sideways scroll there',
      ph['docW'] <= ph['winW'], f"document {ph['docW']}px in {ph['winW']}px")
check('the collage keeps its arrangement on a phone',
      ph['photos'][0]['box']['r'] > ph['photos'][1]['box']['l'],
      "the photographs still overlap")
check('and the cards stack in one column under it',
      all(c['box']['t'] > ph['collage']['b'] - 2 for c in ph['cards'])
      and len({c['box']['l'] for c in ph['cards']}) == 1,
      f"collage ends {ph['collage']['b']}, first card starts {ph['cards'][0]['box']['t']}")

# ------------------------------------------------------------ the richtext --
check("the card paragraph is the size the setting asks for, not the theme's",
      d['bodySize'] == '15px',
      f"rendered at {d['bodySize']} against a 15px setting")
check('and it is the paragraph that was typed',
      d['bodyText'] and 'Soft enough' in d['bodyText'],
      f"{d['bodyText']!r}")

# ---------------------------------------------------------- pills on hover --
hov = run('pills-hover', overrides={'settings': {'pill_visibility': 'hover'}})
check('pills can be set to show only over the photo being hovered',
      all(p['op'] == '0' for p in hov['pills']),
      f"opacities {[p['op'] for p in hov['pills']]}")
check('and they are shown outright by default',
      all(p['op'] == '1' for p in d['pills']),
      f"opacities {[p['op'] for p in d['pills']]}")

# ------------------------------------------------- depth, and the icon row --
check('every photograph carries a drop shadow, so they read as lying over one another',
      all('rgba' in (p.get('shadow') or '') and 'px' in (p.get('shadow') or '')
          for p in d['photos']),
      f"{d['photos'][0].get('shadow')}")
check('and turning the depth off removes it',
      all((p.get('shadow') or 'none') == 'none'
          for p in run('flat', overrides={'settings': {'photo_shadow': 0}})['photos']),
      "no shadow at 0%")

check('the icon sits beside the words rather than above them',
      d['iconRow'] and abs(d['iconRow']['tileTop'] - d['iconRow']['textTop']) < 30
      and d['iconRow']['tileLeft'] < d['iconRow']['textLeft'],
      f"tile at {d['iconRow']['tileLeft']}, words at {d['iconRow']['textLeft']}, "
      f"tops {d['iconRow']['tileTop']} and {d['iconRow']['textTop']}")
check('and the cards on the right are its mirror',
      d['mirror']['dir'] == 'row-reverse' and d['mirror']['align'] == 'right'
      and d['mirror']['tileLeft'] > d['mirror']['textLeft'],
      f"{d['mirror']['dir']}, text {d['mirror']['align']}, "
      f"tile at {d['mirror']['tileLeft']} against words at {d['mirror']['textLeft']}")

flat = run('no-mirror', overrides={'settings': {'icon_mirror': False}})
check('mirroring can be turned off',
      flat['mirror']['dir'] == 'row' and flat['mirror']['tileLeft'] < flat['mirror']['textLeft'],
      f"{flat['mirror']['dir']}, tile at {flat['mirror']['tileLeft']}")

check('on a phone every card reads the same way round',
      ph['mirror']['dir'] == 'row' and ph['mirror']['tileLeft'] < ph['mirror']['textLeft'],
      f"{ph['mirror']['dir']}, tile at {ph['mirror']['tileLeft']} "
      f"against words at {ph['mirror']['textLeft']}")

plain = run('plain', overrides={'settings': {'card_layout': 'plain'}})
check('the cards can drop their box so the photographs carry the section',
      plain['cardBorder'] in ('0px', '') or plain['cardBorder'].startswith('0'),
      f"card border {plain['cardBorder']} against {d['cardBorder']} when boxed")

check('the collage is wider than the columns beside it',
      d['collage']['w'] > d['cards'][0]['box']['w'] * 1.5,
      f"collage {d['collage']['w']}px against a card column of "
      f"{d['cards'][0]['box']['w']}px")

# ------------------------------------------------ the collage keeps to itself --
# A photo is placed by percentage but sized by its own height, so one can hang
# out of the bottom of the stage and land on the card beneath it. The preset is
# set so that square photographs -- what the placeholders are -- stay inside.
# A much taller photograph still needs its "Down" lowered by hand.
spill = [i for i, p in enumerate(d['photos'])
         if p['box']['b'] > d['stage']['b'] + 2]
check('at the settings it ships with, no photograph hangs out of the collage',
      not spill,
      f"stage ends {d['stage']['b']}, photos end "
      f"{[p['box']['b'] for p in d['photos']]}")

phspill = [i for i, p in enumerate(ph['photos'])
           if p['box']['b'] > ph['cards'][0]['box']['t'] + 2]
check('and none of them lands on the first card on a phone',
      not phspill,
      f"first card starts {ph['cards'][0]['box']['t']}, photos end "
      f"{[p['box']['b'] for p in ph['photos']]}")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
