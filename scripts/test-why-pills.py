"""Check the pill version of "Why choose us".

The claim worth proving is that the pills rest against each other and never on
top of each other. A rotated pill's layout box says nothing useful about that —
the transform is not in it — so this measures the shapes themselves. Each pill
is a capsule: border-radius 999px on a box of height H is a rectangle with
semicircular ends of radius H/2, which is a line segment thickened by H/2. Two
capsules intersect exactly when the distance between their segments is less
than the sum of their radii, and that is a closed-form answer rather than an
approximation.

The harness lessons from the blob reveal apply here too and are used the same
way: animation timelines do not advance under a virtual time budget, so the
settled state is forced by removing the animation rather than waited for; and
IntersectionObserver needs a layout pass it will not otherwise get.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'why-pills.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

SNAP = """
// The untransformed box plus the tilt: enough to rebuild the capsule.
function capsule(el) {
  var prev = el.style.transform;
  el.style.transform = 'none';
  var r = el.getBoundingClientRect();
  el.style.transform = prev;
  var deg = parseFloat(getComputedStyle(el).getPropertyValue('--rot')) || 0;
  var t = deg * Math.PI / 180;
  var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  var rad = r.height / 2;
  // The segment runs between the centres of the two end caps.
  var half = Math.max(r.width / 2 - rad, 0);
  return {
    deg: deg, rad: rad, w: Math.round(r.width), h: Math.round(r.height),
    cx: cx, cy: cy,
    a: { x: cx - half * Math.cos(t), y: cy - half * Math.sin(t) },
    b: { x: cx + half * Math.cos(t), y: cy + half * Math.sin(t) },
    box: { l: Math.round(r.left), r: Math.round(r.right),
           t: Math.round(r.top), b: Math.round(r.bottom) }
  };
}

function snap() {
  var root = document.querySelector('.hp-pill');
  var badge = document.querySelector('.hp-pill__badge');
  var heading = document.querySelector('.hp-pill__heading');
  var stack = document.querySelector('.hp-pill__stack');
  return {
    cls: root.className,
    sectionBox: (function () {
      var r = root.getBoundingClientRect();
      return { l: Math.round(r.left), r: Math.round(r.right) };
    })(),
    badge: badge ? (function () {
      var r = badge.getBoundingClientRect();
      return { l: Math.round(r.left), r: Math.round(r.right),
               t: Math.round(r.top), b: Math.round(r.bottom) };
    })() : null,
    headingB: heading ? Math.round(heading.getBoundingClientRect().bottom) : null,
    stackT: stack ? Math.round(stack.getBoundingClientRect().top) : null,
    pills: [].map.call(document.querySelectorAll('.hp-pill__pill'), function (el) {
      var c = getComputedStyle(el);
      var row = el.closest('.hp-pill__row');
      return {
        text: el.textContent.trim(),
        side: row.className.indexOf('--l') !== -1 ? 'l' : 'r',
        isIn: el.classList.contains('is-in'),
        opacity: Math.round(parseFloat(c.opacity) * 100) / 100,
        name: c.animationName,
        delay: c.animationDelay,
        inlineDelay: el.style.animationDelay,
        fontSize: c.fontSize,
        shadow: c.boxShadow,
        bg: c.backgroundColor,
        ink: c.color,
        cap: capsule(el)
      };
    }),
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth
  };
}
"""

POLL = """
function when(test, done, tries) {
  if (tries === undefined) tries = 200;
  void document.body.offsetHeight;
  if (test() || tries <= 0) return done();
  // Two nudges, because neither is reliable alone. Reading a layout property
  // forces style and layout. Asking for a frame is what actually schedules
  // "update the rendering", the step an intersection is computed in — but
  // requestAnimationFrame never fires at all under a virtual time budget, so
  // it cannot be waited on: whichever of the two arrives first continues, and
  // the timer guarantees one of them does.
  var moved = false;
  function step() {
    if (moved) return;
    moved = true;
    when(test, done, tries - 1);
  }
  try { requestAnimationFrame(step); } catch (e) {}
  setTimeout(step, 40);
}
function report() { document.title = 'RESULT' + JSON.stringify(snap()); }
function arrived() { return !!document.querySelector('.hp-pill__pill.is-in'); }
function tidied() {
  var els = document.querySelectorAll('.hp-pill__pill');
  for (var i = 0; i < els.length; i++) {
    if (els[i].style.animationDelay !== '') return false;
  }
  return arrived();
}
"""

# A page with nothing to draw never runs "update the rendering", and an
# intersection is computed in that step — so the observer may simply never
# deliver. An animation that never ends keeps the loop turning. It is on a
# pseudo element of the body, so it touches nothing being measured.
TICK = """<style>
  @keyframes hp-test-tick { from { opacity: 0.99; } to { opacity: 1; } }
  body::after {
    content: '';
    position: fixed;
    width: 1px;
    height: 1px;
    top: 0;
    left: 0;
    animation: hp-test-tick 50ms linear infinite;
  }
