"""Check the collapsible rows.

There is no JavaScript in this section at all: <details>/<summary> gives the
open and close, the keyboard handling and find-in-page, and the `name`
attribute gives one-at-a-time without a line of script. So the first thing
this asserts is that no script crept in -- the moment one does, the rows stop
working for anyone it fails for.

Transitions are switched off before measuring. Under a virtual time budget a
transition never advances, so an open panel still reports its closed height
and every check below would be measuring the animation's first frame rather
than where it lands.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path(__file__).resolve().parent.parent
SECTION = ROOT / 'sections' / 'collapsible-rows.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

STILL = ("<style>.hp-acc__panel,.hp-acc__mark,.hp-acc__bar"
         "{transition:none !important}</style>")

PROBE = """
function rowInfo(r){
  var p=r.querySelector('.hp-acc__panel');
  var inner=r.querySelector('.hp-acc__panel-inner');
  var sum=r.querySelector('.hp-acc__summary');
  var mark=r.querySelector('.hp-acc__mark');
  var ico=r.querySelector('.hp-acc__ico, .hp-acc__ico-img');
  var cs=getComputedStyle(r);
  return {
    tag:r.tagName, open:r.hasAttribute('open'), name:r.getAttribute('name'),
    title:(r.querySelector('.hp-acc__title')||{}).textContent,
    rows:getComputedStyle(p).gridTemplateRows,
    panelH:Math.round(p.getBoundingClientRect().height),
    innerScroll:inner.scrollHeight,
    summaryH:Math.round(sum.getBoundingClientRect().height),
    summaryTag:sum.tagName,
    mark:mark?getComputedStyle(mark).transform:null,
    barOpacity:(function(){var b=r.querySelector('.hp-acc__bar');
      return b?getComputedStyle(b).opacity:null;})(),
    hasIcon:!!ico,
    border:cs.borderTopWidth, radius:cs.borderTopLeftRadius,
    shadow:cs.boxShadow, bg:cs.backgroundColor
  };
}
function snap(){
  var rows=document.querySelectorAll('.hp-acc__row');
  var body=document.querySelector('.hp-acc__body p')||document.querySelector('.hp-acc__body');
  return {rows:[].map.call(rows,rowInfo),
    scripts:document.querySelectorAll('.hp-acc script, .hp-acc-section script').length,
    bodySize:body?getComputedStyle(body).fontSize:null,
    bodyText:body?body.textContent.trim().slice(0,22):null,
    titleColor:getComputedStyle(document.querySelector('.hp-acc__title')).color,
    bodyColor:body?getComputedStyle(body).color:null,
    docW:document.documentElement.scrollWidth, winW:window.innerWidth};
}
"""


def run(name, script='', width=1200, overrides=None):
    page = TMP / f'acc-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or {}), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>',
        STILL + '<script>' + PROBE + script +
        "\nsetTimeout(function(){document.title='RESULT'+JSON.stringify(snap());},350);"
        "</script></body>"), encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=6000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    # The measurement comes back through --dump-dom, which serialises the page
    # as HTML -- so an & in any text measured is re-escaped on the way out and
    # "Shipping & returns" arrives as "Shipping &amp; returns". Undo exactly
    # the three the serialiser introduces in element content; leaving &quot;
    # alone keeps the JSON's own quoting intact.
    raw = (m.group(1).replace('&lt;', '<').replace('&gt;', '>')
           .replace('&amp;', '&'))
    return json.loads(raw)


OPEN = "document.querySelectorAll('.hp-acc__row')[%d].open = true;"

res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(v):
    return [int(x) for x in re.findall(r'\d+', v)[:3]]


def contrast(a, b):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def lum(c):
        return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


# --------------------------------------------------------------- no script ---
d = run('base')
check('the section ships no JavaScript at all',
      d['scripts'] == 0,
      'the browser supplies open, close, keyboard and find-in-page')
check('each row is a real <details> with a <summary>',
      all(r['tag'] == 'DETAILS' and r['summaryTag'] == 'SUMMARY' for r in d['rows']),
      f"{[r['tag'] for r in d['rows']]}")
check('three rows, named as asked',
      [r['title'] for r in d['rows']] == ['Materials', 'Shipping & returns', 'Care & safety'],
      f"{[r['title'] for r in d['rows']]}")
check('and each carries its icon',
      all(r['hasIcon'] for r in d['rows']), 'an icon in every row')

# ------------------------------------------------------- open and closed ----
check('every row starts closed, at no height',
      all(r['panelH'] == 0 for r in d['rows']),
      f"panel heights {[r['panelH'] for r in d['rows']]}")
check('but the text is in the markup, so find-in-page can reach it',
      all(r['innerScroll'] > 0 for r in d['rows']),
      f"content heights {[r['innerScroll'] for r in d['rows']]}")

one = run('open-one', script=OPEN % 0)
check('opening a row opens it to the height of its own words',
      one['rows'][0]['panelH'] == one['rows'][0]['innerScroll']
      and one['rows'][0]['panelH'] > 20,
      f"panel {one['rows'][0]['panelH']}px against content "
      f"{one['rows'][0]['innerScroll']}px")
check('and the chevron turns over',
      one['rows'][0]['mark'] == 'matrix(-1, 0, 0, -1, 0, 0)',
      f"{one['rows'][0]['mark']}")

# ------------------------------------------------------------- one at a time -
excl = run('exclusive', script=(OPEN % 0) + (OPEN % 1))
check('opening a second row closes the first, with no script to do it',
      excl['rows'][0]['open'] is False and excl['rows'][1]['open'] is True,
      f"open flags {[r['open'] for r in excl['rows']]}")
check('which is the browser honouring one shared name',
      len({r['name'] for r in excl['rows']}) == 1,
      f"name {d['rows'][0]['name']!r} on every row")

many = run('many', script=(OPEN % 0) + (OPEN % 1),
           overrides={'settings': {'one_at_a_time': False}})
check('and they can be allowed open together instead',
      many['rows'][0]['open'] and many['rows'][1]['open']
      and len({r['name'] for r in many['rows']}) == 3,
      f"open flags {[r['open'] for r in many['rows']]}, "
      f"{len({r['name'] for r in many['rows']})} distinct names")

first = run('first-open', overrides={'blocks': [
    {'type': 'row', 'settings': {'title': 'Materials', 'open': True,
                                 'body': '<p>Cotton.</p>'}},
    {'type': 'row', 'settings': {'title': 'Shipping', 'body': '<p>Fast.</p>'}},
]})
check('a row can be set to start open',
      first['rows'][0]['panelH'] > 0 and first['rows'][1]['panelH'] == 0,
      f"panel heights {[r['panelH'] for r in first['rows']]}")

# -------------------------------------------------------------- the marker ---
plus = run('plus', script=OPEN % 0, overrides={'settings': {'marker': 'plus'}})
check('the plus marker loses its upright stroke rather than spinning',
      plus['rows'][0]['barOpacity'] == '0' and plus['rows'][1]['barOpacity'] == '1',
      f"open row bar {plus['rows'][0]['barOpacity']}, "
      f"closed row bar {plus['rows'][1]['barOpacity']}")

# --------------------------------------------------------------- the style ---
check('the rows wear the site: outline, rounding and a hard shadow',
      d['rows'][0]['border'] == '2px' and d['rows'][0]['radius'] == '18px'
      and '0px' in d['rows'][0]['shadow'],
      f"outline {d['rows'][0]['border']}, radius {d['rows'][0]['radius']}, "
      f"shadow {d['rows'][0]['shadow'][:40]}")

div = run('divided', overrides={'settings': {'row_style': 'divided'}})
check('and they can be hairlines instead, to sit quieter by a buy box',
      div['rows'][0]['radius'] == '0px' and div['rows'][0]['shadow'] == 'none',
      f"radius {div['rows'][0]['radius']}, shadow {div['rows'][0]['shadow']}")

# ------------------------------------------------------------- reachability --
check('the handle is a comfortable target on any pointer',
      all(r['summaryH'] >= 44 for r in d['rows']),
      f"summary heights {[r['summaryH'] for r in d['rows']]}")

# ------------------------------------------------------------ the richtext ---
check("the row text is the size the setting asks for, not the theme's",
      d['bodySize'] == '16px', f"rendered at {d['bodySize']} against a 16px setting")
check('and it is the words that were typed',
      d['bodyText'] and 'Double gauze' in d['bodyText'], f"{d['bodyText']!r}")

# --------------------------------------------------------------- contrast ----
row_bg = rgb(d['rows'][0]['bg']) if 'rgba(0, 0, 0, 0)' not in d['rows'][0]['bg'] else [252, 251, 246]
check('the titles read on the row',
      contrast(rgb(d['titleColor']), row_bg) >= 4.5,
      f"{contrast(rgb(d['titleColor']), row_bg)}:1")
check('and so does the text inside it',
      contrast(rgb(d['bodyColor']), row_bg) >= 4.5,
      f"{contrast(rgb(d['bodyColor']), row_bg)}:1")

# ----------------------------------------------------------------- widths ----
for w in (1200, 750, 500):
    r = run(f'w{w}', width=w)
    check(f'nothing runs off the page at {w}px',
          r['docW'] <= r['winW'], f"document {r['docW']}px in {r['winW']}px")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
