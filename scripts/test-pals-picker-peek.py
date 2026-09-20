"""Check the side Pals on "Meet the Pals": that picking a Pal puts exactly the
other two out in the gutters, one per side, that neither ever reaches the panel,
and that the whole layer disappears where there is no room for it.

Geometry is measured with motion off. Headless Chromium renders about two frames
under --virtual-time-budget, so an element mid-animation reports its *starting*
transform — measuring the entrance would measure the slide-in, not the layout.
Motion is checked separately, by reading which animations are wired up.
"""
import json, subprocess, sys, pathlib, re

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SECTION = '/home/user/hankie-pals-shopify-store/sections/pals-picker.liquid'
HERE = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path('/tmp/claude-0')

# Stand-ins for the cut-out photos: portrait, so a peek has a real height.
from PIL import Image
for name, rgb in (('a', (216, 139, 109)), ('b', (181, 201, 154)), ('c', (236, 168, 131))):
    Image.new('RGBA', (400, 520), rgb + (255,)).save(TMP / f'peek-{name}.png')

PALS = {'blocks': [
    {'type': 'pal', 'settings': {'name': 'Pip', 'image': str(TMP / 'peek-a.png')}},
    {'type': 'pal', 'settings': {'name': 'Bo', 'image': str(TMP / 'peek-b.png')}},
    {'type': 'pal', 'settings': {'name': 'June', 'image': str(TMP / 'peek-c.png')}},
]}

PROBE = """<script>
function box(r) {
  return { l: Math.round(r.left), r: Math.round(r.right),
           t: Math.round(r.top), b: Math.round(r.bottom),
           w: Math.round(r.width), h: Math.round(r.height) };
}

function shown(el) {
  var cs = getComputedStyle(el);
  return cs.display !== 'none' && cs.visibility !== 'hidden';
}

function state() {
  var panel = null;
  [].forEach.call(document.querySelectorAll('.hp-pals__panel'), function (p) {
    if (shown(p)) panel = p;
  });
  var checked = document.querySelector('.hp-pals__radio:checked');
  var mid = window.innerWidth / 2;

  return {
    selected: checked ? checked.getAttribute('data-pal') : null,
    panel: panel ? box(panel.getBoundingClientRect()) : null,
    panelZ: panel ? getComputedStyle(panel).zIndex : null,
    // Where the ink actually is. The name, the trait and the button row are
    // block level, so their boxes reach the column edge whatever the text
    // does — these are the boxes a peek must never cross.
    painted: panel ? [].map.call(
      panel.querySelectorAll('.hp-pals__photo, .hp-pals__copy > *'),
      function (el) {
        var r = el.getBoundingClientRect();
        return { what: el.className || el.tagName, l: Math.round(r.left), r: Math.round(r.right) };
      }) : [],
    // The centre the peeks are anchored to: the stage's own middle, which is
    // the panel's middle too, scrollbar included.
    centre: (function () {
      var st = document.querySelector('.hp-pals__stage').getBoundingClientRect();
      return Math.round((st.left + st.right) / 2);
    })(),
    peeksInDom: document.querySelectorAll('.hp-pals__peek').length,
    peeks: [].filter.call(document.querySelectorAll('.hp-pals__peek'), shown)
      .map(function (el) {
        var cs = getComputedStyle(el);
        var r = el.getBoundingClientRect();
        return {
          pal: el.getAttribute('data-pal'),
          box: box(r),
          side: (r.left + r.right) / 2 < mid ? 'left' : 'right',
          z: cs.zIndex,
          opacity: Math.round(parseFloat(cs.opacity) * 100) / 100,
          anim: cs.animationName,
          masked: el.classList.contains('hp-pals__peek--mask'),
          // The layout box, not the rect: a rotated element reports a bigger
          // rect than it occupies, which would read as the wrong shape.
          ratio: Math.round((el.offsetWidth / el.offsetHeight) * 100) / 100,
          events: cs.pointerEvents
        };
      }),
    marksInDom: document.querySelectorAll('.hp-pals__mark').length,
    marks: [].filter.call(document.querySelectorAll('.hp-pals__mark'), shown)
      .map(function (el) { return box(el.getBoundingClientRect()); }),
    markAnim: (function () {
      var m = document.querySelector('.hp-pals__mark');
      return m ? getComputedStyle(m).animationName : null;
    })(),
    // The peeks run off both sides; if the section is not clipping they widen
    // the page instead.
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth,
    clip: getComputedStyle(document.querySelector('.hp-pals')).overflowX
  };
}

setTimeout(function () {
  var out = { first: state() };

  // Pick the third Pal the way a click does, then measure again.
  // getBoundingClientRect forces layout, so this is up to date immediately.
  var radios = document.querySelectorAll('.hp-pals__radio');
  if (radios.length > 2) {
    radios[2].checked = true;
    out.second = state();
  }
  document.title = 'RESULT' + JSON.stringify(out);
}, 700);
</script>"""