</style>"""

SETTLE = """<style>
  .hp-pill__pill.is-in { animation: none !important; }
</style>"""


def probe(mode):
    if mode == 'play':
        return ("<script>" + SNAP + POLL +
                "var el=document.querySelector('hp-pill-drop');"
                "if(el&&el.play) el.play(); setTimeout(report,60);</script>")
    if mode == 'plain':
        return "<script>" + SNAP + POLL + "setTimeout(report,400);</script>"
    wait = {'wired': 'arrived', 'tidied': 'tidied'}[mode]
    return TICK + "<script>" + SNAP + POLL + f"when({wait}, report);</script>"


def run(overrides, name, mode='play', settle=True, width=1280, flags=(), extra_head='',
        budget=6000):
    page = TMP / f'wp-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    body = page.read_text(encoding='utf-8').replace('<body>', '<body>' + extra_head)
    page.write_text(body.replace('</body>', (SETTLE if settle else '') + probe(mode) + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1000', f'--virtual-time-budget={budget}', *flags,
        '--dump-dom', 'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def _point_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    den = vx * vx + vy * vy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / den))
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return (dx * dx + dy * dy) ** 0.5


def _crosses(a, b, c, d):
    def side(p, q, r):
        return (q['x'] - p['x']) * (r['y'] - p['y']) - (q['y'] - p['y']) * (r['x'] - p['x'])
    d1, d2 = side(c, d, a), side(c, d, b)
    d3, d4 = side(a, b, c), side(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def seg_distance(p1, p2, q1, q2):
    """Exact shortest distance between two 2D segments.

    The usual closed form clamps its two parameters independently, which
    overestimates whenever the unclamped solution falls outside the segments —
    it reported 109px between two pills that a drawing put 41px apart. Either
    the segments cross, in which case the distance is zero, or the closest
    point is one of the four endpoints against the other segment.
    """
    if _crosses(p1, p2, q1, q2):
        return 0.0
    return min(
        _point_seg(p1['x'], p1['y'], q1['x'], q1['y'], q2['x'], q2['y']),
        _point_seg(p2['x'], p2['y'], q1['x'], q1['y'], q2['x'], q2['y']),
        _point_seg(q1['x'], q1['y'], p1['x'], p1['y'], p2['x'], p2['y']),
        _point_seg(q2['x'], q2['y'], p1['x'], p1['y'], p2['x'], p2['y']),
    )


def clearance(c1, c2):
    """Gap between two capsules. Negative means they are on top of each other."""
    return seg_distance(c1['a'], c1['b'], c2['a'], c2['b']) - c1['rad'] - c2['rad']


# ------------------------------------------------------- the arrangement ----
d = run({}, 'default')
labels = [p['text'] for p in d['pills']]
check('one pill per reason, in order',
      len(d['pills']) == 5 and labels[0] == 'Soft on little noses',
      f"{len(d['pills'])} pills: {labels}")
check('they alternate sides',
      [p['side'] for p in d['pills']] == ['l', 'r', 'l', 'r', 'l'],
      f"{[p['side'] for p in d['pills']]}")
check('and the tilt alternates with them',
      [p['cap']['deg'] for p in d['pills']] == [3, -3, 3, -3, 3],
      f"{[p['cap']['deg'] for p in d['pills']]}")

pairs = [(i, j) for i in range(len(d['pills'])) for j in range(i + 1, len(d['pills']))]
worst = min((clearance(d['pills'][i]['cap'], d['pills'][j]['cap']), i, j) for i, j in pairs)
check('no two pills end up on top of each other',
      worst[0] >= 0,
      f"closest pair is {worst[1]} and {worst[2]} at {round(worst[0], 1)}px apart"
      if worst[0] >= 0 else
      f"pills {worst[1]} and {worst[2]} overlap by {round(-worst[0], 1)}px")
check('and they are close enough to read as one stack',
      worst[0] <= 40, f"{round(worst[0], 1)}px at the tightest")

check('every pill stays inside the section',
      all(p['cap']['box']['l'] >= d['sectionBox']['l'] - 1
          and p['cap']['box']['r'] <= d['sectionBox']['r'] + 1 for p in d['pills']),
      f"section {d['sectionBox']['l']}–{d['sectionBox']['r']}, pills "
      f"{min(p['cap']['box']['l'] for p in d['pills'])}–"
      f"{max(p['cap']['box']['r'] for p in d['pills'])}")

for w in (1600, 1280, 990, 750, 500):
    n = run({}, f'w{w}', width=w)
    pr = [(i, j) for i in range(len(n['pills'])) for j in range(i + 1, len(n['pills']))]
    worst_w = min(clearance(n['pills'][i]['cap'], n['pills'][j]['cap']) for i, j in pr)
    inside = all(p['cap']['box']['l'] >= n['sectionBox']['l'] - 1
                 and p['cap']['box']['r'] <= n['sectionBox']['r'] + 1 for p in n['pills'])
    check(f'still no stacking, and nothing off the edge, at {w}px',
          worst_w >= 0 and inside and n['docW'] <= n['winW'],
          f"tightest {round(worst_w, 1)}px, inside the section: {inside}, "
          f"document {n['docW']}px in {n['winW']}px")

tight = run({'settings': {'pill_gap': 0, 'tilt': 12}}, 'tight')
pr = [(i, j) for i in range(len(tight['pills'])) for j in range(i + 1, len(tight['pills']))]
worst_t = min(clearance(tight['pills'][i]['cap'], tight['pills'][j]['cap']) for i, j in pr)
check('the tightest settings the editor allows still do not stack them',
      worst_t >= 0, f"gap 0 and 12deg of tilt leaves {round(worst_t, 1)}px")

big = run({'settings': {'pill_size': 80}}, 'big')
check('the size control actually changes the pills',
      float(big['pills'][0]['fontSize'][:-2]) > float(d['pills'][0]['fontSize'][:-2]),
      f"{d['pills'][0]['fontSize']} at the default, {big['pills'][0]['fontSize']} at 80")
over = run({'blocks': [{'type': 'pill', 'settings': {'label': 'Straight', 'tilt_override': 9}}]},
           'override')
check('a single pill can be tilted on its own',
      over['pills'][0]['cap']['deg'] == 9, f"{over['pills'][0]['cap']['deg']}deg")

# ------------------------------------------------------------- the shadow ---
def shadow_parts(v):
    """(colour, offset-x, offset-y, blur, spread) from a computed box-shadow."""
    if v == 'none':
        return None
    nums = re.findall(r'(-?[\d.]+)px', v)
    colour = re.match(r'rgba?\([^)]*\)', v)
    return (colour.group(0) if colour else '', [float(n) for n in nums])


sh = shadow_parts(d['pills'][0]['shadow'])
check('the pills carry a shadow by default',
      sh is not None and sh[1][2] > 0,
      f"{d['pills'][0]['shadow']}")
check('it is soft rather than the buttons\' hard edge',
      sh and sh[1][2] >= 20, f"{sh[1][2]}px of blur")
check('it sits below the pill and is tucked under it',
      sh and sh[1][1] > 0 and sh[1][3] < 0,
      f"offset {sh[1][1]}px down, spread {sh[1][3]}px")
check('and it is the ink colour, not black',
      sh and sh[0].startswith('rgba(47, 51, 38'), f"{sh[0]}")

nosh = run({'settings': {'shadow_strength': 0}}, 'noshadow')
check('0 makes it invisible',
      shadow_parts(nosh['pills'][0]['shadow'])[0].endswith(', 0)'),
      f"{nosh['pills'][0]['shadow']}")
check('and changes nothing about where the pills are',
      [p['cap']['box'] for p in nosh['pills']] == [p['cap']['box'] for p in d['pills']],
      'a box-shadow is painted, not laid out, so the arrangement is untouched')

def alpha(v):
    """The alpha out of a computed box-shadow's colour. rgb() means 1."""
    m = re.match(r'rgba\(\s*[\d.]+,\s*[\d.]+,\s*[\d.]+,\s*([\d.]+)\)', v)
    return float(m.group(1)) if m else 1.0