def run(overrides, name, width=1440, flags=()):
    page = TMP / f'pk-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), SECTION,
                    json.dumps(overrides), str(page)], check=True, capture_output=True)
    page.write_text(page.read_text(encoding='utf-8').replace('</body>', PROBE + '</body>'),
                    encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},1000', '--virtual-time-budget=4000', *flags,
        '--dump-dom', 'file://' + str(page)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


still = dict(PALS, settings={'enable_motion': False})

# ---------------------------------------------------------------- wide -----
d = run(still, 'wide')['first']
p = d['panel']
check('one peek is rendered per Pal, not one per side',
      d['peeksInDom'] == 3, f"{d['peeksInDom']} peeks for 3 Pals")
check('exactly two Pals wait at the sides',
      len(d['peeks']) == 2, f"{[x['pal'] for x in d['peeks']]} shown")
check('the Pal on show is never also at the side',
      d['selected'] not in [x['pal'] for x in d['peeks']],
      f"selected {d['selected']}, at the sides {[x['pal'] for x in d['peeks']]}")
check('one on the left, one on the right',
      sorted(x['side'] for x in d['peeks']) == ['left', 'right'],
      ', '.join(f"{x['pal']} {x['side']}" for x in d['peeks']))

left = [x for x in d['peeks'] if x['side'] == 'left'][0]
right = [x for x in d['peeks'] if x['side'] == 'right'][0]
check('each stops exactly where the offset says, tilt and all',
      abs(left['box']['r'] - (d['centre'] - 560)) <= 1 and
      abs(right['box']['l'] - (d['centre'] + 560)) <= 1,
      f"centre {d['centre']}, left ends {left['box']['r']} (want {d['centre'] - 560}), "
      f"right starts {right['box']['l']} (want {d['centre'] + 560})")
check('neither reaches the panel',
      left['box']['r'] <= p['l'] + 1 and right['box']['l'] >= p['r'] - 1,
      f"left ends {left['box']['r']}, panel {p['l']}–{p['r']}, right starts {right['box']['l']}")
check('both sit behind the panel, not over it',
      int(left['z']) < int(d['panelZ']) and int(right['z']) < int(d['panelZ']),
      f"peeks z {left['z']}/{right['z']} vs panel z {d['panelZ']}")
check('both are clicked through, not over the buttons',
      left['events'] == 'none' and right['events'] == 'none',
      f"pointer-events {left['events']}/{right['events']}")
check('enough of each is on screen to read as a Pal',
      left['box']['r'] - max(left['box']['l'], 0) >= 60 and
      min(right['box']['r'], d['winW']) - right['box']['l'] >= 60,
      f"left shows {left['box']['r'] - max(left['box']['l'], 0)}px, "
      f"right shows {min(right['box']['r'], d['winW']) - right['box']['l']}px")
check('they are held back from the chosen Pal',
      0 < left['opacity'] < 1, f"opacity {left['opacity']}")
check('they sit level with the panel, not above or below it',
      left['box']['t'] > p['t'] - 200 and left['box']['b'] < p['b'] + 200,
      f"peek {left['box']['t']}–{left['box']['b']} vs panel {p['t']}–{p['b']}")
check('the band clips them instead of widening the page',
      d['docW'] <= d['winW'] and d['clip'] in ('hidden', 'clip'),
      f"document {d['docW']}px in a {d['winW']}px window, overflow-x: {d['clip']}")
check('the panel width setting is what bounds the panel',
      p['w'] == 1120, f"panel {p['w']}px wide")

# The copy that can run widest: a long personality line and a long body wrap
# to the full column, so their boxes end at the panel's own edge.
LONG = 'Wants to do absolutely everything by herself these days, thank you very much'
stress = dict(settings={'enable_motion': False}, blocks=[
    dict(b, settings=dict(b['settings'], trait=LONG, quote='Ready! I did my shoes all by myself!',
                          body='<p>' + 'Pip does not wait for anybody. ' * 4 + '</p>',
                          link='#', link_label='Meet this Pal'))
    for b in PALS['blocks']])
st = run(stress, 'stress')['first']
sl = [x for x in st['peeks'] if x['side'] == 'left'][0]
sr = [x for x in st['peeks'] if x['side'] == 'right'][0]
clear = min(min(w['l'] - sl['box']['r'], sr['box']['l'] - w['r']) for w in st['painted'])
check('nothing in the panel is covered, even at the longest copy',
      clear >= 0,
      'closest approach ' + str(clear) + 'px, at ' +
      min(st['painted'], key=lambda w: min(w['l'] - sl['box']['r'], sr['box']['l'] - w['r']))['what'])

# ------------------------------------------------------------- the swap ----
both = run(still, 'swap')
a, b = both['first'], both['second']
check('picking another Pal swaps who is waiting at the sides',
      a['selected'] != b['selected'] and
      sorted(x['pal'] for x in a['peeks']) != sorted(x['pal'] for x in b['peeks']),
      f"{a['selected']} -> {[x['pal'] for x in a['peeks']]}, "
      f"{b['selected']} -> {[x['pal'] for x in b['peeks']]}")
check('after the swap it is still the other two, one per side',
      len(b['peeks']) == 2 and b['selected'] not in [x['pal'] for x in b['peeks']]
      and sorted(x['side'] for x in b['peeks']) == ['left', 'right'],
      f"{[(x['pal'], x['side']) for x in b['peeks']]}")

# ------------------------------------------------------------ narrower ----
for w in (1319, 1100, 900, 600):
    n = run(still, f'w{w}', width=max(w, 500))['first']
    check(f'no side Pals at {w}px, where there is no room for them',
          len(n['peeks']) == 0 and n['docW'] <= n['winW'],
          f"{len(n['peeks'])} shown, document {n['docW']}px in {n['winW']}px")

# --------------------------------------------------------------- marks ----
check('eight sparkles, all on screen on desktop',
      d['marksInDom'] == 8 and len(d['marks']) == 8,
      f"{len(d['marks'])} of {d['marksInDom']} shown")
check('no sparkle lands on the panel',
      all(m['r'] <= p['l'] or m['l'] >= p['r'] or m['b'] <= p['t'] or m['t'] >= p['b']
          for m in d['marks']),
      f"panel {p['l']},{p['t']}–{p['r']},{p['b']}; "
      f"nearest {min((min(abs(m['l'] - p['r']), abs(m['r'] - p['l'])) for m in d['marks']))}px clear")
check('every sparkle stays inside the band',
      all(0 <= m['l'] and m['r'] <= d['winW'] for m in d['marks']),
      f"x range {min(m['l'] for m in d['marks'])}–{max(m['r'] for m in d['marks'])} in {d['winW']}px")
small = run(still, 'marks-mobile', width=600)['first']
check('no sparkles on mobile',
      len(small['marks']) == 0, f"{len(small['marks'])} shown at 600px")
off = run(dict(PALS, settings={'enable_motion': False, 'show_marks': False}), 'marks-off')['first']
check('the sparkles can be turned off',
      off['marksInDom'] == 0, f"{off['marksInDom']} in the DOM with the setting off")

# -------------------------------------------------------------- motion ----
m = run(PALS, 'motion')['first']
names = sorted(x['anim'] for x in m['peeks'])
check('each side gets its own entrance, then drifts',
      names == ['hp-pals-peek-l, hp-pals-peek-float', 'hp-pals-peek-r, hp-pals-peek-float'],
      f"{names}")
check('the sparkles drift too',
      m['markAnim'] == 'hp-pals-mark-float', f"{m['markAnim']}")
rm = run(PALS, 'reduced', flags=('--force-prefers-reduced-motion',))['first']
check('nothing moves for a visitor who asked for less motion',
      all(x['anim'] == 'none' for x in rm['peeks']) and rm['markAnim'] == 'none',
      f"peeks {[x['anim'] for x in rm['peeks']]}, sparkles {rm['markAnim']}")
check('and they are still there, at full placement',
      len(rm['peeks']) == 2 and rm['peeks'][0]['opacity'] > 0,
      f"{len(rm['peeks'])} shown at opacity {rm['peeks'][0]['opacity'] if rm['peeks'] else '-'}")

# -------------------------------------------------------- masked option ---
mask = run(dict(PALS, settings={'enable_motion': False, 'peek_mask': True}), 'mask')['first']
check('the blob mask is off unless asked for',
      not d['peeks'][0]['masked'] and abs(d['peeks'][0]['ratio'] - 400 / 520) < 0.02,
      f"masked {d['peeks'][0]['masked']}, ratio {d['peeks'][0]['ratio']}")
check('turning the mask on makes each side Pal a square blob',
      mask['peeks'][0]['masked'] and abs(mask['peeks'][0]['ratio'] - 1) < 0.02,
      f"masked {mask['peeks'][0]['masked']}, ratio {mask['peeks'][0]['ratio']}")

# ------------------------------------------------------------ two Pals ----
two = run({'settings': {'enable_motion': False}, 'blocks': PALS['blocks'][:2]}, 'two')['first']
check('with only two Pals the other one shows once, not on both sides',
      len(two['peeks']) == 1, f"{len(two['peeks'])} shown")
one = run({'settings': {'enable_motion': False}, 'blocks': PALS['blocks'][:1]}, 'one')['first']
check('with one Pal there is nothing to wait at the side',
      len(one['peeks']) == 0 and one['peeksInDom'] == 0,
      f"{one['peeksInDom']} in the DOM")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