deep = run({'settings': {'shadow_strength': 70}}, 'deepshadow')
deep_a = alpha(deep['pills'][0]['shadow'])
base_a = alpha(d['pills'][0]['shadow'])
check('turning it up makes it stronger',
      deep_a > base_a, f"alpha {base_a} at the default, {deep_a} at 70%")

# ------------------------------------------------------------- the badge ----
check('no picture until one is chosen',
      d['badge'] is None, f"badge element present: {d['badge'] is not None}")
noimg = run({'settings': {'show_image': True}}, 'noimg')
check('and none when the toggle is on but no image is set',
      noimg['badge'] is None, 'nothing is drawn for an empty image_picker')
from PIL import Image
Image.new('RGB', (400, 400), (181, 201, 154)).save(TMP / 'badge.png')
img = run({'settings': {'show_image': True, 'image': str(TMP / 'badge.png')}}, 'img')
check('with both, it sits between the headline and the pills',
      img['badge'] and img['badge']['t'] >= img['headingB']
      and img['badge']['b'] <= img['stackT'],
      f"heading ends {img['headingB']}, badge {img['badge']['t']}–{img['badge']['b']}, "
      f"pills start {img['stackT']}")
check('and is centred',
      img['badge'] and abs((img['badge']['l'] - img['sectionBox']['l'])
                           - (img['sectionBox']['r'] - img['badge']['r'])) <= 2,
      f"{img['badge']['l'] - img['sectionBox']['l']}px left, "
      f"{img['sectionBox']['r'] - img['badge']['r']}px right")

# ------------------------------------------------------------- the motion ---
observed = run({}, 'observed', mode='wired', settle=False, budget=15000)
check('the pills wait for the section to come into view, then fall',
      all(p['isIn'] for p in observed['pills']),
      f"is-in {[p['isIn'] for p in observed['pills']]}")

wired = run({}, 'wired', settle=False)
check('they fall one after the next, not together',
      [p['delay'] for p in wired['pills']] == ['0s', '0.15s', '0.3s', '0.45s', '0.6s'],
      f"{[p['delay'] for p in wired['pills']]}")
check('and each starts from nothing',
      all(p['opacity'] == 0 for p in wired['pills']),
      f"{[p['opacity'] for p in wired['pills']]}")
late = run({}, 'late', mode='tidied', settle=False, budget=15000)
check('the delay is cleared once each has landed',
      all(p['inlineDelay'] == '' for p in late['pills']),
      f"{[p['inlineDelay'] for p in late['pills']]!r}")

for style in ('drop', 'bounce', 'swing', 'fade'):
    a = run({'settings': {'motion': style}}, style, settle=False)
    b = run({'settings': {'motion': style}}, style + '-settled')
    check(f'"{style}" plays its own animation and settles',
          all(p['name'] == f'hp-pill-{style}' for p in a['pills'])
          and all(p['opacity'] == 1 for p in b['pills']),
          f"animation-name {a['pills'][0]['name']}, settles at {b['pills'][0]['opacity']}")

settled = run({}, 'settled')
check('and every pill keeps its tilt once it has landed',
      [p['cap']['deg'] for p in settled['pills']] == [3, -3, 3, -3, 3],
      f"{[p['cap']['deg'] for p in settled['pills']]}")

# ------------------------------------------------------------- bail-outs ----
off = run({'settings': {'motion': 'none'}}, 'none', mode='plain', settle=False)
check('"none" leaves the section alone entirely',
      'hp-pill--reveal' not in off['cls']
      and all(p['opacity'] == 1 and p['name'] == 'none' for p in off['pills']),
      f"class \"{off['cls']}\"")
rm = run({}, 'reduced', mode='plain', settle=False, flags=('--force-prefers-reduced-motion',))
check('reduced motion drops it, pills visible',
      all(p['opacity'] == 1 for p in rm['pills']) and 'hp-pill--reveal' not in rm['cls'],
      f"opacity {[p['opacity'] for p in rm['pills']]}")
noio = run({}, 'noio', mode='plain', settle=False,
           extra_head='<script>delete window.IntersectionObserver;</script>')
check('with no IntersectionObserver the pills are simply there',
      all(p['opacity'] == 1 for p in noio['pills']) and 'hp-pill--reveal' not in noio['cls'],
      f"opacity {[p['opacity'] for p in noio['pills']]}")

# ------------------------------------------------------------- contrast -----
def rgb(v):
    return [int(x) for x in re.findall(r'\d+', v)[:3]]


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


ratios = [contrast(rgb(p['ink']), rgb(p['bg'])) for p in d['pills']]
check('every pill in the preset is readable',
      min(ratios) >= 4.5,
      ', '.join(f"{p['text']} {r}" for p, r in zip(d['pills'], ratios)))

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
